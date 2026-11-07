"""
Layer 4: Specialized Source-Family Parsers Package.
Exports universal evidence models, typed locators, and specialized parsers.
"""

from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceExtractionValidator,
    EvidenceRelationship,
    EvidenceUnit,
    EvidenceValidationResult,
    ExtractionQualityReport,
    ExtractionStatus,
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
    SourceLocator,
    StructuralRelationType,
    compute_content_hash,
    compute_evidence_id,
    compute_evidence_instance_id,
)
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.parsers.conversation_parser import ConversationParser
from app.ingestion.parsers.metadata_parser import MetadataParser

__all__ = [
    "EvidenceUnit",
    "ParsedEvidenceUnit",
    "ParsedEvidenceResult",
    "ExtractionQualityReport",
    "EvidenceExtractionValidator",
    "EvidenceValidationResult",
    "SourceLocator",
    "ContentRole",
    "ExtractionStatus",
    "StructuralRelationType",
    "EvidenceRelationship",
    "compute_content_hash",
    "compute_evidence_id",
    "compute_evidence_instance_id",
    "DocumentParser",
    "StructuredDataParser",
    "ConversationParser",
    "MetadataParser",
]
