"""
Manifest Initializer for Sprint AD: 50-Document Validation.

Scans `research/validation_50/raw_documents/` and automatically compiles
`research/validation_50/document_manifest.json` with cryptographic SHA-256 signatures,
detected document types, page counts, and metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DOCS_DIR = Path("B:/Context_Layer_Ai/research/validation_50/raw_documents")
DEFAULT_MANIFEST_PATH = Path("B:/Context_Layer_Ai/research/validation_50/document_manifest.json")


def detect_document_type(path: Path | str) -> str:
    """Infers document category from parent directory and filename semantics."""
    p = Path(path)
    fn = p.name.lower()
    parent = p.parent.name.lower() if len(p.parts) > 1 else ""

    if any(k in fn for k in ("scanned", "ocr", "receipt_scan", "image_scan")):
        return "scanned_document"
    if "refund" in parent or any(k in fn for k in ("refund", "return", "cancellation", "exchange")):
        return "refund_policy"
    if "invoice" in parent or any(k in fn for k in ("invoice", "billing", "receipt", "order", "charge", "tax forms")):
        return "invoice"
    if "hr" in parent or any(k in fn for k in ("hr", "employment", "leave", "conduct", "handbook", "remote", "human-rights")):
        return "hr_policy"
    if "contract" in parent or any(k in fn for k in ("vendor", "agreement", "contract", "nda", "sla", "master", "covenant", "po-terms", "licensing", "terms", "enrollment")):
        return "contract"
    if "technical" in parent or any(k in fn for k in ("entra", "deployment", "operations guide", "architecture", "security operations")):
        return "technical_documentation"
    if "difficult" in parent or any(k in fn for k in ("dpa", "regulatory", "compliance", "gdpr", "hipaa", "privacy", "security", "soc2", "assurance")):
        return "regulatory_compliance"
    if any(k in fn for k in ("table", "matrix", "schedule", "pricing")):
        return "table_heavy"
    return "general_policy"


def get_pdf_page_count(path: Path) -> int:
    """Extracts page count from PDF using pypdf if available, else estimates."""
    if not path.name.lower().endswith(".pdf"):
        return 1
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return len(reader.pages)
    except Exception:
        # Fallback regex search for /Type /Page
        try:
            raw = path.read_bytes()
            pages = raw.count(b"/Type /Page\n") + raw.count(b"/Type /Page ") + raw.count(b"/Type/Page")
            return max(1, pages)
        except Exception:
            return 1


def build_manifest(raw_docs_dir: Path, output_manifest: Path) -> Dict[str, Any]:
    raw_docs_dir.mkdir(parents=True, exist_ok=True)
    # Recursively find all documents, ignoring hidden/temp files
    files = sorted([
        f for f in raw_docs_dir.rglob("*")
        if f.is_file() and not f.name.startswith((".", "~$")) and f.suffix.lower() in (
            ".pdf", ".docx", ".doc", ".md", ".txt", ".json", ".csv"
        )
    ])

    if not files:
        logger.warning(
            "No files found in %s! Place your documents into this folder, then rerun this script.",
            raw_docs_dir,
        )

    documents: Dict[str, Any] = {}
    type_counts: Dict[str, int] = {}

    for idx, f in enumerate(files, start=51):
        doc_id = f"DOC-{idx:03d}"
        file_bytes = f.read_bytes()
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        doc_type = detect_document_type(f)
        page_count = get_pdf_page_count(f)

        type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        documents[doc_id] = {
            "document_id": doc_id,
            "filename": f.name,
            "file_path": str(f.resolve()),
            "source_sha256": sha256,
            "file_size_bytes": len(file_bytes),
            "document_type": doc_type,
            "page_count": page_count,
            "organization": "Enterprise Validation Corpus",
            "tier": "tier_1",
            "audit_status": "PENDING",
        }

    manifest = {
        "manifest_version": "1.0",
        "milestone": "Sprint AD: 50-Document Parsing and Claim Validation",
        "total_documents": len(documents),
        "document_type_distribution": type_counts,
        "documents": documents,
    }

    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Manifest created at %s with %d documents.", output_manifest, len(documents))
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Build document_manifest.json from raw_documents directory")
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR, help="Path to folder containing documents")
    parser.add_argument("--output", type=Path, default=DEFAULT_MANIFEST_PATH, help="Path for generated manifest JSON")

    args = parser.parse_args()
    build_manifest(args.docs_dir, args.output)


if __name__ == "__main__":
    main()