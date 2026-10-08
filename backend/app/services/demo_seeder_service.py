import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    ClaimStatus,
    ConflictStatus,
    RecordStatus,
    UserRole,
)
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.user import User
from app.db.models.user_activity import UserActivityLog


class DemoSeederService:
    """Automated Sample Data Seeder for Demo Evaluations and New Tenant Provisioning."""

    @classmethod
    async def seed_starter_knowledge(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        clear_existing: bool = False,
    ) -> dict:
        """Seeds complete demo knowledge graph (Connectors, Policies, Claims, Conflicts) for an organization."""
        # 1. Optionally clear existing demo data for this org
        if clear_existing:
            # Delete claims and conflicts for this org
            claims_stmt = select(Claim.id).where(Claim.organization_id == organization_id)
            claim_ids_res = await db.execute(claims_stmt)
            claim_ids = [c for c in claim_ids_res.scalars().all()]
            if claim_ids:
                await db.execute(
                    delete(ClaimConflict).where(
                        (ClaimConflict.claim_a_id.in_(claim_ids)) | (ClaimConflict.claim_b_id.in_(claim_ids))
                    )
                )
                await db.execute(delete(Claim).where(Claim.organization_id == organization_id))

            # Delete documents
            await db.execute(delete(Document).where(Document.organization_id == organization_id))
            # Delete sources
            await db.execute(delete(DataSource).where(DataSource.organization_id == organization_id))
            await db.flush()

        # 2. Ensure Data Source Connectors exist
        source_res = await db.execute(
            select(DataSource).where(DataSource.organization_id == organization_id).limit(1)
        )
        existing_source = source_res.scalar_one_or_none()

        if not existing_source:
            source_finance = DataSource(
                id=uuid.uuid4(),
                organization_id=organization_id,
                owner_id=user_id,
                name="Acme Finance & Billing Confluence",
                source_type="confluence",
                external_id="confluence://finance.internal/policies",
                authority_level=90,
                domain="finance",
                status=RecordStatus.ACTIVE,
                connection_config={"space": "FIN", "auth": "oauth2"},
            )
            source_secops = DataSource(
                id=uuid.uuid4(),
                organization_id=organization_id,
                owner_id=user_id,
                name="Engineering SecOps GitHub Repository",
                source_type="github",
                external_id="github://internal-org/security-mandates",
                authority_level=95,
                domain="secops",
                status=RecordStatus.ACTIVE,
                connection_config={"repo": "security-mandates", "branch": "main"},
            )
            db.add_all([source_finance, source_secops])
            await db.flush()
        else:
            source_finance = existing_source
            source_secops = existing_source

        # 3. Create Sample Documents & Versions
        docs_created = []

        # Doc 1: Active 2026 Customer Refund Policy
        content_1 = (
            "# Enterprise Customer Refund Authorization Policy (2026)\n\n"
            "Under the updated 2026 Enterprise Service Tier SLA, enterprise customers on annual commitments "
            "are eligible for a full 45-day refund window upon Vice President (VP) of Customer Success authorization. "
            "All refund disbursements exceeding $10,000 must be processed through automated payment gateways within 5 business days."
        )
        doc_1 = Document(
            id=uuid.uuid4(),
            organization_id=organization_id,
            source_id=source_finance.id,
            owner_id=user_id,
            title="CUSTOMER_REFUND_POLICY_2026.md",
            document_type="policy",
            domain="finance",
            content_hash=hashlib.sha256(content_1.encode()).hexdigest(),
        )
        db.add(doc_1)
        await db.flush()

        ver_1 = DocumentVersion(
            id=uuid.uuid4(),
            document_id=doc_1.id,
            version_number=1,
            content_hash=doc_1.content_hash,
            content_uri=f"inline://policies/{doc_1.id}",
            is_current=True,
        )
        db.add(ver_1)
        await db.flush()
        docs_created.append((doc_1, ver_1))

        # Doc 2: Outdated Legacy Billing SLA (Intentionally conflicting)
        content_2 = (
            "# Legacy Billing SLA & Arbitration Guidelines (2023)\n\n"
            "Customer refund claims submitted after 14 calendar days from the invoice issuance date are strictly prohibited. "
            "Under no circumstances may customer success representatives or department directors extend the dispute window beyond 14 days without board approval."
        )
        doc_2 = Document(
            id=uuid.uuid4(),
            organization_id=organization_id,
            source_id=source_finance.id,
            owner_id=user_id,
            title="LEGACY_BILLING_SLA_2023.md",
            document_type="policy",
            domain="finance",
            content_hash=hashlib.sha256(content_2.encode()).hexdigest(),
        )
        db.add(doc_2)
        await db.flush()

        ver_2 = DocumentVersion(
            id=uuid.uuid4(),
            document_id=doc_2.id,
            version_number=1,
            content_hash=doc_2.content_hash,
            content_uri=f"inline://policies/{doc_2.id}",
            is_current=True,
        )
        db.add(ver_2)
        await db.flush()
        docs_created.append((doc_2, ver_2))

        # Doc 3: Friday Freeze Mandate (SecOps)
        content_3 = (
            "# Infrastructure Change Freeze & Friday Deployment Mandate\n\n"
            "To preserve core system reliability, all production deployments, cloud infrastructure modifications, "
            "and IAM permission grants are strictly frozen on Fridays after 14:00 UTC. Emergency hotfixes require dual executive sign-off from the Lead Security Architect and CISO."
        )
        doc_3 = Document(
            id=uuid.uuid4(),
            organization_id=organization_id,
            source_id=source_secops.id,
            owner_id=user_id,
            title="FRIDAY_DEPLOYMENT_FREEZE_MANDATE.md",
            document_type="policy",
            domain="secops",
            content_hash=hashlib.sha256(content_3.encode()).hexdigest(),
        )
        db.add(doc_3)
        await db.flush()

        ver_3 = DocumentVersion(
            id=uuid.uuid4(),
            document_id=doc_3.id,
            version_number=1,
            content_hash=doc_3.content_hash,
            content_uri=f"inline://policies/{doc_3.id}",
            is_current=True,
        )
        db.add(ver_3)
        await db.flush()
        docs_created.append((doc_3, ver_3))

        # Doc 4: AI Governance & LLM Privacy Mandate
        content_4 = (
            "# Enterprise LLM Privacy & Zero Data Retention Policy\n\n"
            "Autonomous AI agents and LLM inference pipelines must operate under zero data retention mode. "
            "Customer personally identifiable information (PII), API tokens, and corporate trading ledger logs must be stripped before external inference."
        )
        doc_4 = Document(
            id=uuid.uuid4(),
            organization_id=organization_id,
            source_id=source_secops.id,
            owner_id=user_id,
            title="ENTERPRISE_LLM_PRIVACY_SLA.md",
            document_type="policy",
            domain="secops",
            content_hash=hashlib.sha256(content_4.encode()).hexdigest(),
        )
        db.add(doc_4)
        await db.flush()

        ver_4 = DocumentVersion(
            id=uuid.uuid4(),
            document_id=doc_4.id,
            version_number=1,
            content_hash=doc_4.content_hash,
            content_uri=f"inline://policies/{doc_4.id}",
            is_current=True,
        )
        db.add(ver_4)
        await db.flush()
        docs_created.append((doc_4, ver_4))

        # 4. Create Atomic Claims
        claim_1 = Claim(
            id=uuid.uuid4(),
            organization_id=organization_id,
            document_version_id=ver_1.id,
            claim_text="Enterprise tier customers may receive a full refund within 45 days upon VP authorization.",
            subject="Enterprise Customer Refund",
            predicate="allows_refund_window",
            object="45 calendar days with VP sign-off",
            claim_type="policy",
            extraction_method="llm",
            status=ClaimStatus.ACTIVE,
        )
        claim_2 = Claim(
            id=uuid.uuid4(),
            organization_id=organization_id,
            document_version_id=ver_2.id,
            claim_text="Customer refund claims submitted after 14 calendar days from invoice are strictly prohibited.",
            subject="Enterprise Customer Refund",
            predicate="limits_refund_window",
            object="14 calendar days maximum",
            claim_type="policy",
            extraction_method="llm",
            status=ClaimStatus.CONFLICTED,
        )
        claim_3 = Claim(
            id=uuid.uuid4(),
            organization_id=organization_id,
            document_version_id=ver_3.id,
            claim_text="Production deployments and IAM modifications are strictly prohibited on Fridays after 14:00 UTC.",
            subject="Production Deployments",
            predicate="prohibits_changes",
            object="Fridays after 14:00 UTC",
            claim_type="policy",
            extraction_method="llm",
            status=ClaimStatus.ACTIVE,
        )
        claim_4 = Claim(
            id=uuid.uuid4(),
            organization_id=organization_id,
            document_version_id=ver_4.id,
            claim_text="Autonomous AI agents and LLM inference pipelines must operate with zero customer data retention.",
            subject="AI Agent Inference",
            predicate="mandates_retention_policy",
            object="Zero retention of customer PII and trading logs",
            claim_type="policy",
            extraction_method="llm",
            status=ClaimStatus.ACTIVE,
        )
        db.add_all([claim_1, claim_2, claim_3, claim_4])
        await db.flush()

        # 5. Create Conflict Pair between Claim 1 and Claim 2
        conflict = ClaimConflict(
            id=uuid.uuid4(),
            claim_a_id=claim_1.id,
            claim_b_id=claim_2.id,
            conflict_type="contradiction",
            severity="high",
            confidence=Decimal("0.95"),
            resolution_status=ConflictStatus.DETECTED,
        )
        db.add(conflict)
        await db.flush()

        # 6. Log activity
        activity = UserActivityLog(
            organization_id=organization_id,
            user_id=user_id,
            user_name="System Demo Seeder",
            user_role="admin",
            action_type="DEMO_DATA_SEEDED",
            target_type="workspace",
            target_title="Starter Knowledge Graph",
            domain="General",
            details={
                "documents_count": 4,
                "claims_count": 4,
                "conflicts_count": 1,
            },
        )
        db.add(activity)
        await db.commit()

        return {
            "status": "success",
            "message": "Demo starter knowledge graph seeded successfully.",
            "documents_seeded": 4,
            "claims_seeded": 4,
            "conflicts_seeded": 1,
            "organization_id": str(organization_id),
        }
