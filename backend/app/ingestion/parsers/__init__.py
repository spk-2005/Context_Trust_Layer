"""
Layer 4: Specialized Source-Family Parsers Package.
Exports universal evidence models and specialized parsers.
"""

from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.parsers.conversation_parser import ConversationParser
from app.ingestion.parsers.metadata_parser import MetadataParser

__all__ = [
    "ParsedEvidenceUnit",
    "ParsedEvidenceResult",
    "DocumentParser",
    "StructuredDataParser",
    "ConversationParser",
    "MetadataParser",
]
