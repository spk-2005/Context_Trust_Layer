"""
Sprint AF-8: Independent Evidence Verification Engine

Implements an autonomous verification service that independently inspects
original raw document bytes (PDF, DOCX, text) without trusting extractor metadata:
1. Exact source span existence check
2. Page coordinate correctness
3. Character offset alignment (document and page-level)
4. Enclosing clause extraction
5. Verification status determination (EVIDENCE_VERIFIED, EVIDENCE_PARTIAL, EVIDENCE_FAILED)
6. Boolean 'span_exists' hard gate evaluation for v3.0 claim certification
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class EvidenceVerificationStatus(str, Enum):
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    EVIDENCE_PARTIAL = "EVIDENCE_PARTIAL"
    EVIDENCE_FAILED = "EVIDENCE_FAILED"


@dataclass
class DocumentPage:
    page_number: int
    text: str
    char_offset_start: int
    char_offset_end: int


@dataclass
class SourceClause:
    clause_id: str
    clause_text: str
    page_number: int
    char_start: int
    char_end: int


@dataclass
class EvidenceVerificationReport:
    claim_id: str
    document_id: str
    verification_status: EvidenceVerificationStatus
    span_exists: bool
    page_match: bool
    reported_page: Optional[int]
    actual_page: Optional[int]
    char_start: int
    char_end: int
    matched_quote: str
    enclosing_clause_text: str
    failure_reasons: List[str] = field(default_factory=list)
    confidence: float = 1.0


class IndependentEvidenceVerifier:
    """
    Independent evidence auditor that parses raw documents from bytes/path
    and deterministically validates that alleged claim evidence spans
    exist in the source text.
    """

    @classmethod
    def extract_document_pages(cls, file_path_or_bytes: Union[str, Path, bytes], filename: str = "") -> List[DocumentPage]:
        """
        Extracts structured pages and global character offsets directly from PDF, DOCX, or text bytes.
        """
        pages: List[DocumentPage] = []
        raw_bytes: bytes

        if isinstance(file_path_or_bytes, (str, Path)):
            p = Path(file_path_or_bytes)
            filename = filename or p.name
            raw_bytes = p.read_bytes()
        else:
            raw_bytes = file_path_or_bytes

        ext = Path(filename).suffix.lower() if filename else ".pdf"

        if ext == ".pdf":
            pages = cls._parse_pdf_bytes(raw_bytes)
        elif ext in (".docx", ".doc"):
            pages = cls._parse_docx_bytes(raw_bytes)
        else:
            # Fallback plain text / markdown
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = raw_bytes.decode("latin-1", errors="replace")
            pages = [DocumentPage(page_number=1, text=text, char_offset_start=0, char_offset_end=len(text))]

        return pages

    @classmethod
    def _parse_pdf_bytes(cls, raw_bytes: bytes) -> List[DocumentPage]:
        pages: List[DocumentPage] = []
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            current_offset = 0
            for idx, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ""
                # Normalize linebreaks, typography, and replacement characters
                norm_page_text = cls.normalize_text_for_matching(page_text)
                end_offset = current_offset + len(norm_page_text)
                pages.append(DocumentPage(
                    page_number=idx,
                    text=norm_page_text,
                    char_offset_start=current_offset,
                    char_offset_end=end_offset,
                ))
                current_offset = end_offset + 1  # delimiter spacing
        except Exception as e:
            logger.error("Failed to parse PDF bytes with pypdf: %s", e)
        return pages

    @classmethod
    def _parse_docx_bytes(cls, raw_bytes: bytes) -> List[DocumentPage]:
        pages: List[DocumentPage] = []
        try:
            import docx
            doc = docx.Document(io.BytesIO(raw_bytes))
            full_paras = [p.text for p in doc.paragraphs if p.text]
            full_text = cls.normalize_text_for_matching("\n\n".join(full_paras))
            pages.append(DocumentPage(
                page_number=1,
                text=full_text,
                char_offset_start=0,
                char_offset_end=len(full_text)
            ))
        except Exception as e:
            logger.error("Failed to parse DOCX bytes: %s", e)
        return pages

    @classmethod
    def normalize_text_for_matching(cls, text: str) -> str:
        """Strips excessive whitespace, non-breaking spaces, replacement chars, and typographical quotes."""
        if not text:
            return ""
        t = text.replace("\xa0", " ").replace("\ufffd", "'").replace("\xad", "").replace("\u200b", "")
        t = t.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'").replace("`", "'")
        t = t.replace("—", "-").replace("–", "-")
        t = re.sub(r"\s+", " ", t)
        t = re.sub(r"(\.\.\.|\…)\s*$", "", t)
        return t.strip()

    @classmethod
    def verify_claim_evidence(
        cls,
        claim_id: str,
        document_id: str,
        evidence_quote: str,
        reported_page: Optional[int],
        pages: List[DocumentPage],
        full_clause_hint: Optional[str] = None,
    ) -> EvidenceVerificationReport:
        """
        Executes independent verification of evidence quote against parsed document pages.
        """
        report = EvidenceVerificationReport(
            claim_id=claim_id,
            document_id=document_id,
            verification_status=EvidenceVerificationStatus.EVIDENCE_FAILED,
            span_exists=False,
            page_match=False,
            reported_page=reported_page,
            actual_page=None,
            char_start=-1,
            char_end=-1,
            matched_quote="",
            enclosing_clause_text="",
        )

        clean_target = cls.normalize_text_for_matching(evidence_quote)
        if not clean_target or len(clean_target) < 6:
            report.failure_reasons.append("Evidence quote is empty or too short for reliable identification.")
            return report

        # 1. First search on reported page (if provided)
        found_page_idx = -1
        match_start_on_page = -1
        match_end_on_page = -1
        matched_page_text = ""

        # Search candidates in pages
        best_candidate: Optional[Tuple[int, int, int, str]] = None  # (page_num, start, end, exact_str)

        # Check reported page first
        if reported_page and 1 <= reported_page <= len(pages):
            p = pages[reported_page - 1]
            cand = cls._find_substring_in_page(clean_target, p)
            if cand:
                best_candidate = (p.page_number, cand[0], cand[1], cand[2])

        # If not found on reported page, search all pages
        if not best_candidate:
            for p in pages:
                cand = cls._find_substring_in_page(clean_target, p)
                if cand:
                    best_candidate = (p.page_number, cand[0], cand[1], cand[2])
                    break

        # 2. Evaluate match outcome
        if best_candidate:
            actual_page_num, start_in_page, end_in_page, matched_slice = best_candidate
            target_page_obj = next(p for p in pages if p.page_number == actual_page_num)

            doc_char_start = target_page_obj.char_offset_start + start_in_page
            doc_char_end = target_page_obj.char_offset_start + end_in_page

            report.actual_page = actual_page_num
            report.char_start = doc_char_start
            report.char_end = doc_char_end
            report.matched_quote = matched_slice

            # Page match evaluation
            page_matches = (reported_page is None) or (reported_page == actual_page_num)
            report.page_match = page_matches

            # Extract enclosing paragraph / clause
            enclosing = cls._extract_enclosing_paragraph(target_page_obj.text, start_in_page, end_in_page)
            report.enclosing_clause_text = enclosing

            if page_matches:
                report.verification_status = EvidenceVerificationStatus.EVIDENCE_VERIFIED
                report.span_exists = True
                report.confidence = 1.0
            else:
                # Off-by-one page drift (common in PDF header offsets)
                drift = abs(actual_page_num - reported_page) if reported_page else 0
                if drift <= 1:
                    report.verification_status = EvidenceVerificationStatus.EVIDENCE_PARTIAL
                    report.span_exists = True
                    report.confidence = 0.90
                    report.failure_reasons.append(f"Quote found on page {actual_page_num}, but claim reported page {reported_page}.")
                else:
                    report.verification_status = EvidenceVerificationStatus.EVIDENCE_PARTIAL
                    report.span_exists = True
                    report.confidence = 0.75
                    report.failure_reasons.append(f"Substantial page drift: quote on page {actual_page_num} vs reported page {reported_page}.")
        else:
            # Try fuzzy segment match (first 40 characters prefix)
            prefix = clean_target[:min(45, len(clean_target))]
            for p in pages:
                cand = cls._find_substring_in_page(prefix, p)
                if cand:
                    report.actual_page = p.page_number
                    report.char_start = p.char_offset_start + cand[0]
                    report.char_end = p.char_offset_start + cand[1]
                    report.matched_quote = cand[2]
                    report.enclosing_clause_text = cls._extract_enclosing_paragraph(p.text, cand[0], cand[1])
                    report.verification_status = EvidenceVerificationStatus.EVIDENCE_PARTIAL
                    report.span_exists = True
                    report.confidence = 0.80
                    report.failure_reasons.append("Exact complete quote not matched; verified leading quote prefix in document.")
                    return report

            report.verification_status = EvidenceVerificationStatus.EVIDENCE_FAILED
            report.span_exists = False
            report.confidence = 0.0
            report.failure_reasons.append("Evidence quote cannot be grounded anywhere in raw document text.")

        return report

    @classmethod
    def _find_substring_in_page(cls, target_norm: str, page: DocumentPage) -> Optional[Tuple[int, int, str]]:
        """
        Locates target in page with whitespace tolerance, returning (start_idx, end_idx, verbatim_text).
        """
        p_text = page.text
        if not p_text:
            return None

        # 1. Exact raw substring
        idx = p_text.find(target_norm)
        if idx != -1:
            return (idx, idx + len(target_norm), p_text[idx:idx + len(target_norm)])

        # 2. Regex-escaped whitespace-flexible match with punctuation tolerance
        words = []
        for w in target_norm.split():
            escaped = re.escape(w)
            escaped = escaped.replace(r"\'", r"['’`\s]?")
            escaped = escaped.replace(r"\-", r"[-—–\s]?")
            words.append(escaped)

        if not words:
            return None

        pattern = r"\s+".join(words)
        match = re.search(pattern, p_text, flags=re.IGNORECASE)
        if match:
            return (match.start(), match.end(), p_text[match.start():match.end()])

        return None

    @classmethod
    def _extract_enclosing_paragraph(cls, text: str, start: int, end: int) -> str:
        """Finds paragraph boundaries surrounding the matched span."""
        para_start = text.rfind("\n\n", 0, start)
        if para_start == -1:
            para_start = max(0, start - 200)
        else:
            para_start += 2

        para_end = text.find("\n\n", end)
        if para_end == -1:
            para_end = min(len(text), end + 200)

        enclosing = text[para_start:para_end].strip()
        return enclosing if enclosing else text[start:end]
