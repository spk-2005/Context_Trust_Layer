import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import EncryptionService
from app.db.models.data_source import DataSource
from app.db.repositories.data_source_repository import DataSourceRepository
from app.ingestion.connector_registry import ConnectorRegistry
from app.ingestion.connectors.confluence_connector import ConfluenceConnector
from app.ingestion.connectors.github_connector import GitHubConnector, sanitize_github_repo
from app.ingestion.connectors.jira_connector import JiraConnector
from app.ingestion.connectors.kafka_connector import KafkaConnector
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.connectors.postgres_connector import PostgresConnector
from app.ingestion.connectors.salesforce_connector import SalesforceConnector
from app.ingestion.connectors.universal_driver import UniversalConnectorDriver
from app.services.claim_extraction_service import ClaimExtractionService
from app.services.conflict_service import ConflictService
from app.services.trust_service import TrustService

_SYNC_LOCKS: dict[uuid.UUID, asyncio.Lock] = {}


class SyncResult(BaseModel):
    source_id: uuid.UUID
    source_name: str
    source_type: str
    documents_synced: int
    documents_created: int = 0
    documents_updated: int = 0
    documents_skipped: int = 0
    claims_extracted: int
    conflicts_detected: int
    execution_time_ms: int = 0
    status: str = "success"
    synced_at: datetime
    message: str


class SyncEngine:
    """Orchestrates end-to-end continuous synchronization between connectors and the Context Trust Layer."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.source_repo = DataSourceRepository(session)
        self.extraction_service = ClaimExtractionService(session)
        self.conflict_service = ConflictService(session)
        self.trust_service = TrustService(session)

    def get_connector_for_source(self, source: DataSource, owner_id: uuid.UUID | None = None):
        source_type = (source.source_type or "").lower().strip()
        raw_config = dict(source.connection_config or {})

        # Decrypt stored credentials if envelope-encrypted
        encrypted_token = raw_config.get("_encrypted_credentials")
        if encrypted_token:
            decrypted = EncryptionService.decrypt_payload(encrypted_token)
            raw_config.update(decrypted)

        effective_owner = owner_id or source.owner_id

        if source_type in ("postgresql", "postgres"):
            return PostgresConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                connection_config=raw_config,
                owner_id=effective_owner,
            )
        elif source_type in ("kafka", "apache_kafka", "confluent"):
            return KafkaConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                connection_config=raw_config,
                owner_id=effective_owner,
            )
        elif source_type in ("salesforce", "sfdc", "salesforce_crm"):
            return SalesforceConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                connection_config=raw_config,
                owner_id=effective_owner,
            )
        elif source_type in ("mongodb", "mongo", "mongo_atlas", "mongodb_atlas", "mongodb_self", "documentdb", "cosmos_mongo"):
            return MongoDbConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                connection_config=raw_config,
                owner_id=effective_owner,
            )
        elif source_type in ("confluence", "wiki"):
            return ConfluenceConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                space_key=raw_config.get("space_key") or source.external_id or "POLICIES",
                base_url=raw_config.get("base_url") or raw_config.get("url") or raw_config.get("confluenceBaseUrl"),
                api_token=raw_config.get("api_token") or raw_config.get("token") or raw_config.get("confluenceToken"),
                user_email=raw_config.get("user_email") or raw_config.get("email"),
                owner_id=effective_owner,
                connection_config=raw_config,
            )
        elif source_type in ("jira", "jira_issues"):
            return JiraConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                project_key=raw_config.get("project_key") or source.external_id or "OPS",
                base_url=raw_config.get("base_url") or raw_config.get("url") or raw_config.get("jiraBaseUrl"),
                api_token=raw_config.get("api_token") or raw_config.get("token") or raw_config.get("jiraToken"),
                user_email=raw_config.get("user_email") or raw_config.get("email"),
                owner_id=effective_owner,
                connection_config=raw_config,
            )
        elif source_type in ("github", "repo", "git"):
            raw_repo = raw_config.get("repository") or raw_config.get("repo") or source.external_id or "demo-org/security-standards"
            repo_target = sanitize_github_repo(raw_repo)
            token_val = raw_config.get("access_token") or raw_config.get("token")
            return GitHubConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                repo=repo_target,
                branch=raw_config.get("branch"),
                token=token_val,
                owner_id=effective_owner,
                connection_config=raw_config,
            )
        else:
            return UniversalConnectorDriver(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                source_type=source_type,
                connection_config=raw_config,
                owner_id=effective_owner,
            )

    async def sync_data_source(
        self,
        source_id: uuid.UUID,
        use_mock_llm: bool = True,
        user_id: uuid.UUID | None = None,
    ) -> SyncResult:
        """Executes a complete delta sync cycle with SHA-256 deduplication and per-connection locking."""
        start_time = time.perf_counter()
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise ValueError(f"Data source {source_id} not found.")

        source_id_val = source.id
        source_name_val = source.name
        source_type_val = source.source_type

        # Acquire per-connection lock to prevent concurrent sync
        if source_id_val not in _SYNC_LOCKS:
            _SYNC_LOCKS[source_id_val] = asyncio.Lock()
        lock = _SYNC_LOCKS[source_id_val]

        if lock.locked():
            return SyncResult(
                source_id=source_id_val,
                source_name=source_name_val,
                source_type=source_type_val,
                documents_synced=0,
                documents_created=0,
                documents_updated=0,
                documents_skipped=0,
                claims_extracted=0,
                conflicts_detected=0,
                execution_time_ms=0,
                status="running",
                synced_at=datetime.now(timezone.utc),
                message=f"Sync job is already actively running for '{source_name_val}'.",
            )

        async with lock:
            effective_owner = user_id or source.owner_id
            if user_id and not source.owner_id:
                source.owner_id = user_id

            cfg = dict(source.connection_config or {})
            cfg["connection_status"] = "syncing"
            cfg["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            source.connection_config = cfg
            await self.session.flush()
            await self.session.commit()

            try:
                connector = self.get_connector_for_source(source, owner_id=effective_owner)
                synced_docs = await connector.sync()
                documents_synced_count = len(synced_docs)

                total_claims_extracted = 0
                total_conflicts_detected = 0
                documents_created_count = 0
                documents_updated_count = 0
                documents_skipped_count = 0

                if use_mock_llm:
                    from app.llm.mock_provider import MockLLMProvider
                    llm_provider = MockLLMProvider()
                    extraction_service = ClaimExtractionService(self.session, llm_provider=llm_provider)
                    conflict_service = ConflictService(self.session, llm_provider=llm_provider)
                else:
                    extraction_service = self.extraction_service
                    conflict_service = self.conflict_service

                for item in synced_docs:
                    if len(item) == 3:
                        doc, version, is_changed = item
                    else:
                        doc, version = item[0], item[1]
                        from app.db.repositories.claim_repository import ClaimRepository
                        claim_repo = ClaimRepository(self.session)
                        existing_claims = await claim_repo.list_by_version(version.id)
                        is_changed = len(existing_claims) == 0

                    if not is_changed:
                        documents_skipped_count += 1
                        continue

                    if version.version_number == 1:
                        documents_created_count += 1
                    else:
                        documents_updated_count += 1

                    claims = await extraction_service.extract_claims_from_version(version.id)
                    total_claims_extracted += len(claims)

                    conflicts = await conflict_service.run_conflict_detection_for_version(version.id)
                    total_conflicts_detected += len(conflicts)

                    await self.trust_service.calculate_for_version(version.id)

                synced_at_ts = datetime.now(timezone.utc)
                source.last_synced_at = synced_at_ts

                # Update persisted status and checkpoint in connection_config
                cfg = dict(source.connection_config or {})
                cfg["connection_status"] = "connected"
                cfg["last_successful_sync_at"] = synced_at_ts.isoformat()
                cfg["last_error"] = None
                cfg["discovered_items_count"] = documents_synced_count
                cfg["sync_checkpoint"] = {
                    "last_synced_at": synced_at_ts.isoformat(),
                    "documents_count": documents_synced_count,
                    "claims_count": total_claims_extracted,
                }
                source.connection_config = cfg
                await self.session.flush()
                await self.session.commit()

                exec_ms = max(1, int((time.perf_counter() - start_time) * 1000))

                if documents_skipped_count > 0 and documents_created_count == 0 and documents_updated_count == 0:
                    msg = (
                        f"⚡ Instant deduplication sync for {source_name_val}: "
                        f"{documents_skipped_count} documents verified unchanged (0 new claims extracted) in {exec_ms}ms."
                    )
                else:
                    msg = (
                        f"Successfully synced {documents_synced_count} documents ({documents_created_count} new, "
                        f"{documents_updated_count} updated, {documents_skipped_count} unchanged) from {source_name_val}. "
                        f"Extracted {total_claims_extracted} atomic claims and surfaced {total_conflicts_detected} potential conflicts in {exec_ms}ms."
                    )

                return SyncResult(
                    source_id=source_id_val,
                    source_name=source_name_val,
                    source_type=source_type_val,
                    documents_synced=documents_synced_count,
                    documents_created=documents_created_count,
                    documents_updated=documents_updated_count,
                    documents_skipped=documents_skipped_count,
                    claims_extracted=total_claims_extracted,
                    conflicts_detected=total_conflicts_detected,
                    execution_time_ms=exec_ms,
                    status="success",
                    synced_at=synced_at_ts,
                    message=msg,
                )
            except Exception as err:
                await self.session.rollback()
                exec_ms = max(1, int((time.perf_counter() - start_time) * 1000))
                error_msg = str(err)

                # Persist failed status and error message
                try:
                    cfg = dict(source.connection_config or {})
                    cfg["connection_status"] = "failed"
                    cfg["last_error"] = error_msg
                    source.connection_config = cfg
                    await self.session.commit()
                except Exception:
                    pass

                return SyncResult(
                    source_id=source_id_val,
                    source_name=source_name_val,
                    source_type=source_type_val,
                    documents_synced=0,
                    documents_created=0,
                    documents_updated=0,
                    documents_skipped=0,
                    claims_extracted=0,
                    conflicts_detected=0,
                    execution_time_ms=exec_ms,
                    status="error",
                    synced_at=datetime.now(timezone.utc),
                    message=f"Sync failed for {source_name_val}: {error_msg}",
                )

    async def sync_all_organization_sources(
        self,
        organization_id: uuid.UUID,
        use_mock_llm: bool = True,
    ) -> list[SyncResult]:
        """Syncs all registered data sources for an organization in sequence."""
        sources = await self.source_repo.list_by_organization(organization_id)
        source_metadata = [(s.id, s.name, s.source_type) for s in sources]
        results = []
        for sid, sname, stype in source_metadata:
            try:
                res = await self.sync_data_source(sid, use_mock_llm=use_mock_llm)
                results.append(res)
            except Exception as e:
                results.append(
                    SyncResult(
                        source_id=sid,
                        source_name=sname,
                        source_type=stype,
                        documents_synced=0,
                        documents_created=0,
                        documents_updated=0,
                        documents_skipped=0,
                        claims_extracted=0,
                        conflicts_detected=0,
                        execution_time_ms=0,
                        status="error",
                        synced_at=datetime.now(timezone.utc),
                        message=f"Sync failed for {sname}: {str(e)}",
                    )
                )
        return results
