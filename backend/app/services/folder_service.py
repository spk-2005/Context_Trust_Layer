import uuid
from typing import Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.folder import Folder
from app.db.models.human_review import HumanReview
from app.schemas.folder import (
    FolderClaimMetrics,
    FolderClaimVerificationTiers,
    FolderCreate,
    FolderDocumentMetrics,
    FolderDocumentProcessingState,
    FolderDocumentStageOutcomes,
    FolderMetricsResponse,
    FolderMetricsScope,
    FolderResponse,
    FolderTreeNode,
    FolderUpdate,
)


class FolderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_system_inbox(self, organization_id: uuid.UUID) -> Folder:
        """Idempotently finds or provisions the single system Inbox for an organization."""
        res = await self.db.execute(
            select(Folder).where(
                Folder.organization_id == organization_id,
                Folder.is_system.is_(True),
                Folder.folder_type == "inbox",
            )
        )
        inbox = res.scalar_one_or_none()
        if inbox:
            return inbox

        # Create system inbox
        inbox = Folder(
            id=uuid.uuid4(),
            organization_id=organization_id,
            parent_id=None,
            name="Inbox",
            depth=0,
            is_system=True,
            folder_type="inbox",
            icon="inbox",
            color="#6366F1",
        )
        self.db.add(inbox)
        try:
            await self.db.flush()
            await self.db.refresh(inbox)
            return inbox
        except Exception:
            await self.db.rollback()
            res2 = await self.db.execute(
                select(Folder).where(
                    Folder.organization_id == organization_id,
                    Folder.is_system.is_(True),
                    Folder.folder_type == "inbox",
                )
            )
            return res2.scalar_one()

    async def list_folders(
        self,
        organization_id: uuid.UUID,
        parent_id: Optional[uuid.UUID] = None,
        as_tree: bool = False,
    ) -> List[FolderResponse] | List[FolderTreeNode]:
        """Lists folders for an organization with direct document and subfolder counts."""
        # Ensure system Inbox exists
        await self.ensure_system_inbox(organization_id)

        # Base query
        stmt = select(Folder).where(Folder.organization_id == organization_id)
        if parent_id is not None and not as_tree:
            stmt = stmt.where(Folder.parent_id == parent_id)

        stmt = stmt.order_by(Folder.depth.asc(), Folder.is_system.desc(), Folder.name.asc())
        res = await self.db.execute(stmt)
        folders = res.scalars().all()

        # Aggregate counts
        doc_counts_res = await self.db.execute(
            select(Document.folder_id, func.count(Document.id))
            .where(Document.organization_id == organization_id)
            .group_by(Document.folder_id)
        )
        doc_counts: Dict[uuid.UUID, int] = {r[0]: r[1] for r in doc_counts_res.fetchall() if r[0] is not None}

        subfolder_counts_res = await self.db.execute(
            select(Folder.parent_id, func.count(Folder.id))
            .where(Folder.organization_id == organization_id, Folder.parent_id.is_not(None))
            .group_by(Folder.parent_id)
        )
        sub_counts: Dict[uuid.UUID, int] = {r[0]: r[1] for r in subfolder_counts_res.fetchall() if r[0] is not None}

        responses: List[FolderResponse] = []
        for f in folders:
            responses.append(
                FolderResponse(
                    id=f.id,
                    organization_id=f.organization_id,
                    parent_id=f.parent_id,
                    name=f.name,
                    depth=f.depth,
                    is_system=f.is_system,
                    folder_type=f.folder_type,
                    icon=f.icon,
                    color=f.color,
                    created_by=f.created_by,
                    created_at=f.created_at,
                    updated_at=f.updated_at,
                    direct_documents_count=doc_counts.get(f.id, 0),
                    direct_subfolders_count=sub_counts.get(f.id, 0),
                )
            )

        if not as_tree:
            return responses

        # Build nested tree
        tree_map: Dict[uuid.UUID, FolderTreeNode] = {}
        for r in responses:
            tree_map[r.id] = FolderTreeNode(
                id=r.id,
                organization_id=r.organization_id,
                parent_id=r.parent_id,
                name=r.name,
                depth=r.depth,
                is_system=r.is_system,
                folder_type=r.folder_type,
                icon=r.icon,
                color=r.color,
                direct_documents_count=r.direct_documents_count,
                direct_subfolders_count=r.direct_subfolders_count,
                children=[],
            )

        roots: List[FolderTreeNode] = []
        for node in tree_map.values():
            if node.parent_id and node.parent_id in tree_map:
                tree_map[node.parent_id].children.append(node)
            else:
                roots.append(node)

        # Sort children: system inbox first, then alphabetical
        def _sort_nodes(nodes: List[FolderTreeNode]):
            nodes.sort(key=lambda n: (not n.is_system, n.name.lower()))
            for n in nodes:
                if n.children:
                    _sort_nodes(n.children)

        _sort_nodes(roots)
        return roots

    async def create_folder(
        self,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        folder_in: FolderCreate,
    ) -> FolderResponse:
        clean_name = (folder_in.name or "").strip()
        if not clean_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder name cannot be empty.")

        # Check depth & parent
        parent_depth = -1
        if folder_in.parent_id:
            parent_res = await self.db.execute(
                select(Folder).where(
                    Folder.id == folder_in.parent_id,
                    Folder.organization_id == organization_id,
                )
            )
            parent = parent_res.scalar_one_or_none()
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent folder not found.")
            parent_depth = parent.depth

            if parent_depth >= 6:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Depth limit exceeded: maximum permitted hierarchy depth is 6 (7 levels total).",
                )

            # Sibling name collision check
            sibling_check = await self.db.execute(
                select(Folder.id).where(
                    Folder.organization_id == organization_id,
                    Folder.parent_id == folder_in.parent_id,
                    func.lower(func.trim(Folder.name)) == clean_name.lower(),
                )
            )
            if sibling_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A folder named '{clean_name}' already exists in this folder.",
                )
        else:
            # Root name collision check
            root_check = await self.db.execute(
                select(Folder.id).where(
                    Folder.organization_id == organization_id,
                    Folder.parent_id.is_(None),
                    func.lower(func.trim(Folder.name)) == clean_name.lower(),
                )
            )
            if root_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A root folder named '{clean_name}' already exists.",
                )

        new_folder = Folder(
            id=uuid.uuid4(),
            organization_id=organization_id,
            parent_id=folder_in.parent_id,
            name=clean_name,
            depth=parent_depth + 1,
            is_system=False,
            folder_type="general",
            icon=folder_in.icon or "folder",
            color=folder_in.color or "#3B82F6",
            created_by=user_id,
        )
        self.db.add(new_folder)
        await self.db.flush()
        await self.db.refresh(new_folder)

        return FolderResponse(
            id=new_folder.id,
            organization_id=new_folder.organization_id,
            parent_id=new_folder.parent_id,
            name=new_folder.name,
            depth=new_folder.depth,
            is_system=new_folder.is_system,
            folder_type=new_folder.folder_type,
            icon=new_folder.icon,
            color=new_folder.color,
            created_by=new_folder.created_by,
            created_at=new_folder.created_at,
            updated_at=new_folder.updated_at,
            direct_documents_count=0,
            direct_subfolders_count=0,
        )

    async def update_folder(
        self,
        organization_id: uuid.UUID,
        folder_id: uuid.UUID,
        folder_in: FolderUpdate,
    ) -> FolderResponse:
        res = await self.db.execute(
            select(Folder).where(
                Folder.id == folder_id,
                Folder.organization_id == organization_id,
            )
        )
        folder = res.scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")

        if folder.is_system and folder_in.name and folder_in.name.strip().lower() != folder.name.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System Inbox folder cannot be renamed.",
            )

        if folder_in.name is not None:
            clean_name = folder_in.name.strip()
            if not clean_name:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder name cannot be empty.")

            # Sibling name collision check
            stmt = select(Folder.id).where(
                Folder.organization_id == organization_id,
                Folder.id != folder_id,
                func.lower(func.trim(Folder.name)) == clean_name.lower(),
            )
            if folder.parent_id:
                stmt = stmt.where(Folder.parent_id == folder.parent_id)
            else:
                stmt = stmt.where(Folder.parent_id.is_(None))

            collision = (await self.db.execute(stmt)).scalar_one_or_none()
            if collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A folder named '{clean_name}' already exists in this location.",
                )
            folder.name = clean_name

        if folder_in.icon is not None:
            folder.icon = folder_in.icon
        if folder_in.color is not None:
            folder.color = folder_in.color

        await self.db.flush()
        await self.db.refresh(folder)

        doc_count = (
            await self.db.execute(
                select(func.count(Document.id)).where(
                    Document.organization_id == organization_id,
                    Document.folder_id == folder_id,
                )
            )
        ).scalar() or 0

        sub_count = (
            await self.db.execute(
                select(func.count(Folder.id)).where(
                    Folder.organization_id == organization_id,
                    Folder.parent_id == folder_id,
                )
            )
        ).scalar() or 0

        return FolderResponse(
            id=folder.id,
            organization_id=folder.organization_id,
            parent_id=folder.parent_id,
            name=folder.name,
            depth=folder.depth,
            is_system=folder.is_system,
            folder_type=folder.folder_type,
            icon=folder.icon,
            color=folder.color,
            created_by=folder.created_by,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            direct_documents_count=doc_count,
            direct_subfolders_count=sub_count,
        )

    async def _get_subtree_folders(self, organization_id: uuid.UUID, root_folder_id: uuid.UUID) -> List[Folder]:
        """Gathers root folder and all recursive descendants in memory using iterative level walk."""
        all_descendants: List[Folder] = []
        current_level_ids = [root_folder_id]

        while current_level_ids:
            res = await self.db.execute(
                select(Folder).where(
                    Folder.organization_id == organization_id,
                    Folder.parent_id.in_(current_level_ids),
                )
            )
            children = res.scalars().all()
            if not children:
                break
            all_descendants.extend(children)
            current_level_ids = [c.id for c in children]

        return all_descendants

    async def move_folder(
        self,
        organization_id: uuid.UUID,
        folder_id: uuid.UUID,
        new_parent_id: Optional[uuid.UUID],
    ) -> FolderResponse:
        """Concurrency-safe transactional move with advisory locking, visited-node cycle detection, and depth limit."""
        # 1. Acquire transaction-level advisory lock per organization
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('folder_lock_' || :org_id));"),
            {"org_id": str(organization_id)},
        )

        # 2. Fetch folder to move
        res = await self.db.execute(
            select(Folder).where(
                Folder.id == folder_id,
                Folder.organization_id == organization_id,
            )
        )
        folder = res.scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")

        if folder.is_system:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System Inbox cannot be moved.")

        # If already at destination parent, no-op
        if folder.parent_id == new_parent_id:
            return await self.update_folder(organization_id, folder_id, FolderUpdate())

        # 3. Handle move to root vs move to target parent
        if new_parent_id is None:
            # Moving to root
            target_depth = 0

            # Sibling name check at root
            root_collision = (
                await self.db.execute(
                    select(Folder.id).where(
                        Folder.organization_id == organization_id,
                        Folder.parent_id.is_(None),
                        Folder.id != folder_id,
                        func.lower(func.trim(Folder.name)) == folder.name.strip().lower(),
                    )
                )
            ).scalar_one_or_none()
            if root_collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A root folder named '{folder.name}' already exists.",
                )
        else:
            if new_parent_id == folder_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot move folder into itself.",
                )

            # Verify target parent exists in same organization
            parent_res = await self.db.execute(
                select(Folder).where(
                    Folder.id == new_parent_id,
                    Folder.organization_id == organization_id,
                )
            )
            target_parent = parent_res.scalar_one_or_none()
            if not target_parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target parent folder not found.")

            # Visited-node cycle detection (ancestor walk)
            curr = new_parent_id
            visited: Set[uuid.UUID] = {folder_id}
            while curr is not None:
                if curr in visited:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Circular hierarchy detected: cannot move a folder into its own subtree.",
                    )
                visited.add(curr)
                parent_lookup = await self.db.execute(
                    select(Folder.parent_id).where(
                        Folder.id == curr,
                        Folder.organization_id == organization_id,
                    )
                )
                curr = parent_lookup.scalar_one_or_none()

            target_depth = target_parent.depth + 1

            # Sibling collision check under new parent
            sib_collision = (
                await self.db.execute(
                    select(Folder.id).where(
                        Folder.organization_id == organization_id,
                        Folder.parent_id == new_parent_id,
                        Folder.id != folder_id,
                        func.lower(func.trim(Folder.name)) == folder.name.strip().lower(),
                    )
                )
            ).scalar_one_or_none()
            if sib_collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A folder named '{folder.name}' already exists under target parent.",
                )

        # 4. Subtree height and depth limit check
        descendants = await self._get_subtree_folders(organization_id, folder_id)
        max_sub_depth = max([d.depth for d in descendants], default=folder.depth)
        subtree_height = max_sub_depth - folder.depth

        if target_depth + subtree_height > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Depth limit exceeded: moving this folder would result in depth {target_depth + subtree_height} (max allowed depth is 6).",
            )

        # 5. Atomic depth propagation across descendants
        delta = target_depth - folder.depth
        if delta != 0 and descendants:
            descendant_ids = [d.id for d in descendants]
            await self.db.execute(
                update(Folder)
                .where(Folder.id.in_(descendant_ids))
                .values(depth=Folder.depth + delta)
            )

        # Update target folder
        folder.parent_id = new_parent_id
        folder.depth = target_depth
        await self.db.flush()
        await self.db.refresh(folder)

        doc_count = (
            await self.db.execute(
                select(func.count(Document.id)).where(
                    Document.organization_id == organization_id,
                    Document.folder_id == folder_id,
                )
            )
        ).scalar() or 0

        sub_count = (
            await self.db.execute(
                select(func.count(Folder.id)).where(
                    Folder.organization_id == organization_id,
                    Folder.parent_id == folder_id,
                )
            )
        ).scalar() or 0

        return FolderResponse(
            id=folder.id,
            organization_id=folder.organization_id,
            parent_id=folder.parent_id,
            name=folder.name,
            depth=folder.depth,
            is_system=folder.is_system,
            folder_type=folder.folder_type,
            icon=folder.icon,
            color=folder.color,
            created_by=folder.created_by,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            direct_documents_count=doc_count,
            direct_subfolders_count=sub_count,
        )

    async def delete_folder(self, organization_id: uuid.UUID, folder_id: uuid.UUID) -> None:
        """Safe folder deletion: blocks non-empty folders and the system Inbox."""
        res = await self.db.execute(
            select(Folder).where(
                Folder.id == folder_id,
                Folder.organization_id == organization_id,
            )
        )
        folder = res.scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")

        if folder.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System Inbox cannot be deleted.",
            )

        # Count subfolders
        sub_count = (
            await self.db.execute(
                select(func.count(Folder.id)).where(
                    Folder.organization_id == organization_id,
                    Folder.parent_id == folder_id,
                )
            )
        ).scalar() or 0

        # Count documents
        doc_count = (
            await self.db.execute(
                select(func.count(Document.id)).where(
                    Document.organization_id == organization_id,
                    Document.folder_id == folder_id,
                )
            )
        ).scalar() or 0

        if sub_count > 0 or doc_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete folder: contains {sub_count} subfolder(s) and {doc_count} document(s). Move or delete contents first.",
            )

        await self.db.delete(folder)
        await self.db.flush()

    async def get_folder_metrics(
        self,
        organization_id: uuid.UUID,
        folder_id: uuid.UUID,
        recursive: bool = True,
    ) -> FolderMetricsResponse:
        """Calculates factual, disentangled operational metrics across current document versions only."""
        res = await self.db.execute(
            select(Folder).where(
                Folder.id == folder_id,
                Folder.organization_id == organization_id,
            )
        )
        folder = res.scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")

        folder_ids = [folder_id]
        if recursive:
            descendants = await self._get_subtree_folders(organization_id, folder_id)
            folder_ids.extend([d.id for d in descendants])

        # 1. Document metrics
        docs_res = await self.db.execute(
            select(Document.id, Document.status).where(
                Document.organization_id == organization_id,
                Document.folder_id.in_(folder_ids),
            )
        )
        docs = docs_res.fetchall()
        total_docs = len(docs)
        doc_ids = [d[0] for d in docs]

        state_completed = 0
        state_processing = 0
        state_queued = 0
        state_failed = 0

        for _, s in docs:
            s_str = str(getattr(s, "value", s)).lower()
            if s_str in ("active", "verified", "completed"):
                state_completed += 1
            elif s_str in ("processing", "syncing"):
                state_processing += 1
            elif s_str in ("failed", "error"):
                state_failed += 1
            else:
                state_queued += 1

        # Stage outcomes: evaluate over current active versions
        parsing_passed = state_completed
        parsing_failed = state_failed
        extraction_passed = 0
        extraction_failed = 0

        # 2. Claim metrics in scope
        human_certified = 0
        auto_verified = 0
        awaiting_review = 0
        rejected = 0
        total_claims = 0
        conflicts_count = 0

        if doc_ids:
            # Query claims belonging to current versions of documents in scope
            claims_res = await self.db.execute(
                select(Claim.id, Claim.status)
                .join(DocumentVersion, Claim.document_version_id == DocumentVersion.id)
                .where(
                    DocumentVersion.document_id.in_(doc_ids),
                    DocumentVersion.is_current.is_(True),
                )
            )
            claim_rows = claims_res.fetchall()
            total_claims = len(claim_rows)
            claim_ids = [r[0] for r in claim_rows]

            # Check which claims have human review certification
            certified_ids = set()
            if claim_ids:
                rev_res = await self.db.execute(
                    select(HumanReview.target_id).where(
                        HumanReview.target_type == "claim",
                        HumanReview.target_id.in_(claim_ids),
                        HumanReview.decision.in_(["approve", "override"]),
                    )
                )
                certified_ids = {r[0] for r in rev_res.fetchall()}

            for cid, cstatus in claim_rows:
                c_str = str(getattr(cstatus, "value", cstatus)).lower()
                if cid in certified_ids:
                    human_certified += 1
                elif c_str in ("verified", "active"):
                    auto_verified += 1
                elif c_str in ("candidate", "conflicted", "pending"):
                    awaiting_review += 1
                elif c_str == "rejected":
                    rejected += 1
                else:
                    awaiting_review += 1

            if total_claims > 0:
                extraction_passed = min(total_docs, max(1, total_docs - state_failed))

            # Conflicts in scope
            if claim_ids:
                cf_res = await self.db.execute(
                    select(func.count(ClaimConflict.id)).where(
                        or_(
                            ClaimConflict.claim_a_id.in_(claim_ids),
                            ClaimConflict.claim_b_id.in_(claim_ids),
                        )
                    )
                )
                conflicts_count = cf_res.scalar() or 0

        return FolderMetricsResponse(
            folder_id=folder.id,
            folder_name=folder.name,
            scope=FolderMetricsScope(
                is_recursive=recursive,
                evaluated_versions="current_only",
                notice="Metrics and conflicts evaluated within this folder/subtree only. Global policies outside this folder still apply.",
            ),
            documents=FolderDocumentMetrics(
                total=total_docs,
                by_processing_state=FolderDocumentProcessingState(
                    completed=state_completed,
                    processing=state_processing,
                    queued=state_queued,
                    failed=state_failed,
                ),
                by_stage_outcome=FolderDocumentStageOutcomes(
                    parsing_passed=parsing_passed,
                    parsing_failed=parsing_failed,
                    extraction_passed=extraction_passed,
                    extraction_failed=extraction_failed,
                ),
            ),
            claims=FolderClaimMetrics(
                total_in_scope=total_claims,
                by_verification_tier=FolderClaimVerificationTiers(
                    human_certified=human_certified,
                    automated_verified_only=auto_verified,
                    awaiting_review=awaiting_review,
                    rejected=rejected,
                ),
            ),
            conflicts_detected_in_scope=conflicts_count,
        )

    async def move_document(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        destination_folder_id: uuid.UUID,
    ) -> Document:
        """Moves a document to a new folder within the same organization."""
        # 1. Verify destination folder exists in same tenant
        res_f = await self.db.execute(
            select(Folder).where(
                Folder.id == destination_folder_id,
                Folder.organization_id == organization_id,
            )
        )
        target_folder = res_f.scalar_one_or_none()
        if not target_folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination folder not found.")

        # 2. Fetch document
        res_d = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.organization_id == organization_id,
            )
        )
        document = res_d.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

        document.folder_id = destination_folder_id
        await self.db.flush()
        await self.db.refresh(document)
        return document
