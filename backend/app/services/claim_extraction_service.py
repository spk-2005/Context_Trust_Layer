import asyncio
import hashlib
import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document_version import DocumentVersion
from app.db.repositories.claim_repository import ClaimRepository
from app.db.repositories.document_repository import DocumentRepository
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.normalization.normalizer import DocumentNormalizer


class ClaimExtractionService:
    """Extracts atomic claims, exact evidence spans, and validity from normalized documents."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.claim_repo = ClaimRepository(session)
        self.normalizer = DocumentNormalizer()
        self.llm = llm_provider or get_llm_provider()

    @staticmethod
    def calculate_evidence_hash(text_span: str) -> str:
        return hashlib.sha256(text_span.encode("utf-8")).hexdigest()

    async def extract_claims_from_version(
        self,
        document_version_id: uuid.UUID,
    ) -> Sequence[Claim]:
        """Extract claims for a specific document version and persist in database.

        All document sections are processed in parallel via asyncio.gather so
        Ollama (or any async LLM provider) handles them concurrently rather
        than one-at-a-time, reducing wall-clock time by N x for N sections.
        """
        # 1. Fetch document version and parent document
        version = await self.session.get(DocumentVersion, document_version_id)
        if not version:
            raise ValueError(f"Document version {document_version_id} not found.")

        doc = await self.doc_repo.get_by_id(version.document_id)
        if not doc:
            raise ValueError(f"Parent document for version {document_version_id} not found.")

        raw_text = version.content_uri or ""
        normalized = self.normalizer.normalize(
            document_id=doc.id,
            document_version_id=version.id,
            title=doc.title,
            raw_text=raw_text,
        )

        # 2. Extract all sections in PARALLEL with noise scrubbing and entity anchoring
        async def _extract_section(section):
            scrubbed_content = self.normalizer.scrub_noise(section.content)
            if not scrubbed_content.strip():
                scrubbed_content = section.content

            # Provide qualified hierarchical section title
            sec_display = section.title or "General"
            qualified_sec_title = f"{doc.title} > {sec_display}" if sec_display != "General" else doc.title

            return section, await self.llm.extract_claims(
                document_title=doc.title,
                section_title=qualified_sec_title,
                section_content=scrubbed_content,
            )

        section_results = await asyncio.gather(
            *[_extract_section(s) for s in normalized.sections],
            return_exceptions=False,
        )

        extracted_claim_records: list[Claim] = []
        claim_cache: dict[str, Claim] = {}

        # 3. Persist results with Canonical Deduplication & Multi-Citation Lineage
        for section, result in section_results:
            for item in result.claims:
                # 3a. Generate canonical multi-factor matching keys
                norm_text_key = " ".join(item.claim_text.strip().lower().split())
                
                sub_clean = (item.subject or "").strip().lower()
                pred_clean = (item.predicate or "").strip().lower()
                obj_clean = (item.object or "").strip().lower()
                spo_key = f"{sub_clean}::{pred_clean}::{obj_clean}" if (sub_clean and pred_clean) else None
                
                num_key = None
                if item.numeric_value is not None and sub_clean and pred_clean:
                    num_key = f"{sub_clean}::{pred_clean}::{item.numeric_value}::{item.numeric_unit or ''}"

                # 3b. Check canonical cache
                claim = (
                    claim_cache.get(norm_text_key)
                    or (claim_cache.get(spo_key) if spo_key else None)
                    or (claim_cache.get(num_key) if num_key else None)
                )

                if not claim:
                    claim = Claim(
                        organization_id=doc.organization_id,
                        document_version_id=version.id,
                        claim_text=item.claim_text,
                        subject=item.subject,
                        predicate=item.predicate,
                        object=item.object,
                        claim_type=item.claim_type,
                        extraction_method=result.extraction_method,
                        extraction_model=result.extraction_model,
                        status=ClaimStatus.ACTIVE,
                    )
                    self.session.add(claim)
                    await self.session.flush()
                    await self.session.refresh(claim)
                    
                    # Register canonical keys
                    claim_cache[norm_text_key] = claim
                    if spo_key:
                        claim_cache[spo_key] = claim
                    if num_key:
                        claim_cache[num_key] = claim
                        
                    extracted_claim_records.append(claim)

                    validity = ClaimValidity(
                        claim_id=claim.id,
                        valid_from=item.valid_from,
                        valid_until=item.valid_until,
                        version=str(version.version_number),
                        is_current=version.is_current,
                        validity_status="active" if version.is_current else "outdated",
                    )
                    self.session.add(validity)

                # 3c. Always attach evidence citation (direct quote span, hash, section)
                text_span = item.evidence_text_span or item.claim_text
                start_offset = section.start_char_offset
                end_offset = section.end_char_offset

                span_idx = raw_text.find(text_span)
                if span_idx != -1:
                    start_offset = span_idx
                    end_offset = span_idx + len(text_span)

                evidence = ClaimEvidence(
                    claim_id=claim.id,
                    document_id=doc.id,
                    evidence_type="direct_quote",
                    section=section.title,
                    text_span=text_span,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    evidence_hash=self.calculate_evidence_hash(text_span),
                    page_number=section.page_number or 1,
                )
                self.session.add(evidence)

        await self.session.flush()
        return extracted_claim_records
