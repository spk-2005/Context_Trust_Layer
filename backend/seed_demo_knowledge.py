import asyncio
import decimal
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, RecordStatus
from app.db.models.agent import Agent
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.organization import Organization


async def seed_demo_knowledge():
    async with AsyncSessionLocal() as session:
        # 1. Get demo organization
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        res_org = await session.execute(select(Organization).where(Organization.id == org_id))
        org = res_org.scalar_one_or_none()
        if not org:
            org = Organization(id=org_id, name="demo", slug="demo")
            session.add(org)
            await session.flush()

        # 2. Register Claude Desktop Agent & Default Agent
        agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
        res_agent = await session.execute(select(Agent).where(Agent.id == agent_id))
        if not res_agent.scalar_one_or_none():
            agent = Agent(
                id=agent_id,
                organization_id=org_id,
                name="Claude Desktop Assistant",
                agent_type="claude_mcp_client",
                status=RecordStatus.ACTIVE,
            )
            session.add(agent)
            await session.flush()

        # 3. Create Data Source: Enterprise Policy Service
        ds_id = uuid.uuid4()
        source = DataSource(
            id=ds_id,
            organization_id=org_id,
            name="Enterprise Policy Service",
            source_type="policy_service",
            external_id="enterprise-policy-v2",
            authority_level=95,
            status=RecordStatus.ACTIVE,
        )
        session.add(source)
        await session.flush()

        # 4. Create Document: Customer Refund Policy 2026
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            organization_id=org_id,
            source_id=ds_id,
            external_id="POL-REFUND-2026",
            title="Customer Refund Policy 2026 (V2)",
            document_type="policy",
            content_uri="https://policies.corp.internal/refund-2026",
            content_hash="hash_refund_2026",
            status=RecordStatus.ACTIVE,
        )
        session.add(doc)
        await session.flush()

        # 5. Create Document Version
        ver_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        version = DocumentVersion(
            id=ver_id,
            document_id=doc_id,
            version_number=2,
            content_uri="https://policies.corp.internal/refund-2026",
            content_hash="hash_refund_2026_v2",
            is_current=True,
            created_at=now,
            modified_at=now,
        )
        session.add(version)
        await session.flush()

        # 6. Create Claims with Evidence, Trust Scores, and Validity
        claims_data = [
            {
                "text": "Enterprise tier customers are eligible for a 60-day exception refund window upon VP approval.",
                "subject": "Enterprise Tier Customer",
                "predicate": "eligible_for_refund_window",
                "object": "60 days",
                "score": decimal.Decimal("0.98"),
                "status": ClaimStatus.VERIFIED,
                "section": "Section 4.1 - Enterprise Exception Window",
                "is_current": True,
            },
            {
                "text": "Standard automated customer refund limit is strictly capped at ₹10,000 for regular tiers.",
                "subject": "Standard Customer",
                "predicate": "automated_refund_cap",
                "object": "₹10,000",
                "score": decimal.Decimal("0.96"),
                "status": ClaimStatus.VERIFIED,
                "section": "Section 3.2 - Automated Thresholds",
                "is_current": True,
            },
            {
                "text": "All production API ingress must enforce TLS 1.3 encryption and JWT token authentication.",
                "subject": "Production API Ingress",
                "predicate": "must_enforce",
                "object": "TLS 1.3 and JWT Authentication",
                "score": decimal.Decimal("0.98"),
                "status": ClaimStatus.VERIFIED,
                "section": "Section 2 - Security Requirements",
                "is_current": True,
            },
            {
                "text": "Engineering staff are authorized for up to 4 days remote work per week.",
                "subject": "Engineering Staff",
                "predicate": "authorized_remote_work",
                "object": "4 days per week",
                "score": decimal.Decimal("0.92"),
                "status": ClaimStatus.VERIFIED,
                "section": "Section 1.3 - Engineering Remote Work Guidelines",
                "is_current": True,
            },
            {
                "text": "Legacy 2025 refund window of 30 days is outdated and superseded by the 2026 Customer Refund Policy.",
                "subject": "Legacy 2025 Refund Window",
                "predicate": "superseded_by",
                "object": "2026 Customer Refund Policy",
                "score": decimal.Decimal("0.40"),
                "status": ClaimStatus.OUTDATED,
                "section": "Archive Appendix A",
                "is_current": False,
            },
        ]

        for item in claims_data:
            c_id = uuid.uuid4()
            claim = Claim(
                id=c_id,
                organization_id=org_id,
                document_version_id=ver_id,
                claim_text=item["text"],
                subject=item["subject"],
                predicate=item["predicate"],
                object=item["object"],
                claim_type="policy_rule",
                status=item["status"],
            )
            session.add(claim)
            await session.flush()

            # Evidence
            ev = ClaimEvidence(
                id=uuid.uuid4(),
                claim_id=c_id,
                document_id=doc_id,
                evidence_type="direct_quote",
                section=item["section"],
                text_span=item["text"],
            )
            session.add(ev)

            # Trust Score
            ts = ClaimTrustScore(
                id=uuid.uuid4(),
                claim_id=c_id,
                source_score=decimal.Decimal("0.95"),
                freshness_score=decimal.Decimal("0.98"),
                evidence_score=decimal.Decimal("0.95"),
                consistency_score=decimal.Decimal("0.95"),
                authority_score=decimal.Decimal("0.95"),
                human_score=decimal.Decimal("0.00"),
                overall_score=item["score"],
            )
            session.add(ts)

            # Validity
            val = ClaimValidity(
                id=uuid.uuid4(),
                claim_id=c_id,
                valid_from=now,
                valid_until=datetime(2027, 12, 31, tzinfo=timezone.utc),
                is_current=item["is_current"],
                validity_status="valid" if item["is_current"] else "outdated",
            )
            session.add(val)

        await session.commit()
        print(f"Successfully seeded {len(claims_data)} verified claims for organization 'demo' ({org_id})!")


if __name__ == "__main__":
    asyncio.run(seed_demo_knowledge())
