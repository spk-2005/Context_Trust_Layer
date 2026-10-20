import argparse
import asyncio
import hashlib
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.enums import RecordStatus, SourceFamily, SourceIntent
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.organization import Organization
from app.db.repositories.claim_repository import ClaimRepository
from app.db.repositories.document_repository import DocumentRepository
from app.extraction.pipeline import global_extraction_pipeline
from app.ingestion.document_ingestion import DocumentIngestionService
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.universal_file_parser import UniversalFileParser
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.document import DocumentCreate
from app.services.claim_extraction_service import ClaimExtractionService
from app.services.conflict_service import ConflictService
from app.services.trust_service import TrustService
from app.validation_gate.pipeline import global_validation_gate

logger = logging.getLogger(__name__)

STORAGE_UPLOADS_DIR = Path(__file__).resolve().parents[2] / "storage" / "uploads"


class UniversalDocumentPipeline:
    """Universal Enterprise Document Ingestion & Verification Pipeline.

    Handles any input document format including:
    - Microsoft Print to PDF (rasterized vector-drawings with RapidOCR + wordsegment)
    - Standard digital PDFs, scanned documents, Docx, CSV, JSON, Markdown, etc.

    Executes the complete TRULIN 6-layer architecture and verification stack:
    1. Layer 1/2: Organization governance and source connector routing
    2. Layer 3: Canonical source envelope and Merkle hash verification
    3. Layer 4: Evidence unit deconstruction (spatial layout, tables, sections)
    4. Layer 5: Candidate extraction, propositional gatekeepers, modality detection
    5. Layer 6: Python grounding verification, deduplication, and PostgreSQL persistence
    6. Fine-grained atomic clause extraction and boundary anchoring
    7. Cross-policy contradiction and conflict detection
    8. Multi-factor trust scoring (evidence, consistency, authority, freshness)
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: Optional[BaseLLMProvider] = None,
    ):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.claim_repo = ClaimRepository(session)
        self.llm = llm_provider or get_llm_provider()
        self.ingestion_service = DocumentIngestionService(session)

    async def ensure_source_exists(
        self,
        organization_id: uuid.UUID,
        source_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        """Finds or creates a dedicated file-upload DataSource for the organization."""
        # Ensure organization exists
        res_org = await self.session.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        if not res_org.scalar_one_or_none():
            org = Organization(
                id=organization_id,
                name="Default Org",
                slug=f"org-{str(organization_id)[:8]}",
            )
            self.session.add(org)
            await self.session.flush()

        if source_id:
            res_src = await self.session.execute(
                select(DataSource).where(DataSource.id == source_id)
            )
            if res_src.scalar_one_or_none():
                return source_id

        # Find existing 'file' upload source for this organization
        res_file_src = await self.session.execute(
            select(DataSource).where(
                DataSource.organization_id == organization_id,
                DataSource.source_type == "file",
            ).limit(1)
        )
        existing_file_src = res_file_src.scalar_one_or_none()
        if existing_file_src:
            return existing_file_src.id

        new_src_id = uuid.uuid4()
        new_source = DataSource(
            id=new_src_id,
            organization_id=organization_id,
            name="Direct Document Upload",
            source_type="file",
            source_family=SourceFamily.DOCUMENT,
            source_intent=SourceIntent.GOVERNANCE_POLICY,
            external_id=f"file-upload-{str(organization_id)[:8]}",
            authority_level=85,
            status=RecordStatus.ACTIVE,
            scope_config={"include_all_uploads": True},
            capabilities={"supports_file_upload": True, "supports_snapshots": True},
        )
        self.session.add(new_source)
        await self.session.flush()
        return new_src_id

    @staticmethod
    def persist_raw_file_bytes(doc_id: uuid.UUID, filename: str, raw_bytes: bytes) -> Path:
        """Stores original uploaded bytes on disk for direct file viewing and audit verification."""
        STORAGE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        doc_dir = STORAGE_UPLOADS_DIR / str(doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)

        safe_name = os.path.basename(filename or "document.pdf")
        saved_file_path = doc_dir / safe_name
        saved_file_path.write_bytes(raw_bytes)

        if safe_name.lower().endswith(".pdf"):
            (STORAGE_UPLOADS_DIR / f"{doc_id}.pdf").write_bytes(raw_bytes)

        return saved_file_path

    async def process_file(
        self,
        filename: str,
        raw_bytes: bytes,
        organization_id: uuid.UUID,
        source_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
        document_type: str = "policy",
        external_id: Optional[str] = None,
        source_intent: Optional[str] = None,
        persist_file: bool = True,
    ) -> Dict[str, Any]:
        """Ingests and executes full claim extraction, conflict detection, and trust scoring for any uploaded file."""
        t0 = time.time()
        resolved_source_id = await self.ensure_source_exists(organization_id, source_id)

        clean_filename = filename or "uploaded_document.pdf"
        doc_title = title or clean_filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        doc_title = doc_title.replace("\x00", "").strip()
        doc_external_id = (external_id or f"file://{clean_filename}").replace("\x00", "").strip()

        # 1. Universal structured parsing (handles vector Print-to-PDF, layout OCR, tables)
        parsed_doc = UniversalFileParser.parse_structured(
            filename=clean_filename,
            raw_bytes=raw_bytes,
            doc_title=doc_title,
        )
        content_text = parsed_doc.full_text

        # 2. Database ingestion with deduplication
        doc_in = DocumentCreate(
            organization_id=organization_id,
            source_id=resolved_source_id,
            title=doc_title,
            content=content_text,
            document_type=document_type.replace("\x00", ""),
            external_id=doc_external_id,
            metadata={
                "filename": clean_filename,
                "file_size": len(raw_bytes),
                "page_count": len(parsed_doc.pages),
                "is_scanned": parsed_doc.is_scanned,
                "extraction_quality": parsed_doc.extraction_quality,
            },
        )
        document, version, normalized, _ = await self.ingestion_service.ingest_document_with_dedup(doc_in)
        await self.session.commit()

        if persist_file:
            self.persist_raw_file_bytes(document.id, clean_filename, raw_bytes)

        # 3. TRULIN 6-Layer Architecture Pipeline
        resolved_intent = SourceIntent.GOVERNANCE_POLICY
        if source_intent:
            try:
                resolved_intent = SourceIntent(source_intent.lower().strip())
            except ValueError:
                pass
        elif document_type != "policy":
            resolved_intent = SourceIntent.OPERATIONAL_DATA

        canonical_env = EnvelopeFactory.create_from_file_upload(
            filename=clean_filename,
            raw_bytes=raw_bytes,
            parsed_content=content_text,
            organization_id=organization_id,
            source_id=resolved_source_id,
            document_type=document_type,
            source_intent=resolved_intent,
        )

        fmt_lower = (clean_filename.rsplit(".", 1)[-1] if "." in clean_filename else "txt").lower()
        if fmt_lower in ("csv", "json", "xlsx", "sql"):
            evidence_result = await StructuredDataParser.parse(canonical_env)
        else:
            evidence_result = await DocumentParser.parse(canonical_env)

        l5_extraction_result = await global_extraction_pipeline.process_envelope(canonical_env, evidence_result)

        await global_validation_gate.process_extraction_result(
            canonical_env, l5_extraction_result, session=self.session, document_version_id=version.id
        )
        await self.session.commit()

        # 4. Fine-grained atomic clause extraction
        claim_ext_svc = ClaimExtractionService(self.session, llm_provider=self.llm)
        atomic_claims = await claim_ext_svc.extract_claims_from_version(version.id)
        await self.session.commit()

        # 5. Cross-policy conflict detection and trust scoring
        conf_svc = ConflictService(self.session, llm_provider=self.llm)
        conflicts = await conf_svc.run_conflict_detection_for_version(version.id)

        trust_svc = TrustService(self.session)
        await trust_svc.calculate_for_version(version.id)
        await self.session.commit()

        total_claims_res = await self.session.execute(
            select(Claim).where(Claim.document_version_id == version.id)
        )
        total_claims = total_claims_res.scalars().all()

        total_duration = time.time() - t0
        logger.info(
            "Document pipeline finished for '%s' (%s): %d claims, %d conflicts in %.2fs",
            doc_title,
            document.id,
            len(total_claims),
            len(conflicts),
            total_duration,
        )

        return {
            "document_id": str(document.id),
            "version_id": str(version.id),
            "title": document.title,
            "filename": clean_filename,
            "char_count": len(content_text),
            "page_count": len(parsed_doc.pages),
            "claims_count": len(total_claims),
            "conflicts_count": len(conflicts),
            "duration_seconds": round(total_duration, 2),
            "document": document,
            "version": version,
        }

    async def process_existing_document(
        self,
        document_id: uuid.UUID,
        reparse_text: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Processes an existing document in PostgreSQL by document UUID."""
        t0 = time.time()
        doc = await self.session.get(Document, document_id)
        if not doc:
            logger.error("Document %s not found in database.", document_id)
            return None

        ver_res = await self.session.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == doc.id,
                DocumentVersion.is_current == True,
            )
        )
        version = ver_res.scalar_one_or_none()
        if not version:
            logger.error("Current version for document %s not found.", document_id)
            return None

        # Resolve raw file on disk
        pdf_path = STORAGE_UPLOADS_DIR / f"{document_id}.pdf"
        if not pdf_path.exists():
            matches = list(STORAGE_UPLOADS_DIR.glob(f"*{document_id}*"))
            if matches:
                pdf_path = matches[0]
            else:
                sub_matches = list((STORAGE_UPLOADS_DIR / str(document_id)).glob("*"))
                if sub_matches:
                    pdf_path = sub_matches[0]

        raw_bytes = b""
        filename = f"{doc.title}.pdf"
        if pdf_path.exists() and pdf_path.is_file():
            raw_bytes = pdf_path.read_bytes()
            filename = pdf_path.name

        # Parse text if needed
        content_text = doc.content_uri or version.content_uri or ""
        if reparse_text or len(content_text.strip()) < 500:
            if raw_bytes:
                parsed_doc = UniversalFileParser.parse_structured(
                    filename=filename,
                    raw_bytes=raw_bytes,
                    doc_title=doc.title,
                )
                content_text = parsed_doc.full_text
                new_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
                doc.content_uri = content_text
                doc.content_hash = new_hash
                version.content_uri = content_text
                version.content_hash = new_hash
                await self.session.commit()

        # Run TRULIN 6-Layer Pipeline
        if raw_bytes and content_text:
            canonical_env = EnvelopeFactory.create_from_file_upload(
                filename=filename,
                raw_bytes=raw_bytes,
                parsed_content=content_text,
                organization_id=doc.organization_id,
                source_id=doc.source_id,
                document_type=doc.document_type or "policy",
                source_intent=SourceIntent.GOVERNANCE_POLICY,
            )
            evidence_result = await DocumentParser.parse(canonical_env)
            l5_res = await global_extraction_pipeline.process_envelope(canonical_env, evidence_result)
            await global_validation_gate.process_extraction_result(
                canonical_env, l5_res, session=self.session, document_version_id=version.id
            )
            await self.session.commit()

        # Fine-grained atomic claims extraction
        claim_ext_svc = ClaimExtractionService(self.session, llm_provider=self.llm)
        await claim_ext_svc.extract_claims_from_version(version.id)
        await self.session.commit()

        # Conflicts and Trust
        conf_svc = ConflictService(self.session, llm_provider=self.llm)
        conflicts = await conf_svc.run_conflict_detection_for_version(version.id)

        trust_svc = TrustService(self.session)
        await trust_svc.calculate_for_version(version.id)
        await self.session.commit()

        total_claims_res = await self.session.execute(
            select(Claim).where(Claim.document_version_id == version.id)
        )
        total_claims = total_claims_res.scalars().all()

        total_duration = time.time() - t0
        return {
            "document_id": str(doc.id),
            "version_id": str(version.id),
            "title": doc.title,
            "filename": filename,
            "char_count": len(content_text),
            "claims_count": len(total_claims),
            "conflicts_count": len(conflicts),
            "duration_seconds": round(total_duration, 2),
        }


async def run_pipeline_cli():
    """Universal CLI entrypoint for batch document processing and re-extraction."""
    parser = argparse.ArgumentParser(
        description="Universal Document Pipeline: parse, extract claims, detect conflicts, and score trust for any file or document."
    )
    parser.add_argument("--doc-id", type=str, help="Specific document UUID to process")
    parser.add_argument("--file", type=str, help="Path to a local file to ingest")
    parser.add_argument("--all", action="store_true", help="Process all documents in the database")
    parser.add_argument("--filter", type=str, help="Filter documents by title match")
    parser.add_argument("--reparse", action="store_true", help="Force re-parsing raw PDF bytes with OCR")

    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        pipeline = UniversalDocumentPipeline(session)

        if args.file:
            path = Path(args.file)
            if not path.exists():
                print(f"Error: File '{args.file}' not found.")
                sys.exit(1)
            raw = path.read_bytes()
            org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
            print(f"Processing local file '{path.name}' ({len(raw)} bytes)...")
            res = await pipeline.process_file(
                filename=path.name,
                raw_bytes=raw,
                organization_id=org_id,
            )
            print(f"Result: {res['claims_count']} claims, {res['conflicts_count']} conflicts in {res['duration_seconds']}s")
            return

        if args.doc_id:
            doc_uuid = uuid.UUID(args.doc_id)
            print(f"Processing document UUID {doc_uuid} (reparse={args.reparse})...")
            res = await pipeline.process_existing_document(doc_uuid, reparse_text=args.reparse)
            if res:
                print(f"Result for '{res['title']}': {res['claims_count']} claims, {res['conflicts_count']} conflicts in {res['duration_seconds']}s")
            return

        stmt = select(Document)
        if args.filter:
            stmt = stmt.where(Document.title.ilike(f"%{args.filter}%"))
        docs_res = await session.execute(stmt)
        docs = docs_res.scalars().all()

        print(f"Found {len(docs)} documents to process.")
        for d in docs:
            print(f"\n--- Processing '{d.title}' ({d.id}) ---")
            res = await pipeline.process_existing_document(d.id, reparse_text=args.reparse)
            if res:
                print(f"  -> Extracted: {res['claims_count']} claims, {res['conflicts_count']} conflicts ({res['duration_seconds']}s)")


if __name__ == "__main__":
    asyncio.run(run_pipeline_cli())
