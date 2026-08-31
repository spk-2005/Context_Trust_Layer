import uuid
import pytest

from app.normalization.metadata import build_metadata


def test_build_metadata_merge():
    extra = {"custom_field": "val1", "priority": "low"}
    result = build_metadata(extra_metadata=extra, priority="high", channel_id="C12345")

    assert result["custom_field"] == "val1"
    assert result["priority"] == "high"  # Explicit keyword argument overrides extra_metadata
    assert result["channel_id"] == "C12345"


def test_build_metadata_strips_canonical_keys():
    extra = {
        "title": "Leaked Title",
        "content": "Leaked Content",
        "organization_id": str(uuid.uuid4()),
        "source_url": "https://jira.enterprise.com/issue/1",
    }

    result = build_metadata(
        extra_metadata=extra,
        external_id="EXT-100",
        author="John Doe",
        priority="P2",
    )

    # Canonical keys must be stripped from metadata
    assert "title" not in result
    assert "content" not in result
    assert "organization_id" not in result
    assert "external_id" not in result

    # Non-canonical keys preserved
    assert result["source_url"] == "https://jira.enterprise.com/issue/1"
    assert result["priority"] == "P2"
