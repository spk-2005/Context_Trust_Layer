import uuid
from datetime import datetime, timezone
import pytest

from app.normalization.normalizer import DocumentNormalizer
from app.normalization.validators import DocumentValidationError, validate_normalized_document


def test_validator_empty_title_rejection():
    normalizer = DocumentNormalizer()
    with pytest.raises(DocumentValidationError, match="title cannot be empty"):
        normalizer.normalize(
            title="   ",
            content="Valid content",
            organization_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
        )


def test_validator_empty_content_rejection():
    normalizer = DocumentNormalizer()
    with pytest.raises(DocumentValidationError, match="content cannot be empty"):
        normalizer.normalize(
            title="Valid Title",
            content="   \n\t ",
            organization_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
        )


def test_validator_empty_document_type_rejection():
    normalizer = DocumentNormalizer()
    with pytest.raises(DocumentValidationError, match="type cannot be empty"):
        normalizer.normalize(
            title="Valid Title",
            content="Valid content",
            organization_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            document_type="   ",
        )


def test_validator_inconsistent_timestamps_rejection():
    normalizer = DocumentNormalizer()
    now = datetime.now(timezone.utc)
    earlier = datetime(2020, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(DocumentValidationError, match="Inconsistent timestamps"):
        normalizer.normalize(
            title="Valid Title",
            content="Valid content",
            organization_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            created_at=now,
            updated_at=earlier,
        )


def test_validator_invalid_uuid_types():
    normalizer = DocumentNormalizer()
    doc = normalizer.normalize(
        title="Valid Title",
        content="Valid Content",
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
    )

    # Mutate to invalid UUID type
    doc.organization_id = "invalid-uuid-string"
    with pytest.raises(DocumentValidationError, match="expected UUID"):
        validate_normalized_document(doc)
