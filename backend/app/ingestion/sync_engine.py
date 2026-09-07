import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.data_source import DataSource
from app.db.repositories.data_source_repository import DataSourceRepository
from app.ingestion.connectors.confluence_connector import ConfluenceConnector
from app.ingestion.connectors.github_connector import GitHubConnector
from app.ingestion.connectors.jira_connector import JiraConnector
from app.services.claim_extraction_service import ClaimExtractionService
from app.services.conflict_service import ConflictService
from app.services.trust_service import TrustService


class SyncResult(BaseModel):
    source_id: uuid.UUID
    source_name: str
    source_type: str
    documents_synced: int
    claims_extracted: int
    conflicts_detected: int
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

    def get_connector_for_source(self, source: DataSource):
        source_type = (source.source_type or "").lower()
        if source_type in ("confluence", "wiki"):
            return ConfluenceConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                space_key=source.external_id or "POLICIES",
            )
        elif source_type in ("jira", "jira_issues"):
            return JiraConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                project_key=source.external_id or "OPS",
            )
        elif source_type in ("github", "repo"):
            return GitHubConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                repo=source.external_id or "acme-corp/security-standards",
            )
        else:
            # Fallback to Confluence general connector
            return ConfluenceConnector(
                session=self.session,
                organization_id=source.organization_id,
                source_id=source.id,
                space_key=source.external_id or "GENERAL",
            )

    async def sync_data_source(
        self,
        source_id: uuid.UUID,
        use_mock_llm: bool = True,
    ) -> SyncResult:
        """Executes a complete sync cycle for a specific DataSource."""
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise ValueError(f"Data source {source_id} not found.")

        connector = self.get_connector_for_source(source)

        try:
            # 1. Sync raw documents into document & version tables
            synced_docs = await connector.sync()
            documents_synced_count = len(synced_docs)

            total_claims_extracted = 0
            total_conflicts_detected = 0

            # Fast rule-based provider for immediate responsive sync
            if use_mock_llm:
                from app.llm.mock_provider import MockLLMProvider
                llm_provider = MockLLMProvider()
                extraction_service = ClaimExtractionService(self.session, llm_provider=llm_provider)
                conflict_service = ConflictService(self.session, llm_provider=llm_provider)
            else:
                extraction_service = self.extraction_service
                conflict_service = self.conflict_service

            # 2. Extract atomic claims & detect conflicts for each newly synced version
            for doc, version in synced_docs:
                claims = await extraction_service.extract_claims_from_version(version.id)
                total_claims_extracted += len(claims)

                conflicts = await conflict_service.run_conflict_detection_for_version(version.id)
                total_conflicts_detected += len(conflicts)

                await self.trust_service.calculate_for_version(version.id)

            # 3. Update last_synced_at timestamp on data source
            source.last_synced_at = datetime.now(timezone.utc)
            await self.session.flush()
            await self.session.commit()

            return SyncResult(
                source_id=source.id,
                source_name=source.name,
                source_type=source.source_type,
                documents_synced=documents_synced_count,
                claims_extracted=total_claims_extracted,
                conflicts_detected=total_conflicts_detected,
                status="success",
                synced_at=source.last_synced_at,
                message=(
                    f"Successfully synced {documents_synced_count} documents from {source.name}. "
                    f"Extracted {total_claims_extracted} atomic claims and surfaced {total_conflicts_detected} potential conflicts."
                ),
            )
        except Exception as err:
            await self.session.rollback()
            return SyncResult(
                source_id=source.id,
                source_name=source.name,
                source_type=source.source_type,
                documents_synced=0,
                claims_extracted=0,
                conflicts_detected=0,
                status="error",
                synced_at=datetime.now(timezone.utc),
                message=f"Sync failed for {source.name}: {str(err)}",
            )

    async def sync_all_organization_sources(
        self,
        organization_id: uuid.UUID,
        use_mock_llm: bool = True,
    ) -> list[SyncResult]:
        """Syncs all registered data sources for an organization in sequence."""
        sources = await self.source_repo.list_by_organization(organization_id)
        results = []
        for source in sources:
            res = await self.sync_data_source(source.id, use_mock_llm=use_mock_llm)
            results.append(res)
        return results
