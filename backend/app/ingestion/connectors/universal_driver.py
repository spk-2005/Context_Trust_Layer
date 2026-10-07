# import json
# import uuid
# from typing import Any, Sequence
# from datetime import datetime, timezone
# import httpx
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.models.document import Document
# from app.db.models.document_version import DocumentVersion
# from app.ingestion.connector_registry import ConnectorMetadata, ConnectorRegistry
# from app.ingestion.connectors.base import BaseConnector
# from app.ingestion.document_ingestion import DocumentIngestionService
# from app.schemas.document import DocumentCreate


# class UniversalConnectorDriver(BaseConnector):
#     """
#     Universal protocol driver that handles connection testing, metadata extraction,
#     and contract normalization for any of the 104 enterprise connectors in the catalog.
#     Connects to live endpoints, databases, REST APIs, or cloud metadata endpoints.
#     """

#     def __init__(
#         self,
#         session: AsyncSession,
#         organization_id: uuid.UUID,
#         source_id: uuid.UUID,
#         source_type: str,
#         connection_config: dict[str, Any] | None = None,
#         owner_id: uuid.UUID | None = None,
#     ):
#         super().__init__(session, organization_id, source_id, owner_id)
#         self.source_type = source_type
#         self.meta = ConnectorRegistry.get_by_id(source_type) or ConnectorMetadata(
#             id=source_type,
#             name=source_type.replace("_", " ").title(),
#             category="custom",
#             category_label="Custom Source",
#             family="enterprise_app",
#             description=f"Enterprise connector for {source_type}",
#             monitored_scope="Enterprise data and policy synchronization."
#         )
#         self.config = connection_config or {}
#         self.ingestion_service = DocumentIngestionService(session)

#     async def test_connection(self) -> dict[str, Any]:
#         """Perform protocol-specific pre-flight connectivity verification against real target endpoint."""
#         family = self.meta.family
#         endpoint = (
#             self.config.get("endpoint")
#             or self.config.get("host")
#             or self.config.get("instance_url")
#             or self.config.get("connection_string")
#             or self.config.get("bootstrap_servers")
#         )

#         if not endpoint:
#             return {
#                 "success": False,
#                 "status": "error",
#                 "message": f"Connection configuration missing required host/endpoint for {self.meta.name}.",
#                 "details": {"connector": self.meta.name, "family": family},
#             }

#         # If it's an HTTP/REST based endpoint, test live connectivity
#         if str(endpoint).startswith(("http://", "https://")):
#             try:
#                 headers = {}
#                 api_key = self.config.get("api_key") or self.config.get("token") or self.config.get("client_secret")
#                 if api_key:
#                     headers["Authorization"] = f"Bearer {api_key}"

#                 async with httpx.AsyncClient(timeout=8.0) as client:
#                     resp = await client.get(endpoint, headers=headers)
#                     return {
#                         "success": True,
#                         "status": "ok",
#                         "message": f"Successfully connected to {self.meta.name} endpoint at {endpoint} (HTTP {resp.status_code}).",
#                         "details": {
#                             "connector_id": self.meta.id,
#                             "connector_name": self.meta.name,
#                             "family": family,
#                             "status_code": resp.status_code,
#                             "tested_at": datetime.now(timezone.utc).isoformat(),
#                         },
#                     }
#             except Exception as e:
#                 return {
#                     "success": False,
#                     "status": "error",
#                     "message": f"Connection to {self.meta.name} endpoint failed: {str(e)}",
#                     "details": {"endpoint": endpoint},
#                 }

#         # For host/port configurations, report connection parameters verified
#         port = self.config.get("port") or self.meta.default_port or 443
#         database = self.config.get("database") or self.config.get("workspace") or self.config.get("project") or "default"

#         return {
#             "success": True,
#             "status": "ok",
#             "message": f"Successfully validated connection parameters for {self.meta.name} ({endpoint}:{port}/{database}).",
#             "details": {
#                 "connector_id": self.meta.id,
#                 "connector_name": self.meta.name,
#                 "family": family,
#                 "target": f"{endpoint}:{port}/{database}",
#                 "auth_method": self.meta.default_auth,
#                 "monitored_scope": self.meta.monitored_scope,
#                 "tested_at": datetime.now(timezone.utc).isoformat(),
#             },
#         }

#     async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
#         """Sync live schema, pipeline, metric, or governance contracts from target endpoint."""
#         endpoint = (
#             self.config.get("endpoint")
#             or self.config.get("host")
#             or self.config.get("instance_url")
#             or self.config.get("connection_string")
#             or self.config.get("url")
#             or f"https://policies.{self.source_type.replace('_', '-')}.internal"
#         )

#         # If HTTP/REST endpoint is configured, fetch live OpenAPI / schema or data contract
#         if str(endpoint).startswith(("http://", "https://")):
#             return await self._sync_live_http_endpoint(endpoint)

#         # For database / data warehouse / pipeline connections, register the schema contract
#         return await self._sync_configured_target(endpoint)

#     async def _sync_live_http_endpoint(self, endpoint: str) -> list[tuple[Document, DocumentVersion]]:
#         headers = {}
#         api_key = self.config.get("api_key") or self.config.get("token") or self.config.get("client_secret")
#         if api_key:
#             headers["Authorization"] = f"Bearer {api_key}"

#         try:
#             async with httpx.AsyncClient(timeout=8.0) as client:
#                 resp = await client.get(endpoint, headers=headers)
#                 if resp.status_code >= 400:
#                     return await self._sync_configured_target(endpoint)

#                 content_text = resp.text
#                 try:
#                     parsed = resp.json()
#                     content_text = json.dumps(parsed, indent=2)
#                 except Exception:
#                     pass
#         except Exception:
#             return await self._sync_configured_target(endpoint)

#         title = f"{self.meta.name} API Contract: {self.config.get('database') or self.meta.id}"
#         doc_in = DocumentCreate(
#             organization_id=self.organization_id,
#             source_id=self.source_id,
#             owner_id=self.owner_id,
#             title=title,
#             content=f"# {self.meta.name} Live API Contract\n\nEndpoint: `{endpoint}`\n\n```json\n{content_text[:3000]}\n```",
#             document_type="api_contract",
#             external_id=f"{self.meta.id}://{endpoint}",
#             metadata={
#                 "connector_id": self.meta.id,
#                 "connector_name": self.meta.name,
#                 "family": self.meta.family,
#                 "category": self.meta.category,
#                 **self.config,
#             },
#         )
#         doc, ver, _, _ = await self.ingestion_service.ingest_document_with_dedup(doc_in)
#         return [(doc, ver)]

#     async def _sync_configured_target(self, endpoint: str) -> list[tuple[Document, DocumentVersion]]:
#         database = self.config.get("database") or self.config.get("project") or self.config.get("workspace") or "main"
#         schema_name = self.config.get("schema") or "public"
        
#         content = (
#             f"# {self.meta.name} Data Contract: {database}.{schema_name}\n\n"
#             f"**Connector**: `{self.meta.name}` | **Category**: `{self.meta.category_label}` | **Family**: `{self.meta.family}`\n"
#             f"**Target Host**: `{endpoint}` | **Database/Scope**: `{database}`\n\n"
#             f"## Monitored Scope & SLA\n"
#             f"- {self.meta.monitored_scope}\n"
#             f"- Authentication Mode: `{self.meta.default_auth}`\n"
#             f"- Data Freshness: Continuous synchronization monitored by Context Trust Gate."
#         )

#         doc_in = DocumentCreate(
#             organization_id=self.organization_id,
#             source_id=self.source_id,
#             owner_id=self.owner_id,
#             title=f"{self.meta.name} Contract: {database}.{schema_name}",
#             content=content,
#             document_type="data_contract",
#             external_id=f"{self.meta.id}://{endpoint}/{database}/{schema_name}",
#             metadata={
#                 "connector_id": self.meta.id,
#                 "connector_name": self.meta.name,
#                 "family": self.meta.family,
#                 "category": self.meta.category,
#                 "endpoint": endpoint,
#                 "database": database,
#                 "schema": schema_name,
#             },
#         )
#         doc, ver, _, _ = await self.ingestion_service.ingest_document_with_dedup(doc_in)
#         return [(doc, ver)]
"""
Universal Connector Driver
==========================

The UniversalConnectorDriver provides a common execution layer for
connectors that do not have a dedicated native implementation.

Architecture:

    ConnectorRegistry
           │
           ▼
    ConnectorMetadata
           │
           ▼
    UniversalConnectorDriver
           │
           ├── Configure
           ├── Authenticate
           ├── Test
           ├── Discover
           ├── Select
           ├── Initial Sync
           ├── Continuous Sync
           ├── Normalize
           ├── Provenance
           ├── Conflict Detection
           ├── Lineage
           └── Monitoring

Native connectors such as PostgreSQL, Kafka, Salesforce, MongoDB,
Confluence, Jira and GitHub remain free to use their dedicated
implementations.

The universal driver is used for catalog connectors for which a native
adapter does not yet exist.

IMPORTANT:
    The universal driver does not pretend to magically understand every
    third-party API.

For unsupported connectors it:

    1. Validates configuration.
    2. Builds the appropriate authentication context.
    3. Tests an HTTP/API endpoint where possible.
    4. Discovers generic API resources where possible.
    5. Returns a normalized connector lifecycle result.
    6. Provides an extension point for protocol-specific adapters.

This allows the connector framework to scale without creating 100+
copies of the same lifecycle orchestration code.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin

from app.ingestion.connectors.base import BaseConnector
from app.ingestion.connector_registry import (
    ConnectorMetadata,
    ConnectorRegistry,
)


logger = logging.getLogger(__name__)


class UniversalConnectorDriver(BaseConnector):
    """
    Generic connector driver backed by connector metadata.

    The driver supports:

        Configure
        Authenticate
        Test
        Discover
        Select
        Initial Sync
        Continuous Sync
        Normalize
        Provenance
        Conflict Detection
        Lineage
        Monitoring

    The class intentionally remains lightweight. Source-specific
    behavior should be implemented through a native connector or a
    protocol adapter rather than making this class contain hundreds of
    vendor-specific branches.
    """

    def __init__(
        self,
        session: Any = None,
        organization_id: Any = None,
        source_id: Any = None,
        owner_id: Any = None,
        source_type: Optional[str] = None,
        connection_config: Optional[Dict[str, Any]] = None,
        connector_metadata: Optional[
            ConnectorMetadata | Dict[str, Any]
        ] = None,
        **kwargs: Any,
    ) -> None:

        # -------------------------------------------------------------
        # Resolve metadata from registry when it was not explicitly
        # provided.
        # -------------------------------------------------------------

        metadata: Optional[ConnectorMetadata]

        if isinstance(
            connector_metadata,
            ConnectorMetadata,
        ):
            metadata = connector_metadata

        elif isinstance(
            connector_metadata,
            dict,
        ):
            metadata = ConnectorMetadata(
                **connector_metadata
            )

        else:
            metadata = (
                ConnectorRegistry.get_by_id(
                    source_type
                )
                if source_type
                else None
            )

        # -------------------------------------------------------------
        # If a connector is not present in the catalog, create safe
        # fallback metadata.
        #
        # This preserves compatibility with existing source_type values
        # created before the connector catalog was introduced.
        # -------------------------------------------------------------

        if metadata is None:
            fallback_id = (
                source_type
                or "custom"
            )

            metadata = ConnectorMetadata(
                id=fallback_id,
                name=fallback_id.replace(
                    "_",
                    " ",
                ).title(),
                category="custom",
                category_label="Custom Source",
                family="enterprise_app",
                description=(
                    f"Enterprise connector for "
                    f"{fallback_id}"
                ),
                monitored_scope=(
                    "Enterprise data and policy synchronization."
                ),
                driver="universal",
            )

        self.metadata = metadata

        self.connector_id = metadata.id

        # -------------------------------------------------------------
        # Initialize BaseConnector using the reconciled constructor.
        # -------------------------------------------------------------

        super().__init__(
            session=session,
            organization_id=organization_id,
            source_id=source_id,
            source_type=metadata.id,
            connection_config=connection_config or {},
            connector_metadata=metadata.model_dump(),
            owner_id=owner_id,
            **kwargs,
        )

        # -------------------------------------------------------------
        # Universal-driver runtime state.
        # -------------------------------------------------------------

        self.authenticated = False

        self.tested = False

        self.discovered = False

        self.selected = False

        self.last_error: Optional[str] = None

        self.last_response: Optional[Dict[str, Any]] = None

        self._http_client: Any = None

    # =================================================================
    # INTERNAL HELPERS
    # =================================================================

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _clean_url(
        url: str,
    ) -> str:
        """
        Normalize a URL while preserving its path.
        """

        value = (
            str(url)
            .strip()
        )

        if not value:
            return value

        if not value.startswith(
            (
                "http://",
                "https://",
            )
        ):
            value = (
                "https://"
                + value
            )

        return value.rstrip("/")

    def _get(
        self,
        *keys: str,
        default: Any = None,
    ) -> Any:
        """
        Get the first available configuration value.

        Supports aliases such as:

            base_url
            url
            endpoint
            host
        """

        for key in keys:
            value = self.connection_config.get(
                key
            )

            if value is not None:
                return value

        return default

    def _base_url(self) -> Optional[str]:
        """
        Resolve the base endpoint from generic connector configuration.
        """

        value = self._get(
            "base_url",
            "url",
            "endpoint",
            "api_url",
            "instance_url",
            "host",
        )

        if not value:
            return None

        return self._clean_url(
            str(value)
        )

    def _build_auth_headers(
        self,
    ) -> Dict[str, str]:
        """
        Build generic HTTP authentication headers.

        Supported generic authentication patterns:

            Bearer token
            API key
            Basic username/password
            custom Authorization header
        """

        config = self.connection_config

        headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": (
                "ContextTrustLayer/"
                "UniversalConnectorDriver"
            ),
        }

        # -------------------------------------------------------------
        # Explicit authorization header.
        # -------------------------------------------------------------

        authorization = (
            config.get(
                "authorization"
            )
            or config.get(
                "authorization_header"
            )
        )

        if authorization:
            headers["Authorization"] = str(
                authorization
            )

            return headers

        # -------------------------------------------------------------
        # Bearer token.
        # -------------------------------------------------------------

        token = (
            config.get("access_token")
            or config.get("api_token")
            or config.get("token")
            or config.get("api_key")
        )

        auth_type = str(
            config.get(
                "auth_type",
                self.metadata.default_auth,
            )
            or ""
        ).lower()

        if token:
            if auth_type in (
                "api_key",
                "apikey",
                "x_api_key",
                "api-key",
            ):
                headers[
                    "X-API-Key"
                ] = str(token)

            elif auth_type in (
                "basic",
                "basic_auth",
            ):
                # Basic auth is handled below when username/password
                # are available.
                pass

            else:
                headers[
                    "Authorization"
                ] = (
                    "Bearer "
                    + str(token)
                )

        # -------------------------------------------------------------
        # Username/password Basic authentication.
        # -------------------------------------------------------------

        username = (
            config.get("username")
            or config.get("user")
            or config.get("user_email")
            or config.get("email")
        )

        password = (
            config.get("password")
            or config.get("api_token")
        )

        if (
            username is not None
            and password is not None
            and auth_type in (
                "basic",
                "basic_auth",
                "password",
                "basic_password",
            )
        ):
            raw = (
                f"{username}:{password}"
            ).encode(
                "utf-8"
            )

            encoded = base64.b64encode(
                raw
            ).decode(
                "ascii"
            )

            headers[
                "Authorization"
            ] = (
                "Basic "
                + encoded
            )

        return headers

    def _resource_path(
        self,
    ) -> Optional[str]:
        """
        Determine a generic discovery endpoint.

        Connector metadata may provide:

            discovery_endpoint

        or configuration may provide:

            discovery_endpoint
            resource_path
            api_path
        """

        endpoint = (
            self.connection_config.get(
                "discovery_endpoint"
            )
            or self.connection_config.get(
                "resource_path"
            )
            or self.connection_config.get(
                "api_path"
            )
            or self.metadata.capabilities.get(
                "discovery_endpoint"
            )
        )

        if endpoint:
            return str(endpoint)

        return None

    def _request_client(self) -> Any:
        """
        Return the configured HTTP client.

        Existing application sessions are preferred.

        The method deliberately does not silently create an external
        network client when a session has already been supplied.
        """

        if self.session is not None:
            return self.session

        if self._http_client is not None:
            return self._http_client

        try:
            import httpx

            self._http_client = httpx.AsyncClient(
                timeout=30.0
            )

            return self._http_client

        except ImportError:
            return None

    async def _close_http_client(self) -> None:
        """
        Close a client created by this driver.
        """

        if (
            self._http_client is not None
            and hasattr(
                self._http_client,
                "aclose",
            )
        ):
            try:
                await self._http_client.aclose()
            except Exception:
                logger.debug(
                    "Unable to close universal HTTP client.",
                    exc_info=True,
                )

        self._http_client = None

    async def _http_get(
        self,
        url: str,
        *,
        params: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Execute a generic GET request.

        Supports both:

            httpx.AsyncClient
            synchronous-looking test clients exposing async get()
        """

        client = self._request_client()

        if client is None:
            return {
                "success": False,
                "status": "dependency_missing",
                "message": (
                    "No HTTP client is available."
                ),
            }

        headers = (
            self._build_auth_headers()
        )

        try:
            response = await client.get(
                url,
                headers=headers,
                params=params,
            )

            status_code = getattr(
                response,
                "status_code",
                None,
            )

            response_headers = dict(
                getattr(
                    response,
                    "headers",
                    {},
                )
                or {}
            )

            # ---------------------------------------------------------
            # Parse response body.
            # ---------------------------------------------------------

            payload: Any

            if hasattr(
                response,
                "json",
            ):
                try:
                    payload = response.json()

                    if hasattr(
                        payload,
                        "__await__",
                    ):
                        payload = await payload

                except Exception:
                    payload = None
            else:
                payload = None

            if payload is None:
                payload = getattr(
                    response,
                    "text",
                    None,
                )

            successful = (
                status_code is not None
                and 200 <= status_code < 300
            )

            return {
                "success": successful,
                "status": (
                    "success"
                    if successful
                    else "http_error"
                ),
                "status_code": status_code,
                "headers": response_headers,
                "data": payload,
                "url": url,
            }

        except Exception as exc:
            logger.warning(
                "Universal connector request failed for %s: %s",
                url,
                exc,
            )

            self.last_error = str(
                exc
            )

            return {
                "success": False,
                "status": "connection_error",
                "message": str(exc),
                "url": url,
            }

    # =================================================================
    # 1. CONFIGURE
    # =================================================================

    async def configure(
        self,
    ) -> Dict[str, Any]:
        """
        Validate configuration using connector catalog metadata.
        """

        result = await super().configure()

        if not result.get(
            "success",
            False,
        ):
            return result

        return {
            **result,
            "connector_id": self.connector_id,
            "driver": "universal",
            "metadata": {
                "name": self.metadata.name,
                "category": self.metadata.category,
                "family": self.metadata.family,
            },
        }

    # =================================================================
    # 2. AUTHENTICATE
    # =================================================================

    async def authenticate(
        self,
    ) -> Dict[str, Any]:
        """
        Prepare universal authentication.

        Authentication is considered prepared rather than proven until
        the test phase succeeds.
        """

        config = self.connection_config

        auth_type = str(
            config.get(
                "auth_type",
                self.metadata.default_auth,
            )
            or "password"
        ).lower()

        supported_auth = {
            "none",
            "password",
            "basic",
            "basic_auth",
            "api_key",
            "apikey",
            "bearer",
            "oauth2",
            "oauth",
            "token",
        }

        if auth_type not in supported_auth:
            return {
                "success": False,
                "status": "unsupported_authentication",
                "message": (
                    f"Universal driver does not support "
                    f"authentication type '{auth_type}'."
                ),
                "auth_type": auth_type,
            }

        headers = self._build_auth_headers()

        # Never expose secret header values in API results.
        safe_headers = {
            key: (
                "***"
                if key.lower()
                in {
                    "authorization",
                    "x-api-key",
                }
                else value
            )
            for key, value in headers.items()
        }

        self.authenticated = True

        return {
            "success": True,
            "status": "authenticated",
            "message": (
                "Authentication configuration prepared."
            ),
            "auth_type": auth_type,
            "headers": safe_headers,
            "requires_test": True,
        }

    # =================================================================
    # 3. TEST
    # =================================================================

    async def test(
        self,
    ) -> Dict[str, Any]:
        """
        Test connectivity.

        Strategy:

            1. Use a configured health/test endpoint if supplied.
            2. Otherwise use the configured base URL.
            3. If no endpoint exists, report that testing is not
               possible instead of claiming success.
        """

        base_url = self._base_url()

        if not base_url:
            return {
                "success": False,
                "status": "configuration_required",
                "message": (
                    "No endpoint or base URL is configured "
                    "for this connector."
                ),
            }

        test_path = (
            self.connection_config.get(
                "test_endpoint"
            )
            or self.metadata.capabilities.get(
                "test_endpoint"
            )
        )

        url = base_url

        if test_path:
            url = urljoin(
                base_url.rstrip("/")
                + "/",
                str(test_path).lstrip("/"),
            )

        result = await self._http_get(
            url
        )

        self.tested = bool(
            result.get(
                "success",
                False,
            )
        )

        self.last_response = result

        if self.tested:
            return {
                **result,
                "message": (
                    "Universal connector "
                    "connection test succeeded."
                ),
                "connector_id": self.connector_id,
            }

        return {
            **result,
            "connector_id": self.connector_id,
        }

    async def test_connection(
        self,
    ) -> Dict[str, Any]:
        """
        Backward-compatible test_connection() method.
        """

        return await self.test()

    # =================================================================
    # 4. DISCOVER
    # =================================================================

    async def discover(
        self,
    ) -> Dict[str, Any]:
        """
        Discover resources through a generic API endpoint.

        If the catalog defines a discovery endpoint, it is used.

        Otherwise the connector's configured base endpoint is tested
        and returned as a single selectable resource.
        """

        base_url = self._base_url()

        if not base_url:
            return {
                "success": False,
                "status": "configuration_required",
                "resources": [],
                "message": (
                    "A base URL or endpoint is required "
                    "for generic discovery."
                ),
            }

        resource_path = (
            self._resource_path()
        )

        url = base_url

        if resource_path:
            url = urljoin(
                base_url.rstrip("/")
                + "/",
                resource_path.lstrip("/"),
            )

        result = await self._http_get(
            url
        )

        if not result.get(
            "success",
            False,
        ):
            # If discovery endpoint is not explicitly available,
            # returning the configured endpoint as a resource is more
            # useful than pretending discovery succeeded.
            if not resource_path:
                resources = [
                    {
                        "id": "root",
                        "name": self.metadata.name,
                        "type": "endpoint",
                        "endpoint": base_url,
                        "selectable": True,
                    }
                ]

                self.discovery_result = {
                    "success": True,
                    "status": "partial",
                    "resources": resources,
                    "message": (
                        "No dedicated discovery endpoint was configured. "
                        "The source endpoint is available for selection."
                    ),
                }

                self.discovered = True

                return self.discovery_result

            return {
                **result,
                "resources": [],
            }

        payload = result.get(
            "data"
        )

        resources = self._extract_resources(
            payload,
            base_url=base_url,
        )

        self.discovery_result = {
            "success": True,
            "status": "success",
            "resources": resources,
            "count": len(resources),
            "endpoint": url,
        }

        self.discovered = True

        return self.discovery_result

    async def discover_resources(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Backward-compatible discovery method.
        """

        result = await self.discover()

        return result.get(
            "resources",
            [],
        )

    def _extract_resources(
        self,
        payload: Any,
        *,
        base_url: str,
    ) -> List[Dict[str, Any]]:
        """
        Convert common API response shapes into selectable resources.

        Supported response patterns:

            {"resources": [...]}
            {"items": [...]}
            {"data": [...]}
            {"results": [...]}
            [...]
            {"tables": [...]}
            {"repositories": [...]}
            {"projects": [...]}
            {"folders": [...]}
            {"topics": [...]}
        """

        if payload is None:
            return [
                {
                    "id": "root",
                    "name": self.metadata.name,
                    "type": "endpoint",
                    "endpoint": base_url,
                    "selectable": True,
                }
            ]

        candidate: Any = payload

        if isinstance(
            payload,
            dict,
        ):
            for key in (
                "resources",
                "items",
                "results",
                "data",
                "tables",
                "repositories",
                "projects",
                "folders",
                "topics",
                "collections",
            ):
                value = payload.get(
                    key
                )

                if isinstance(
                    value,
                    list,
                ):
                    candidate = value
                    break

        if not isinstance(
            candidate,
            list,
        ):
            candidate = [
                candidate
            ]

        resources: List[
            Dict[str, Any]
        ] = []

        for index, item in enumerate(
            candidate
        ):
            if isinstance(
                item,
                dict,
            ):
                resource_id = (
                    item.get("id")
                    or item.get("key")
                    or item.get("name")
                    or item.get("path")
                    or f"resource-{index + 1}"
                )

                resource_name = (
                    item.get("name")
                    or item.get("title")
                    or item.get("label")
                    or str(resource_id)
                )

                resource_type = (
                    item.get("type")
                    or item.get("kind")
                    or "resource"
                )

                resources.append(
                    {
                        **item,
                        "id": str(
                            resource_id
                        ),
                        "name": str(
                            resource_name
                        ),
                        "type": resource_type,
                        "selectable": True,
                    }
                )

            else:
                resources.append(
                    {
                        "id": f"resource-{index + 1}",
                        "name": str(item),
                        "type": "resource",
                        "value": item,
                        "selectable": True,
                    }
                )

        return resources

    # =================================================================
    # 5. SELECT
    # =================================================================

    async def select(
        self,
        selection: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Validate and store selected resources.
        """

        selection = selection or {}

        resources = selection.get(
            "resources",
            selection.get(
                "selected_resources",
                [],
            ),
        )

        if resources is None:
            resources = []

        if not isinstance(
            resources,
            list,
        ):
            resources = [
                resources
            ]

        if (
            self.discovered
            and self.discovery_result.get(
                "resources"
            )
        ):
            available_ids = {
                str(
                    resource.get(
                        "id"
                    )
                )
                for resource in self.discovery_result[
                    "resources"
                ]
                if isinstance(
                    resource,
                    dict,
                )
            }

            selected_ids = set()

            for resource in resources:
                if isinstance(
                    resource,
                    dict,
                ):
                    selected_ids.add(
                        str(
                            resource.get(
                                "id"
                            )
                        )
                    )
                else:
                    selected_ids.add(
                        str(resource)
                    )

            invalid = (
                selected_ids
                - available_ids
            )

            if invalid:
                return {
                    "success": False,
                    "status": "invalid_selection",
                    "message": (
                        "One or more selected resources "
                        "were not returned by discovery."
                    ),
                    "invalid_resources": sorted(
                        invalid
                    ),
                }

        result = await super().select(
            {
                **selection,
                "resources": resources,
            }
        )

        self.selected = bool(
            result.get(
                "success",
                False,
            )
        )

        return result

    # =================================================================
    # 6. INITIAL SYNC
    # =================================================================

    async def initial_sync(
        self,
    ) -> Sequence[Any]:
        """
        Generic initial synchronization.

        Generic APIs cannot safely be converted into the application's
        document model without source-specific semantics.

        Therefore this method returns discovered resource payloads in a
        predictable envelope. A protocol/native adapter can override it
        to provide fully normalized documents.
        """

        return await self._sync_resources(
            mode="initial"
        )

    # =================================================================
    # 7. CONTINUOUS SYNC
    # =================================================================

    async def continuous_sync(
        self,
    ) -> Sequence[Any]:
        """
        Generic incremental synchronization.

        Uses a configured cursor/watermark when one exists.
        """

        return await self._sync_resources(
            mode="continuous"
        )

    async def sync(
        self,
    ) -> Sequence[Any]:
        """
        Preserve the existing BaseConnector.sync() contract.

        Existing SyncEngine code can call:

            await connector.sync()

        and universal connectors will perform an initial generic sync.
        """

        return await self.initial_sync()

    async def _sync_resources(
        self,
        *,
        mode: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch selected resources.

        A resource may provide its own endpoint.

        Otherwise the connector's base endpoint is used.
        """

        resources = (
            self.selected_scope.get(
                "resources",
                [],
            )
        )

        if not resources:
            # If the caller skipped explicit selection, sync the root
            # endpoint rather than failing silently.
            resources = [
                {
                    "id": "root",
                    "name": self.metadata.name,
                    "type": "endpoint",
                    "endpoint": self._base_url(),
                }
            ]

        records: List[
            Dict[str, Any]
        ] = []

        cursor = self.connection_config.get(
            "cursor"
        )

        for resource in resources:
            if isinstance(
                resource,
                dict,
            ):
                endpoint = (
                    resource.get(
                        "endpoint"
                    )
                    or resource.get(
                        "url"
                    )
                    or resource.get(
                        "api_url"
                    )
                    or self._base_url()
                )

                resource_id = str(
                    resource.get(
                        "id",
                        "root",
                    )
                )

                resource_name = str(
                    resource.get(
                        "name",
                        resource_id,
                    )
                )

            else:
                endpoint = self._base_url()

                resource_id = str(
                    resource
                )

                resource_name = resource_id

            if not endpoint:
                continue

            params: Dict[
                str,
                Any
            ] = {}

            if mode == "continuous" and cursor:
                params[
                    "cursor"
                ] = cursor

            result = await self._http_get(
                str(endpoint),
                params=params or None,
            )

            if not result.get(
                "success",
                False,
            ):
                records.append(
                    {
                        "connector_id": self.connector_id,
                        "source_id": self.source_id,
                        "resource_id": resource_id,
                        "resource_name": resource_name,
                        "sync_mode": mode,
                        "status": "error",
                        "error": result.get(
                            "message"
                        ),
                        "source_url": endpoint,
                        "retrieved_at": self._now(),
                    }
                )

                continue

            records.append(
                {
                    "connector_id": self.connector_id,
                    "source_id": self.source_id,
                    "resource_id": resource_id,
                    "resource_name": resource_name,
                    "sync_mode": mode,
                    "status": "success",
                    "data": result.get(
                        "data"
                    ),
                    "source_url": endpoint,
                    "retrieved_at": self._now(),
                    "http_status": result.get(
                        "status_code"
                    ),
                }
            )

        self.last_sync_at = self._now()

        return records

    # =================================================================
    # 8. NORMALIZE
    # =================================================================

    async def normalize(
        self,
        records: Sequence[Any],
    ) -> Sequence[Any]:
        """
        Add a common normalized envelope.

        This does not replace the application's document normalizer.

        The purpose is to make universal-driver records structurally
        consistent before entering the existing normalization pipeline.
        """

        normalized: List[Any] = []

        for record in records:
            if not isinstance(
                record,
                dict,
            ):
                normalized.append(
                    {
                        "connector_id": self.connector_id,
                        "source_id": self.source_id,
                        "content": record,
                        "normalized_at": self._now(),
                    }
                )

                continue

            item = dict(
                record
            )

            item.setdefault(
                "connector_id",
                self.connector_id,
            )

            item.setdefault(
                "source_id",
                self.source_id,
            )

            item.setdefault(
                "normalized_at",
                self._now(),
            )

            item.setdefault(
                "normalization_version",
                "1.0",
            )

            normalized.append(
                item
            )

        return normalized

    # =================================================================
    # 9. PROVENANCE
    # =================================================================

    async def provenance(
        self,
        records: Sequence[Any],
    ) -> Sequence[Any]:
        """
        Add source provenance metadata.

        Existing provenance persistence remains owned by the ingestion
        pipeline.
        """

        enriched: List[Any] = []

        for record in records:
            if not isinstance(
                record,
                dict,
            ):
                enriched.append(
                    record
                )

                continue

            item = dict(
                record
            )

            item.setdefault(
                "provenance",
                {
                    "connector_id": self.connector_id,
                    "source_id": self.source_id,
                    "source_type": self.metadata.id,
                    "connector_name": self.metadata.name,
                    "retrieved_at": item.get(
                        "retrieved_at",
                        self._now(),
                    ),
                    "driver": "universal",
                },
            )

            enriched.append(
                item
            )

        return enriched

    # =================================================================
    # 10. CONFLICT DETECTION
    # =================================================================

    async def conflict_detection(
        self,
        records: Sequence[Any],
    ) -> Sequence[Any]:
        """
        Preserve records for the application's existing conflict
        detection pipeline.

        The connector itself should not make cross-source trust
        decisions because it does not have visibility into other
        sources.
        """

        return records

    # =================================================================
    # 11. LINEAGE
    # =================================================================

    async def lineage(
        self,
        records: Sequence[Any],
    ) -> Sequence[Any]:
        """
        Add source-to-resource lineage metadata.
        """

        enriched: List[Any] = []

        for record in records:
            if not isinstance(
                record,
                dict,
            ):
                enriched.append(
                    record
                )

                continue

            item = dict(
                record
            )

            item.setdefault(
                "lineage",
                {
                    "source_id": self.source_id,
                    "connector_id": self.connector_id,
                    "connector": self.metadata.name,
                    "resource_id": item.get(
                        "resource_id"
                    ),
                    "resource_name": item.get(
                        "resource_name"
                    ),
                    "source_url": item.get(
                        "source_url"
                    ),
                },
            )

            enriched.append(
                item
            )

        return enriched

    # =================================================================
    # 12. MONITORING
    # =================================================================

    async def monitoring(
        self,
        *,
        status: str,
        records_processed: int = 0,
        error: Optional[str] = None,
        **metadata: Any,
    ) -> Dict[str, Any]:
        """
        Return standardized monitoring state.
        """

        result = await super().monitoring(
            status=status,
            records_processed=records_processed,
            error=error,
            **metadata,
        )

        result.update(
            {
                "connector_id": self.connector_id,
                "connector_name": self.metadata.name,
                "driver": "universal",
                "tested": self.tested,
                "authenticated": self.authenticated,
                "discovered": self.discovered,
                "selected": self.selected,
                "last_sync_at": self.last_sync_at,
            }
        )

        return result

    # =================================================================
    # COMPLETE LIFECYCLE
    # =================================================================

    async def run_lifecycle(
        self,
        *,
        selection: Optional[
            Dict[str, Any]
        ] = None,
        sync_mode: str = "initial",
        execute_sync: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the connector lifecycle.

        This method performs:

            Configure
            Authenticate
            Test
            Discover
            Select
            Sync
            Normalize
            Provenance
            Conflict Detection
            Lineage
            Monitoring

        It intentionally stops on failures rather than proceeding with
        invalid credentials/configuration.
        """

        result: Dict[str, Any] = {
            "connector_id": self.connector_id,
            "connector_name": self.metadata.name,
            "driver": "universal",
            "lifecycle": {},
            "status": "started",
            "started_at": self._now(),
        }

        # -------------------------------------------------------------
        # Configure
        # -------------------------------------------------------------

        configure_result = await self.configure()

        result[
            "lifecycle"
        ][
            "configure"
        ] = configure_result

        if not configure_result.get(
            "success",
            False,
        ):
            result["status"] = (
                configure_result.get(
                    "status",
                    "configuration_required",
                )
            )

            result[
                "monitoring"
            ] = await self.monitoring(
                status=result["status"],
                error=configure_result.get(
                    "message"
                ),
            )

            return result

        # -------------------------------------------------------------
        # Authenticate
        # -------------------------------------------------------------

        auth_result = await self.authenticate()

        result[
            "lifecycle"
        ][
            "authenticate"
        ] = auth_result

        if not auth_result.get(
            "success",
            False,
        ):
            result["status"] = (
                auth_result.get(
                    "status",
                    "authentication_failed",
                )
            )

            result[
                "monitoring"
            ] = await self.monitoring(
                status=result["status"],
                error=auth_result.get(
                    "message"
                ),
            )

            return result

        # -------------------------------------------------------------
        # Test
        # -------------------------------------------------------------

        test_result = await self.test()

        result[
            "lifecycle"
        ][
            "test"
        ] = test_result

        if not test_result.get(
            "success",
            False,
        ):
            result["status"] = (
                test_result.get(
                    "status",
                    "connection_failed",
                )
            )

            result[
                "monitoring"
            ] = await self.monitoring(
                status=result["status"],
                error=test_result.get(
                    "message"
                ),
            )

            return result

        # -------------------------------------------------------------
        # Discover
        # -------------------------------------------------------------

        discovery_result = await self.discover()

        result[
            "lifecycle"
        ][
            "discover"
        ] = discovery_result

        if not discovery_result.get(
            "success",
            False,
        ):
            result["status"] = (
                discovery_result.get(
                    "status",
                    "discovery_failed",
                )
            )

            result[
                "monitoring"
            ] = await self.monitoring(
                status=result["status"],
                error=discovery_result.get(
                    "message"
                ),
            )

            return result

        # -------------------------------------------------------------
        # Select
        # -------------------------------------------------------------

        if selection is None:
            discovered_resources = (
                discovery_result.get(
                    "resources",
                    [],
                )
            )

            selection = {
                "resources": discovered_resources
            }

        select_result = await self.select(
            selection
        )

        result[
            "lifecycle"
        ][
            "select"
        ] = select_result

        if not select_result.get(
            "success",
            False,
        ):
            result["status"] = (
                select_result.get(
                    "status",
                    "selection_failed",
                )
            )

            result[
                "monitoring"
            ] = await self.monitoring(
                status=result["status"],
                error=select_result.get(
                    "message"
                ),
            )

            return result

        # -------------------------------------------------------------
        # Sync
        # -------------------------------------------------------------

        records: Sequence[Any] = []

        if execute_sync:
            if sync_mode == "continuous":
                records = (
                    await self.continuous_sync()
                )
            else:
                records = (
                    await self.initial_sync()
                )

            result[
                "lifecycle"
            ][
                (
                    "continuous_sync"
                    if sync_mode == "continuous"
                    else "initial_sync"
                )
            ] = {
                "success": True,
                "status": "success",
                "records_count": len(
                    records
                ),
            }

            # ---------------------------------------------------------
            # Normalize
            # ---------------------------------------------------------

            records = await self.normalize(
                records
            )

            result[
                "lifecycle"
            ][
                "normalize"
            ] = {
                "success": True,
                "records_count": len(
                    records
                ),
            }

            # ---------------------------------------------------------
            # Provenance
            # ---------------------------------------------------------

            records = await self.provenance(
                records
            )

            result[
                "lifecycle"
            ][
                "provenance"
            ] = {
                "success": True,
                "records_count": len(
                    records
                ),
            }

            # ---------------------------------------------------------
            # Conflict Detection
            # ---------------------------------------------------------

            records = (
                await self.conflict_detection(
                    records
                )
            )

            result[
                "lifecycle"
            ][
                "conflict_detection"
            ] = {
                "success": True,
                "records_count": len(
                    records
                ),
            }

            # ---------------------------------------------------------
            # Lineage
            # ---------------------------------------------------------

            records = await self.lineage(
                records
            )

            result[
                "lifecycle"
            ][
                "lineage"
            ] = {
                "success": True,
                "records_count": len(
                    records
                ),
            }

            result[
                "records"
            ] = list(
                records
            )

        else:
            result[
                "lifecycle"
            ][
                "sync"
            ] = {
                "success": True,
                "status": "skipped",
                "message": (
                    "Synchronization was not executed."
                ),
            }

        # -------------------------------------------------------------
        # Monitoring
        # -------------------------------------------------------------

        records_processed = len(
            result.get(
                "records",
                [],
            )
        )

        result[
            "monitoring"
        ] = await self.monitoring(
            status="success",
            records_processed=records_processed,
        )

        result["status"] = "success"

        result[
            "completed_at"
        ] = self._now()

        return result

    # =================================================================
    # RESOURCE METADATA
    # =================================================================

    def get_metadata(
        self,
    ) -> Dict[str, Any]:
        """
        Return safe metadata used by APIs and frontend.
        """

        return {
            "id": self.metadata.id,
            "name": self.metadata.name,
            "category": self.metadata.category,
            "category_label": self.metadata.category_label,
            "family": self.metadata.family,
            "description": self.metadata.description,
            "driver": "universal",
            "is_native": False,
            "is_universal": True,
            "default_auth": self.metadata.default_auth,
            "fields": self.metadata.required_fields,
            "lifecycle": self.metadata.lifecycle,
        }

    # =================================================================
    # CLEANUP
    # =================================================================

    async def close(
        self,
    ) -> None:
        """
        Release resources created by the universal driver.
        """

        await self._close_http_client()

    async def __aenter__(
        self,
    ) -> "UniversalConnectorDriver":
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        await self.close()


# =====================================================================
# FACTORY
# =====================================================================


def create_universal_driver(
    *,
    session: Any = None,
    organization_id: Any = None,
    source_id: Any = None,
    owner_id: Any = None,
    source_type: str,
    connection_config: Optional[
        Dict[str, Any]
    ] = None,
    connector_metadata: Optional[
        ConnectorMetadata | Dict[str, Any]
    ] = None,
    **kwargs: Any,
) -> UniversalConnectorDriver:
    """
    Factory used by SyncEngine/API code.

    Example:

        driver = create_universal_driver(
            session=db,
            organization_id=organization_id,
            source_id=source.id,
            source_type=source.type,
            connection_config=config,
        )
    """

    return UniversalConnectorDriver(
        session=session,
        organization_id=organization_id,
        source_id=source_id,
        owner_id=owner_id,
        source_type=source_type,
        connection_config=connection_config,
        connector_metadata=connector_metadata,
        **kwargs,
    )