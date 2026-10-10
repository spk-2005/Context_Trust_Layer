import uuid
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import SourceFamily, SourceIntent


class SourceCapabilities(BaseModel):
    """Declared technical capabilities of an enterprise connector."""
    supports_incremental: bool = Field(default=False, description="Whether connector supports watermark/delta sync")
    supports_cdc: bool = Field(default=False, description="Whether connector supports change data capture")
    supports_schema_discovery: bool = Field(default=False, description="Whether connector can discover schemas/tables/collections")
    supports_granular_selection: bool = Field(default=False, description="Whether user can select specific entities/paths")
    supports_snapshots: bool = Field(default=True, description="Whether connector captures versioned snapshots")
    pagination_type: Literal["cursor", "offset", "page", "none"] = Field(default="none")
    native_identifier_field: str = Field(default="id", description="Primary key or native record identity field")
    supported_formats: list[str] = Field(default_factory=list, description="Native formats handled e.g. ['json', 'sql_row']")

    model_config = ConfigDict(extra="ignore")


class DocumentScopeConfig(BaseModel):
    """Scope configuration for DOCUMENT family sources (Files, Git, Wiki)."""
    file_globs: list[str] = Field(default_factory=lambda: ["**/*.md", "**/*.txt", "**/*.pdf", "**/*.docx"])
    excluded_paths: list[str] = Field(default_factory=lambda: ["node_modules/**", ".git/**", "vendor/**", "tests/**"])
    max_file_size_mb: int = Field(default=50, ge=1, le=500)
    include_subfolders: bool = Field(default=True)
    target_branches_or_spaces: list[str] = Field(default_factory=list)


class StructuredScopeConfig(BaseModel):
    """Scope configuration for STRUCTURED_DATA family sources (SQL, MongoDB, Warehouse)."""
    database: str | None = None
    schemas: list[str] = Field(default_factory=lambda: ["public"])
    selected_entities: list[str] = Field(default_factory=lambda: ["*"], description="Selected tables or collections ('*' for all)")
    excluded_entities: list[str] = Field(default_factory=list, description="Explicitly ignored tables or collections")
    column_whitelist: dict[str, list[str]] = Field(default_factory=dict, description="Entity -> list of columns to inspect")
    filter_predicates: dict[str, str] = Field(default_factory=dict, description="Entity -> SQL WHERE / Mongo query filter")
    sample_size: int = Field(default=100, ge=1, le=10000)
    extract_mode: Literal["schema_and_records", "schema_only", "records_only"] = Field(default="schema_and_records")


class ConversationScopeConfig(BaseModel):
    """Scope configuration for CONVERSATION family sources (Slack, Teams, Jira)."""
    channels_or_threads: list[str] = Field(default_factory=list, description="Selected channel IDs, thread keys, or project keys")
    include_replies: bool = True
    start_date: str | None = None
    min_reactions_threshold: int = Field(default=0, ge=0)
    include_bot_messages: bool = False


class MetadataScopeConfig(BaseModel):
    """Scope configuration for METADATA_OPERATIONAL family sources (BI, Lineage, Configs)."""
    metric_keys: list[str] = Field(default_factory=list, description="Specific BI measures or KPIs to extract")
    model_names: list[str] = Field(default_factory=list, description="Specific dbt / semantic models")
    include_upstream_lineage: bool = True
    config_namespaces: list[str] = Field(default_factory=list)


class ScopeConfiguration(BaseModel):
    """Unified container for Layer 1 source scoping."""
    source_family: SourceFamily = SourceFamily.DOCUMENT
    source_intent: SourceIntent = SourceIntent.GOVERNANCE_POLICY
    document_scope: DocumentScopeConfig | None = None
    structured_scope: StructuredScopeConfig | None = None
    conversation_scope: ConversationScopeConfig | None = None
    metadata_scope: MetadataScopeConfig | None = None
    custom_options: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class SourceInventoryItem(BaseModel):
    """Individual item discovered in a data source for customer selection (harmonized with DiscoveredAsset)."""
    id: str = Field(..., description="Unique entity name or path (e.g. table name, collection, repo path, channel)")
    name: str = Field(..., description="Human readable label")
    item_type: str = Field(default="entity", description="table, view, collection, file, directory, channel, space, project, metric")
    asset_type: str | None = Field(default=None, description="Layer 2 name for item_type")
    parent: str | None = None
    parent_scope: str | None = None
    is_selectable: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.asset_type is None:
            self.asset_type = self.item_type
        if self.parent_scope is None:
            self.parent_scope = self.parent


# DiscoveredAsset alias for Layer 2 compatibility
DiscoveredAsset = SourceInventoryItem


class SourceInventoryResponse(BaseModel):
    """Response returned when discovering available assets in a source."""
    source_id: uuid.UUID | None = None
    source_type: str
    source_family: SourceFamily
    items: list[SourceInventoryItem] = Field(default_factory=list)
    assets: list[SourceInventoryItem] = Field(default_factory=list)
    total_count: int = 0
    discovered_at: str

    def model_post_init(self, __context: Any) -> None:
        if not self.assets and self.items:
            self.assets = self.items
        elif not self.items and self.assets:
            self.items = self.assets

