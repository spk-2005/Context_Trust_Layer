"""
Connector Registry
==================

Central registry for all Context Trust Layer connectors.

The connector catalog is stored in:

    backend/app/ingestion/connector_catalog.json

The registry is responsible for:

    1. Loading connector metadata.
    2. Validating catalog entries.
    3. Looking up connectors by id.
    4. Supporting connector aliases.
    5. Returning lifecycle capabilities.
    6. Returning configuration fields for the frontend/API.
    7. Identifying native versus universal-driver connectors.
    8. Providing backward-compatible ConnectorMetadata objects.

Lifecycle:

    Configure
        ↓
    Authenticate
        ↓
    Test
        ↓
    Discover
        ↓
    Select
        ↓
    Initial Sync
        ↓
    Continuous Sync
        ↓
    Normalize
        ↓
    Provenance
        ↓
    Conflict Detection
        ↓
    Lineage
        ↓
    Monitoring
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, ConfigDict, Field


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

REGISTRY_FILE = Path(__file__).resolve().parent / "connector_catalog.json"


# ---------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------

CONNECTOR_LIFECYCLE: tuple[str, ...] = (
    "configure",
    "authenticate",
    "test",
    "discover",
    "select",
    "initial_sync",
    "continuous_sync",
    "normalize",
    "provenance",
    "conflict_detection",
    "lineage",
    "monitoring",
)


# ---------------------------------------------------------------------
# Native connectors currently implemented in the application
# ---------------------------------------------------------------------

NATIVE_CONNECTORS: frozenset[str] = frozenset(
    {
        "postgresql",
        "postgres",
        "kafka",
        "apache_kafka",
        "confluent",
        "salesforce",
        "sfdc",
        "salesforce_crm",
        "mongodb",
        "mongo",
        "mongo_atlas",
        "confluence",
        "wiki",
        "jira",
        "jira_issues",
        "github",
        "git",
        "repo",
        "slack",
        "slack_channels",
    }
)


# ---------------------------------------------------------------------
# Connector metadata model
# ---------------------------------------------------------------------


class ConnectorMetadata(BaseModel):
    """
    Normalized metadata representation for a connector.

    The JSON catalog can contain additional fields. Pydantic is
    configured to preserve those fields rather than throwing them away.
    """

    model_config = ConfigDict(extra="allow")

    id: str

    name: str

    category: str = "custom"

    category_label: str = "Custom Source"

    family: str = "enterprise_app"

    description: str = ""

    default_port: Optional[int] = None

    default_auth: str = "password"

    doc_type: str = "data_contract"

    monitored_scope: str = (
        "Enterprise data and policy synchronization."
    )

    # Optional catalog fields.
    aliases: List[str] = Field(default_factory=list)

    fields: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    capabilities: Dict[str, Any] = Field(
        default_factory=dict
    )

    driver: str = "universal"

    status: str = "active"

    enabled: bool = True

    # -----------------------------------------------------------------
    # Compatibility properties
    # -----------------------------------------------------------------

    @property
    def connector_id(self) -> str:
        """Backward-compatible connector id."""
        return self.id

    @property
    def display_name(self) -> str:
        """Human-readable connector name."""
        return self.name

    @property
    def is_native(self) -> bool:
        """Whether a native connector implementation exists."""
        return (
            self.driver == "native"
            or self.id in NATIVE_CONNECTORS
        )

    @property
    def is_universal(self) -> bool:
        """Whether the connector uses the universal driver."""
        return not self.is_native

    @property
    def lifecycle(self) -> List[str]:
        """
        Return lifecycle stages supported by the connector.

        A connector can override the catalog capabilities, but all
        connectors inherit the complete Context Trust Layer lifecycle.
        """

        configured = self.capabilities.get("lifecycle")

        if isinstance(configured, list) and configured:
            return list(configured)

        return list(CONNECTOR_LIFECYCLE)

    @property
    def required_fields(self) -> List[Dict[str, Any]]:
        """
        Return configuration fields required by this connector.

        Catalog-defined fields take precedence.

        Legacy defaults are retained for compatibility with the old
        registry implementation.
        """

        if self.fields:
            return self.fields

        return self._legacy_required_fields()

    def _legacy_required_fields(self) -> List[Dict[str, Any]]:
        """
        Compatibility field definitions for catalog entries that don't
        explicitly define fields.
        """

        connector_id = self.id.lower()

        if connector_id in (
            "github",
            "git",
            "repo",
        ):
            return [
                {
                    "id": "repository",
                    "label": "Repository (owner/repo)",
                    "type": "text",
                    "required": True,
                },
                {
                    "id": "branch",
                    "label": "Branch",
                    "type": "text",
                    "required": False,
                    "default": "main",
                },
                {
                    "id": "access_token",
                    "label": "Personal Access Token",
                    "type": "password",
                    "required": False,
                    "secret": True,
                },
            ]

        if connector_id in (
            "postgresql",
            "postgres",
            "mysql",
            "sql_server",
            "mssql",
            "oracle",
            "snowflake",
        ):
            return [
                {
                    "id": "host",
                    "label": "Host",
                    "type": "text",
                    "required": True,
                },
                {
                    "id": "port",
                    "label": "Port",
                    "type": "number",
                    "required": False,
                    "default": self.default_port,
                },
                {
                    "id": "database",
                    "label": "Database",
                    "type": "text",
                    "required": True,
                },
                {
                    "id": "username",
                    "label": "Username",
                    "type": "text",
                    "required": True,
                },
                {
                    "id": "password",
                    "label": "Password",
                    "type": "password",
                    "required": True,
                    "secret": True,
                },
            ]

        if connector_id in (
            "kafka",
            "apache_kafka",
            "confluent",
        ):
            return [
                {
                    "id": "bootstrap_servers",
                    "label": "Bootstrap Servers",
                    "type": "text",
                    "required": True,
                },
                {
                    "id": "topic",
                    "label": "Topic",
                    "type": "text",
                    "required": False,
                },
                {
                    "id": "security_protocol",
                    "label": "Security Protocol",
                    "type": "select",
                    "required": False,
                    "default": "PLAINTEXT",
                    "options": [
                        "PLAINTEXT",
                        "SSL",
                        "SASL_PLAINTEXT",
                        "SASL_SSL",
                    ],
                },
            ]

        if connector_id in (
            "jira",
            "jira_issues",
            "confluence",
            "wiki",
        ):
            return [
                {
                    "id": "base_url",
                    "label": "Base URL",
                    "type": "url",
                    "required": True,
                },
                {
                    "id": "user_email",
                    "label": "User Email",
                    "type": "email",
                    "required": True,
                },
                {
                    "id": "api_token",
                    "label": "API Token",
                    "type": "password",
                    "required": True,
                    "secret": True,
                },
            ]

        if connector_id in (
            "salesforce",
            "sfdc",
            "salesforce_crm",
        ):
            return [
                {
                    "id": "instance_url",
                    "label": "Salesforce Instance URL",
                    "type": "url",
                    "required": True,
                },
                {
                    "id": "access_token",
                    "label": "Access Token",
                    "type": "password",
                    "required": True,
                    "secret": True,
                },
            ]

        if connector_id in (
            "mongodb",
            "mongo",
            "mongo_atlas",
        ):
            return [
                {
                    "id": "connection_string",
                    "label": "MongoDB Connection String",
                    "type": "password",
                    "required": True,
                    "secret": True,
                },
                {
                    "id": "database",
                    "label": "Database",
                    "type": "text",
                    "required": True,
                },
            ]

        # Generic connector configuration.
        return [
            {
                "id": "endpoint",
                "label": "Host / Endpoint",
                "type": "text",
                "required": True,
            },
            {
                "id": "token",
                "label": "API Key / Token",
                "type": "password",
                "required": False,
                "secret": True,
            },
        ]

    # -----------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------

    def to_public_dict(
        self,
        *,
        include_secrets: bool = False,
    ) -> Dict[str, Any]:
        """
        Return metadata safe for API/frontend consumption.

        Secret values are never stored in metadata itself, but field
        definitions can mark fields as secret. This method strips any
        catalog-level secret-like keys as an additional safeguard.
        """

        data = self.model_dump()

        data["lifecycle"] = self.lifecycle

        data["is_native"] = self.is_native

        data["is_universal"] = self.is_universal

        data["required_fields"] = self.required_fields

        if not include_secrets:
            secret_keys = {
                "password",
                "secret",
                "client_secret",
                "access_token",
                "api_token",
                "token",
                "private_key",
            }

            for key in list(data.keys()):
                if key.lower() in secret_keys:
                    data.pop(key, None)

        return data


# ---------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------


class ConnectorRegistry:
    """
    Singleton-style registry backed by connector_catalog.json.

    Usage:

        ConnectorRegistry.get_by_id("postgresql")

        ConnectorRegistry.list()

        ConnectorRegistry.list_by_category("database")

        ConnectorRegistry.get_configuration_schema("github")
    """

    _connectors: Dict[str, ConnectorMetadata] = {}

    _aliases: Dict[str, str] = {}

    _loaded: bool = False

    _catalog_path: Path = REGISTRY_FILE

    # -----------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: Optional[str | Path] = None,
        *,
        force: bool = False,
    ) -> Dict[str, ConnectorMetadata]:
        """
        Load the connector catalog.

        The catalog is loaded lazily the first time the registry is
        queried.
        """

        if cls._loaded and not force:
            return cls._connectors

        catalog_path = (
            Path(path)
            if path is not None
            else cls._catalog_path
        )

        cls._connectors = {}
        cls._aliases = {}

        if not catalog_path.exists():
            logger.warning(
                "Connector catalog not found: %s",
                catalog_path,
            )

            cls._loaded = True
            return cls._connectors

        try:
            with catalog_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                raw_catalog = json.load(file)

        except json.JSONDecodeError as exc:
            logger.exception(
                "Invalid connector catalog JSON: %s",
                catalog_path,
            )
            raise ValueError(
                f"Invalid connector catalog JSON: {exc}"
            ) from exc

        except OSError as exc:
            logger.exception(
                "Unable to read connector catalog: %s",
                catalog_path,
            )
            raise RuntimeError(
                f"Unable to read connector catalog: {exc}"
            ) from exc

        entries = cls._extract_entries(raw_catalog)

        for raw_entry in entries:
            try:
                metadata = cls._normalize_entry(raw_entry)
            except Exception as exc:
                connector_id = (
                    raw_entry.get("id", "<unknown>")
                    if isinstance(raw_entry, dict)
                    else "<invalid>"
                )

                logger.warning(
                    "Skipping invalid connector '%s': %s",
                    connector_id,
                    exc,
                )

                continue

            if not metadata.enabled:
                continue

            connector_id = metadata.id.lower().strip()

            if not connector_id:
                continue

            metadata.id = connector_id

            cls._connectors[connector_id] = metadata

            # Canonical id is always an alias to itself.
            cls._aliases[connector_id] = connector_id

            # Explicit aliases.
            for alias in metadata.aliases:
                alias_key = cls._normalize_key(alias)

                if alias_key:
                    cls._aliases[alias_key] = connector_id

        # Native connectors should remain resolvable even if the
        # catalog was created before the native implementation existed.
        cls._register_native_aliases()

        cls._loaded = True

        logger.info(
            "Loaded %d connectors from %s",
            len(cls._connectors),
            catalog_path,
        )

        return cls._connectors

    @classmethod
    def reload(
        cls,
    ) -> Dict[str, ConnectorMetadata]:
        """Force a catalog reload."""
        return cls.load(force=True)

    # -----------------------------------------------------------------
    # Catalog extraction
    # -----------------------------------------------------------------

    @classmethod
    def _extract_entries(
        cls,
        catalog: Any,
    ) -> List[Dict[str, Any]]:
        """
        Support multiple catalog JSON layouts.

        Supported:

            [
                {...},
                {...}
            ]

        or:

            {
                "connectors": [...]
            }

        or:

            {
                "catalog": [...]
            }

        or:

            {
                "data": [...]
            }
        """

        if isinstance(catalog, list):
            return [
                item
                for item in catalog
                if isinstance(item, dict)
            ]

        if not isinstance(catalog, dict):
            raise ValueError(
                "Connector catalog must be a JSON array or object."
            )

        for key in (
            "connectors",
            "catalog",
            "data",
            "items",
        ):
            value = catalog.get(key)

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

        # Allow a mapping of connector id -> metadata.
        if all(
            isinstance(value, dict)
            for value in catalog.values()
        ):
            entries: List[Dict[str, Any]] = []

            for connector_id, value in catalog.items():
                entry = dict(value)
                entry.setdefault("id", connector_id)
                entries.append(entry)

            return entries

        return []

    # -----------------------------------------------------------------
    # Entry normalization
    # -----------------------------------------------------------------

    @classmethod
    def _normalize_entry(
        cls,
        entry: Dict[str, Any],
    ) -> ConnectorMetadata:
        """Normalize one JSON connector entry."""

        data = dict(entry)

        connector_id = (
            data.get("id")
            or data.get("connector_id")
            or data.get("slug")
            or data.get("key")
        )

        if not connector_id:
            raise ValueError(
                "Connector entry is missing id."
            )

        connector_id = cls._normalize_key(
            str(connector_id)
        )

        name = (
            data.get("name")
            or data.get("display_name")
            or connector_id.replace("_", " ").title()
        )

        category = (
            data.get("category")
            or data.get("type")
            or "custom"
        )

        family = (
            data.get("family")
            or data.get("connector_family")
            or "enterprise_app"
        )

        category_label = (
            data.get("category_label")
            or data.get("categoryLabel")
            or cls._category_label(category)
        )

        description = (
            data.get("description")
            or ""
        )

        default_auth = (
            data.get("default_auth")
            or data.get("defaultAuth")
            or data.get("auth_type")
            or "password"
        )

        default_port = (
            data.get("default_port")
            or data.get("defaultPort")
        )

        if default_port is not None:
            try:
                default_port = int(default_port)
            except (TypeError, ValueError):
                default_port = None

        doc_type = (
            data.get("doc_type")
            or data.get("docType")
            or "data_contract"
        )

        monitored_scope = (
            data.get("monitored_scope")
            or data.get("monitoredScope")
            or "Enterprise data and policy synchronization."
        )

        aliases = data.get("aliases") or []

        if isinstance(aliases, str):
            aliases = [aliases]

        fields = (
            data.get("fields")
            or data.get("configuration")
            or data.get("config_fields")
            or []
        )

        if not isinstance(fields, list):
            fields = []

        capabilities = data.get(
            "capabilities"
        ) or {}

        if not isinstance(capabilities, dict):
            capabilities = {}

        driver = (
            data.get("driver")
            or data.get("driver_type")
            or data.get("implementation")
        )

        if not driver:
            driver = (
                "native"
                if connector_id in NATIVE_CONNECTORS
                else "universal"
            )

        status = (
            data.get("status")
            or data.get("availability")
            or "active"
        )

        enabled = data.get(
            "enabled",
            True,
        )

        normalized = {
            **data,
            "id": connector_id,
            "name": name,
            "category": category,
            "category_label": category_label,
            "family": family,
            "description": description,
            "default_port": default_port,
            "default_auth": default_auth,
            "doc_type": doc_type,
            "monitored_scope": monitored_scope,
            "aliases": aliases,
            "fields": fields,
            "capabilities": capabilities,
            "driver": driver,
            "status": status,
            "enabled": bool(enabled),
        }

        return ConnectorMetadata(**normalized)

    # -----------------------------------------------------------------
    # Lookup
    # -----------------------------------------------------------------

    @classmethod
    def get_by_id(
        cls,
        connector_id: Optional[str],
    ) -> Optional[ConnectorMetadata]:
        """
        Resolve a connector by canonical id or alias.
        """

        if not connector_id:
            return None

        cls.load()

        key = cls._normalize_key(connector_id)

        canonical_id = cls._aliases.get(
            key,
            key,
        )

        return cls._connectors.get(
            canonical_id
        )

    @classmethod
    def get(
        cls,
        connector_id: Optional[str],
    ) -> Optional[ConnectorMetadata]:
        """Alias for get_by_id()."""
        return cls.get_by_id(connector_id)

    @classmethod
    def require(
        cls,
        connector_id: str,
    ) -> ConnectorMetadata:
        """
        Resolve a connector or raise a clear ValueError.
        """

        connector = cls.get_by_id(connector_id)

        if connector is None:
            raise ValueError(
                f"Unsupported connector type: {connector_id}"
            )

        return connector

    # -----------------------------------------------------------------
    # Listing
    # -----------------------------------------------------------------

    @classmethod
    def list(
        cls,
        *,
        category: Optional[str] = None,
        family: Optional[str] = None,
        driver: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[ConnectorMetadata]:
        """
        List connector metadata with optional filters.
        """

        cls.load()

        connectors: Iterable[
            ConnectorMetadata
        ] = cls._connectors.values()

        if enabled_only:
            connectors = (
                connector
                for connector in connectors
                if connector.enabled
            )

        if category:
            category_key = cls._normalize_key(
                category
            )

            connectors = (
                connector
                for connector in connectors
                if cls._normalize_key(
                    connector.category
                )
                == category_key
            )

        if family:
            family_key = cls._normalize_key(
                family
            )

            connectors = (
                connector
                for connector in connectors
                if cls._normalize_key(
                    connector.family
                )
                == family_key
            )

        if driver:
            driver_key = cls._normalize_key(
                driver
            )

            connectors = (
                connector
                for connector in connectors
                if cls._normalize_key(
                    connector.driver
                )
                == driver_key
            )

        return sorted(
            list(connectors),
            key=lambda item: (
                item.category_label.lower(),
                item.name.lower(),
            ),
        )

    @classmethod
    def all(
        cls,
    ) -> List[ConnectorMetadata]:
        """Return all enabled connectors."""
        return cls.list()

    @classmethod
    def list_by_category(
        cls,
        category: str,
    ) -> List[ConnectorMetadata]:
        """Return connectors belonging to a category."""
        return cls.list(
            category=category
        )

    @classmethod
    def list_by_family(
        cls,
        family: str,
    ) -> List[ConnectorMetadata]:
        """Return connectors belonging to a connector family."""
        return cls.list(
            family=family
        )

    @classmethod
    def native_connectors(
        cls,
    ) -> List[ConnectorMetadata]:
        """Return connectors with native application drivers."""
        return cls.list(
            driver="native"
        )

    @classmethod
    def universal_connectors(
        cls,
    ) -> List[ConnectorMetadata]:
        """Return connectors handled by UniversalConnectorDriver."""
        return cls.list(
            driver="universal"
        )

    # -----------------------------------------------------------------
    # Search
    # -----------------------------------------------------------------

    @classmethod
    def search(
        cls,
        query: str,
    ) -> List[ConnectorMetadata]:
        """
        Search by connector id, name, category, family,
        description, or alias.
        """

        cls.load()

        query_key = cls._normalize_key(
            query
        )

        if not query_key:
            return cls.list()

        results: List[ConnectorMetadata] = []

        for connector in cls._connectors.values():
            searchable = " ".join(
                [
                    connector.id,
                    connector.name,
                    connector.category,
                    connector.category_label,
                    connector.family,
                    connector.description,
                    " ".join(connector.aliases),
                ]
            )

            if query_key in cls._normalize_key(
                searchable
            ):
                results.append(connector)

        return sorted(
            results,
            key=lambda item: item.name.lower(),
        )

    # -----------------------------------------------------------------
    # Configuration schema
    # -----------------------------------------------------------------

    @classmethod
    def get_configuration_schema(
        cls,
        connector_id: str,
    ) -> Dict[str, Any]:
        """
        Return the configuration schema used by the ConnectorWizard.
        """

        connector = cls.require(
            connector_id
        )

        return {
            "connector_id": connector.id,
            "name": connector.name,
            "category": connector.category,
            "category_label": connector.category_label,
            "family": connector.family,
            "description": connector.description,
            "default_port": connector.default_port,
            "default_auth": connector.default_auth,
            "doc_type": connector.doc_type,
            "fields": connector.required_fields,
            "lifecycle": connector.lifecycle,
            "driver": connector.driver,
            "is_native": connector.is_native,
            "is_universal": connector.is_universal,
        }

    # -----------------------------------------------------------------
    # Lifecycle information
    # -----------------------------------------------------------------

    @classmethod
    def get_lifecycle(
        cls,
        connector_id: str,
    ) -> Dict[str, Any]:
        """
        Return lifecycle capability information.
        """

        connector = cls.require(
            connector_id
        )

        return {
            "connector_id": connector.id,
            "connector_name": connector.name,
            "driver": connector.driver,
            "lifecycle": connector.lifecycle,
            "stages": {
                stage: stage in connector.lifecycle
                for stage in CONNECTOR_LIFECYCLE
            },
        }

    # -----------------------------------------------------------------
    # Categories
    # -----------------------------------------------------------------

    @classmethod
    def categories(
        cls,
    ) -> List[Dict[str, Any]]:
        """
        Return category summaries for the frontend connector hub.
        """

        cls.load()

        grouped: Dict[str, Dict[str, Any]] = {}

        for connector in cls._connectors.values():
            key = connector.category

            if key not in grouped:
                grouped[key] = {
                    "id": key,
                    "label": connector.category_label,
                    "count": 0,
                    "connectors": [],
                }

            grouped[key]["count"] += 1

            grouped[key]["connectors"].append(
                connector.id
            )

        return sorted(
            grouped.values(),
            key=lambda item: item["label"].lower(),
        )

    # -----------------------------------------------------------------
    # Public API catalog
    # -----------------------------------------------------------------

    @classmethod
    def public_catalog(
        cls,
    ) -> Dict[str, Any]:
        """
        Return the complete catalog in a frontend/API-safe format.
        """

        connectors = cls.list()

        return {
            "version": "1.0",
            "lifecycle": list(
                CONNECTOR_LIFECYCLE
            ),
            "count": len(connectors),
            "categories": cls.categories(),
            "connectors": [
                connector.to_public_dict()
                for connector in connectors
            ],
        }

    # -----------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------

    @classmethod
    def stats(
        cls,
    ) -> Dict[str, Any]:
        """Return registry statistics."""

        connectors = cls.list()

        native = [
            connector
            for connector in connectors
            if connector.is_native
        ]

        universal = [
            connector
            for connector in connectors
            if connector.is_universal
        ]

        return {
            "total": len(connectors),
            "native": len(native),
            "universal": len(universal),
            "categories": len(
                cls.categories()
            ),
            "lifecycle_stages": len(
                CONNECTOR_LIFECYCLE
            ),
        }

    # -----------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------

    @classmethod
    def validate(
        cls,
    ) -> Dict[str, Any]:
        """
        Validate the loaded catalog.

        Returns a report instead of immediately raising so it can be
        used by health/monitoring endpoints.
        """

        cls.load()

        errors: List[str] = []
        warnings: List[str] = []

        seen_ids: set[str] = set()

        for connector in cls._connectors.values():
            if connector.id in seen_ids:
                errors.append(
                    f"Duplicate connector id: {connector.id}"
                )

            seen_ids.add(
                connector.id
            )

            if not connector.name:
                errors.append(
                    f"{connector.id}: missing name"
                )

            if not connector.category:
                warnings.append(
                    f"{connector.id}: missing category"
                )

            if not connector.lifecycle:
                warnings.append(
                    f"{connector.id}: no lifecycle stages"
                )

            if connector.is_native:
                if connector.driver not in (
                    "native",
                    "universal",
                ):
                    warnings.append(
                        f"{connector.id}: native connector "
                        f"uses driver '{connector.driver}'"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": cls.stats(),
        }

    # -----------------------------------------------------------------
    # Alias management
    # -----------------------------------------------------------------

    @classmethod
    def register_alias(
        cls,
        alias: str,
        connector_id: str,
    ) -> None:
        """
        Register a runtime alias.

        Useful when a legacy source_type needs to resolve to a catalog
        connector without modifying the JSON catalog.
        """

        cls.load()

        canonical = cls.get_by_id(
            connector_id
        )

        if canonical is None:
            raise ValueError(
                f"Cannot register alias '{alias}': "
                f"connector '{connector_id}' does not exist."
            )

        alias_key = cls._normalize_key(
            alias
        )

        if not alias_key:
            raise ValueError(
                "Connector alias cannot be empty."
            )

        cls._aliases[alias_key] = canonical.id

    @classmethod
    def aliases_for(
        cls,
        connector_id: str,
    ) -> List[str]:
        """Return aliases resolving to a connector."""

        connector = cls.require(
            connector_id
        )

        return sorted(
            alias
            for alias, canonical in cls._aliases.items()
            if canonical == connector.id
            and alias != connector.id
        )

    # -----------------------------------------------------------------
    # Native aliases
    # -----------------------------------------------------------------

    @classmethod
    def _register_native_aliases(
        cls,
    ) -> None:
        """
        Ensure legacy native source_type values continue resolving.

        These aliases correspond to the existing SyncEngine dispatch
        logic.
        """

        native_aliases = {
            "postgres": "postgresql",
            "apache_kafka": "kafka",
            "confluent": "kafka",
            "sfdc": "salesforce",
            "salesforce_crm": "salesforce",
            "mongo": "mongodb",
            "mongo_atlas": "mongodb",
            "wiki": "confluence",
            "jira_issues": "jira",
            "repo": "github",
            "git": "github",
        }

        for alias, canonical in native_aliases.items():
            if canonical in cls._connectors:
                cls._aliases[
                    alias
                ] = canonical

    # -----------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------

    @staticmethod
    def _normalize_key(
        value: Any,
    ) -> str:
        """
        Normalize ids/categories/aliases for matching.

        Examples:

            "PostgreSQL"      -> "postgresql"
            "post-gresql"     -> "postgresql"
            "Postgre SQL"     -> "postgresql"
            "postgres_sql"    -> "postgresql"
        """

        if value is None:
            return ""

        return (
            str(value)
            .strip()
            .lower()
            .replace("-", "")
            .replace("_", "")
            .replace(" ", "")
        )

    @staticmethod
    def _category_label(
        category: str,
    ) -> str:
        """Generate a human-readable category label."""

        labels = {
            "database": "Databases & Warehouses",
            "storage": "Storage & Lakehouses",
            "streaming": "Streaming & Messaging",
            "etl": "ETL & Data Integration",
            "orchestration": "Orchestration",
            "bi": "Business Intelligence",
            "observability": "Observability",
            "enterprise_app": "Enterprise Applications",
            "ml_ai": "ML & AI",
            "api": "APIs & Services",
            "custom": "Custom Sources",
        }

        normalized = ConnectorRegistry._normalize_key(
            category
        )

        for key, label in labels.items():
            if ConnectorRegistry._normalize_key(
                key
            ) == normalized:
                return label

        return str(category).replace(
            "_",
            " ",
        ).title()


# ---------------------------------------------------------------------
# Module-level compatibility helpers
# ---------------------------------------------------------------------

def get_connector(
    connector_id: str,
) -> Optional[ConnectorMetadata]:
    """Convenience wrapper around ConnectorRegistry.get_by_id()."""
    return ConnectorRegistry.get_by_id(
        connector_id
    )


def get_connector_catalog() -> Dict[str, Any]:
    """Return the public connector catalog."""
    return ConnectorRegistry.public_catalog()


def get_connector_schema(
    connector_id: str,
) -> Dict[str, Any]:
    """Return the configuration schema for a connector."""
    return ConnectorRegistry.get_configuration_schema(
        connector_id
    )


def validate_connector_catalog() -> Dict[str, Any]:
    """Validate the connector catalog."""
    return ConnectorRegistry.validate()


# ---------------------------------------------------------------------
# Lazy initialization
# ---------------------------------------------------------------------

# Do not eagerly load the catalog during import. This avoids startup
# failures when the application is being installed/migrated and the
# catalog has not yet been copied into place.
#
# The first call to ConnectorRegistry.get_by_id(), list(), etc. loads it.

# ---------------------------------------------------------------------
# Aliases & Backward Compatibility
# ---------------------------------------------------------------------
get_connector_metadata = get_connector
CONNECTOR_REGISTRY = ConnectorRegistry

