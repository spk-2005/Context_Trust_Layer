from typing import Any

CANONICAL_DOCUMENT_KEYS = {
    "id",
    "organization_id",
    "source_id",
    "external_id",
    "document_type",
    "title",
    "content",
    "author",
    "created_at",
    "updated_at",
}


def build_metadata(
    extra_metadata: dict[str, Any] | None = None,
    **source_attributes: Any,
) -> dict[str, Any]:
    """Constructs and sanitizes a metadata dictionary for a NormalizedDocument.

    Merges extra_metadata and explicit source attributes while stripping any
    top-level canonical attributes to prevent key collision or duplication.
    """
    merged: dict[str, Any] = {}

    if extra_metadata:
        merged.update(extra_metadata)

    for k, v in source_attributes.items():
        if v is not None:
            merged[k] = v

    # Remove any canonical attributes that accidentally leaked into metadata
    sanitized = {
        key: val
        for key, val in merged.items()
        if key not in CANONICAL_DOCUMENT_KEYS
    }

    return sanitized

