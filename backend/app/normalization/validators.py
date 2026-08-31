import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.normalization.normalizer import NormalizedDocument


class DocumentValidationError(ValueError):
    """Raised when a NormalizedDocument fails domain validation rules."""

    pass


def validate_normalized_document(doc: "NormalizedDocument") -> None:
    """Validates domain invariants for a canonical NormalizedDocument.

    Raises:
        DocumentValidationError: If any validation constraint is violated.
    """
    if not doc.title or not doc.title.strip():
        raise DocumentValidationError("Document title cannot be empty or whitespace.")

    if not doc.content or not doc.content.strip():
        raise DocumentValidationError("Document content cannot be empty or whitespace.")

    if not doc.document_type or not doc.document_type.strip():
        raise DocumentValidationError("Document type cannot be empty or whitespace.")

    if not isinstance(doc.id, uuid.UUID):
        raise DocumentValidationError(f"Invalid document id: expected UUID, got {type(doc.id).__name__}.")

    if not isinstance(doc.organization_id, uuid.UUID):
        raise DocumentValidationError(
            f"Invalid organization_id: expected UUID, got {type(doc.organization_id).__name__}."
        )

    if not isinstance(doc.source_id, uuid.UUID):
        raise DocumentValidationError(
            f"Invalid source_id: expected UUID, got {type(doc.source_id).__name__}."
        )

    if doc.metadata is not None and not isinstance(doc.metadata, dict):
        raise DocumentValidationError(
            f"Invalid metadata: expected dict, got {type(doc.metadata).__name__}."
        )

    if doc.created_at is not None and doc.updated_at is not None:
        if doc.updated_at < doc.created_at:
            raise DocumentValidationError(
                f"Inconsistent timestamps: updated_at ({doc.updated_at}) cannot be earlier than created_at ({doc.created_at})."
            )
