"""
Reset and seed the Context Trust Layer database with clean canonical data.
Clears accumulated duplicate test records and seeds 3 distinct, high-value conflict scenarios.
"""
import asyncio
import decimal
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "backend")

from sqlalchemy import text
from app.db.database import AsyncSessionLocal


async def reset_and_seed():
    async with AsyncSessionLocal() as session:
        print("Cleaning up database tables...")
        # Clean in reverse dependency order
        await session.execute(text("DELETE FROM human_reviews;"))
        await session.execute(text("DELETE FROM agent_context_items;"))
        await session.execute(text("DELETE FROM agent_requests;"))
        await session.execute(text("DELETE FROM claim_conflicts;"))
        await session.execute(text("DELETE FROM claim_trust_scores;"))
        await session.execute(text("DELETE FROM claim_validity;"))
        await session.execute(text("DELETE FROM claim_evidence;"))
        await session.execute(text("DELETE FROM claims;"))
        await session.execute(text("DELETE FROM document_versions;"))
        await session.execute(text("DELETE FROM documents;"))
        await session.execute(text("DELETE FROM data_sources;"))
        await session.execute(text("DELETE FROM users;"))
        await session.execute(text("DELETE FROM agents;"))
        await session.execute(text("DELETE FROM organizations;"))
        await session.commit()
        print("Database cleared successfully.")

        print("Seeding canonical organizations, users, and data sources...")
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        user_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")

        # 1. Organization
        await session.execute(
            text("""
            INSERT INTO organizations (id, name, slug, status)
            VALUES (:id, 'Acme Global Enterprise', 'acme-global', 'active')
            """),
            {"id": org_id},
        )

        # 2. User (Auditor)
        await session.execute(
            text("""
            INSERT INTO users (id, organization_id, name, email, role, status)
            VALUES (:id, :org_id, 'Sarah Chen (Lead Trust Auditor)', 'sarah.chen@acme.corp', 'reviewer', 'active')
            """),
            {"id": user_id, "org_id": org_id},
        )

        # 3. Data Sources
        src_conf_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        src_jira_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        src_sec_id = uuid.UUID("55555555-5555-5555-5555-555555555551")

        await session.execute(
            text("""
            INSERT INTO data_sources (id, organization_id, name, source_type, external_id, authority_level, status)
            VALUES 
                (:src_conf, :org_id, 'Executive Policy Confluence', 'confluence', 'CONF-FINANCE-2026', 95, 'active'),
                (:src_jira, :org_id, 'Operations Jira & Legacy Wiki', 'jira', 'JIRA-OPERATIONS-OLD', 60, 'active'),
                (:src_sec, :org_id, 'Corporate Security Portal', 'portal', 'SEC-MANDATE-2026', 98, 'active')
            """),
            {
                "src_conf": src_conf_id,
                "src_jira": src_jira_id,
                "src_sec": src_sec_id,
                "org_id": org_id,
            },
        )

        # 4. Agent
        await session.execute(
            text("""
            INSERT INTO agents (id, organization_id, name, description, agent_type, model_provider, model_name, status)
            VALUES (:id, :org_id, 'Enterprise Autonomous Decision Gate Agent', 'Context Trust Gate Agent evaluating real-time claims and policies.', 'general_agent', 'ollama', 'qwen3:1.7b', 'active')
            """),
            {"id": agent_id, "org_id": org_id},
        )

        print("Seeding 3 canonical document pairs and conflict scenarios...")

        # -------------------------------------------------------------
        # SCENARIO 1: Refund Window (₹25k Stale vs. ₹10k Authoritative)
        # -------------------------------------------------------------
        doc1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        doc1_v1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1")
        doc1_v2 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2")
        claim1_stale = uuid.UUID("11111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        claim1_auth = uuid.UUID("22222222-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

        await session.execute(
            text("""
            INSERT INTO documents (id, organization_id, source_id, title, document_type, external_id, content_uri, content_hash, status)
            VALUES (:id, :org_id, :src_id, 'Customer Refund & Disputes Policy', 'policy', 'FIN-POL-2026', '# Refund Policy\nStandard automated refund limit is capped at ₹10,000.', 'hash_refund_policy_2026', 'active')
            """),
            {"id": doc1_id, "org_id": org_id, "src_id": src_conf_id},
        )

        await session.execute(
            text("""
            INSERT INTO document_versions (id, document_id, version_number, content_uri, content_hash, is_current)
            VALUES 
                (:v1, :doc_id, 1, 'Customers are eligible for automated refunds up to ₹25,000 without supervisor approval.', 'hash_refund_v1', false),
                (:v2, :doc_id, 2, 'Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.', 'hash_refund_v2', true)
            """),
            {"v1": doc1_v1, "v2": doc1_v2, "doc_id": doc1_id},
        )

        await session.execute(
            text("""
            INSERT INTO claims (id, organization_id, document_version_id, claim_text, subject, predicate, object, claim_type, status)
            VALUES 
                (:c1, :org_id, :v1, 'Customers are eligible for automated refunds up to ₹25,000 without supervisor approval.', 'Customer', 'eligible_for_automated_refund', '₹25,000', 'numerical_limit', 'conflicted'),
                (:c2, :org_id, :v2, 'Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.', 'Customer', 'eligible_for_automated_refund', '₹10,000', 'numerical_limit', 'conflicted')
            """),
            {"c1": claim1_stale, "c2": claim1_auth, "org_id": org_id, "v1": doc1_v1, "v2": doc1_v2},
        )

        await session.execute(
            text("""
            INSERT INTO claim_validity (claim_id, valid_from, valid_until, version, is_current, validity_status)
            VALUES 
                (:c1, '2025-01-01', '2025-12-31', 'v1.0', false, 'expired'),
                (:c2, '2026-01-01', '2027-12-31', 'v2.0', true, 'valid')
            """),
            {"c1": claim1_stale, "c2": claim1_auth},
        )

        await session.execute(
            text("""
            INSERT INTO claim_trust_scores (claim_id, source_score, freshness_score, evidence_score, consistency_score, authority_score, human_score, overall_score)
            VALUES 
                (:c1, 0.60, 0.40, 0.85, 0.50, 0.60, 0.50, 0.55),
                (:c2, 0.95, 0.98, 0.96, 0.94, 0.95, 1.00, 0.96)
            """),
            {"c1": claim1_stale, "c2": claim1_auth},
        )

        await session.execute(
            text("""
            INSERT INTO claim_evidence (claim_id, document_id, evidence_type, section, text_span, start_offset, end_offset, evidence_hash)
            VALUES 
                (:c1, :doc_id, 'direct_quote', 'Section 2.1 - Automated Thresholds (2025)', 'Customers are eligible for automated refunds up to ₹25,000 without supervisor approval.', 0, 85, 'hash_ev_1'),
                (:c2, :doc_id, 'direct_quote', 'Section 3.2 - Automated Thresholds (2026)', 'Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.', 0, 89, 'hash_ev_2')
            """),
            {"c1": claim1_stale, "c2": claim1_auth, "doc_id": doc1_id},
        )

        # Conflict 1
        await session.execute(
            text("""
            INSERT INTO claim_conflicts (claim_a_id, claim_b_id, conflict_type, severity, confidence, resolution_status)
            VALUES (:c1, :c2, 'NUMERICAL_DISCREPANCY', 'high', 0.95, 'human_review_required')
            """),
            {"c1": claim1_stale, "c2": claim1_auth},
        )

        # -------------------------------------------------------------
        # SCENARIO 2: Remote Work Policy (3 Days Onsite vs. 4 Days Remote)
        # -------------------------------------------------------------
        doc2_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        doc2_v1 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1")
        doc2_v2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2")
        claim2_stale = uuid.UUID("11111111-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        claim2_auth = uuid.UUID("22222222-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

        await session.execute(
            text("""
            INSERT INTO documents (id, organization_id, source_id, title, document_type, external_id, content_uri, content_hash, status)
            VALUES (:id, :org_id, :src_id, 'Engineering Remote Work Guidelines 2026', 'policy', 'HR-REMOTE-2026', '# Remote Work\nEngineering staff are authorized for up to 4 days remote work per week.', 'hash_remote_policy_2026', 'active')
            """),
            {"id": doc2_id, "org_id": org_id, "src_id": src_conf_id},
        )

        await session.execute(
            text("""
            INSERT INTO document_versions (id, document_id, version_number, content_uri, content_hash, is_current)
            VALUES 
                (:v1, :doc_id, 1, 'All full-time employees are required to work on-site at least 3 days per week.', 'hash_remote_v1', false),
                (:v2, :doc_id, 2, 'Engineering staff are authorized for up to 4 days remote work per week.', 'hash_remote_v2', true)
            """),
            {"v1": doc2_v1, "v2": doc2_v2, "doc_id": doc2_id},
        )

        await session.execute(
            text("""
            INSERT INTO claims (id, organization_id, document_version_id, claim_text, subject, predicate, object, claim_type, status)
            VALUES 
                (:c1, :org_id, :v1, 'All full-time employees are required to work on-site at least 3 days per week.', 'Employee', 'required_onsite_days', '3 days', 'policy_rule', 'conflicted'),
                (:c2, :org_id, :v2, 'Engineering staff are authorized for up to 4 days remote work per week.', 'Engineering Staff', 'authorized_remote_days', '4 days', 'department_override', 'conflicted')
            """),
            {"c1": claim2_stale, "c2": claim2_auth, "org_id": org_id, "v1": doc2_v1, "v2": doc2_v2},
        )

        await session.execute(
            text("""
            INSERT INTO claim_validity (claim_id, valid_from, valid_until, version, is_current, validity_status)
            VALUES 
                (:c1, '2024-01-01', '2025-12-31', 'v1.0', false, 'expired'),
                (:c2, '2026-02-14', '2027-12-31', 'v2.0', true, 'valid')
            """),
            {"c1": claim2_stale, "c2": claim2_auth},
        )

        await session.execute(
            text("""
            INSERT INTO claim_trust_scores (claim_id, source_score, freshness_score, evidence_score, consistency_score, authority_score, human_score, overall_score)
            VALUES 
                (:c1, 0.50, 0.35, 0.80, 0.45, 0.50, 0.50, 0.50),
                (:c2, 0.95, 0.96, 0.95, 0.92, 0.95, 1.00, 0.95)
            """),
            {"c1": claim2_stale, "c2": claim2_auth},
        )

        await session.execute(
            text("""
            INSERT INTO claim_evidence (claim_id, document_id, evidence_type, section, text_span, start_offset, end_offset, evidence_hash)
            VALUES 
                (:c1, :doc_id, 'direct_quote', 'Section 1.0 - General Attendance (2024)', 'All full-time employees are required to work on-site at least 3 days per week.', 0, 77, 'hash_ev_r1'),
                (:c2, :doc_id, 'direct_quote', 'Section 1.1 - Remote Flexibility (2026)', 'Engineering staff are authorized for up to 4 days remote work per week.', 0, 69, 'hash_ev_r2')
            """),
            {"c1": claim2_stale, "c2": claim2_auth, "doc_id": doc2_id},
        )

        # Conflict 2
        await session.execute(
            text("""
            INSERT INTO claim_conflicts (claim_a_id, claim_b_id, conflict_type, severity, confidence, resolution_status)
            VALUES (:c1, :c2, 'POLICY_OVERRIDE', 'medium', 0.92, 'human_review_required')
            """),
            {"c1": claim2_stale, "c2": claim2_auth},
        )

        # -------------------------------------------------------------
        # SCENARIO 3: Production Ingress TLS Mandate
        # -------------------------------------------------------------
        doc3_id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        doc3_v1 = uuid.UUID("cccccccc-cccc-cccc-cccc-ccccccccccc1")
        doc3_v2 = uuid.UUID("cccccccc-cccc-cccc-cccc-ccccccccccc2")
        claim3_stale = uuid.UUID("11111111-cccc-cccc-cccc-cccccccccccc")
        claim3_auth = uuid.UUID("22222222-cccc-cccc-cccc-cccccccccccc")

        await session.execute(
            text("""
            INSERT INTO documents (id, organization_id, source_id, title, document_type, external_id, content_uri, content_hash, status)
            VALUES (:id, :org_id, :src_id, 'Corporate Security Guidelines 2026', 'policy', 'SEC-POL-2026', '# Security Mandate\nAll external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication.', 'hash_sec_policy_2026', 'active')
            """),
            {"id": doc3_id, "org_id": org_id, "src_id": src_sec_id},
        )

        await session.execute(
            text("""
            INSERT INTO document_versions (id, document_id, version_number, content_uri, content_hash, is_current)
            VALUES 
                (:v1, :doc_id, 1, 'Internal service endpoints may accept standard HTTP connections within the private VPC mesh.', 'hash_sec_v1', false),
                (:v2, :doc_id, 2, 'All external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication.', 'hash_sec_v2', true)
            """),
            {"v1": doc3_v1, "v2": doc3_v2, "doc_id": doc3_id},
        )

        await session.execute(
            text("""
            INSERT INTO claims (id, organization_id, document_version_id, claim_text, subject, predicate, object, claim_type, status)
            VALUES 
                (:c1, :org_id, :v1, 'Internal service endpoints may accept standard HTTP connections within the private VPC mesh.', 'API Endpoints', 'encryption_standard', 'HTTP', 'security_rule', 'conflicted'),
                (:c2, :org_id, :v2, 'All external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication.', 'Ingress API Endpoints', 'encryption_standard', 'TLS 1.3 + JWT', 'security_mandate', 'conflicted')
            """),
            {"c1": claim3_stale, "c2": claim3_auth, "org_id": org_id, "v1": doc3_v1, "v2": doc3_v2},
        )

        await session.execute(
            text("""
            INSERT INTO claim_validity (claim_id, valid_from, valid_until, version, is_current, validity_status)
            VALUES 
                (:c1, '2023-01-01', '2025-12-31', 'v1.0', false, 'expired'),
                (:c2, '2026-08-01', '2028-12-31', 'v2.0', true, 'valid')
            """),
            {"c1": claim3_stale, "c2": claim3_auth},
        )

        await session.execute(
            text("""
            INSERT INTO claim_trust_scores (claim_id, source_score, freshness_score, evidence_score, consistency_score, authority_score, human_score, overall_score)
            VALUES 
                (:c1, 0.55, 0.30, 0.75, 0.40, 0.55, 0.50, 0.48),
                (:c2, 0.98, 0.99, 0.98, 0.95, 0.98, 1.00, 0.98)
            """),
            {"c1": claim3_stale, "c2": claim3_auth},
        )

        await session.execute(
            text("""
            INSERT INTO claim_evidence (claim_id, document_id, evidence_type, section, text_span, start_offset, end_offset, evidence_hash)
            VALUES 
                (:c1, :doc_id, 'direct_quote', 'Section 2.0 - Network Mesh (2023)', 'Internal service endpoints may accept standard HTTP connections within the private VPC mesh.', 0, 89, 'hash_ev_s1'),
                (:c2, :doc_id, 'direct_quote', 'Section 4.1 - Ingress Security (2026)', 'All external production API ingress endpoints must strictly enforce TLS 1.3 encryption and JWT authentication.', 0, 97, 'hash_ev_s2')
            """),
            {"c1": claim3_stale, "c2": claim3_auth, "doc_id": doc3_id},
        )

        # Conflict 3
        await session.execute(
            text("""
            INSERT INTO claim_conflicts (claim_a_id, claim_b_id, conflict_type, severity, confidence, resolution_status)
            VALUES (:c1, :c2, 'SECURITY_COMPLIANCE', 'critical', 0.98, 'human_review_required')
            """),
            {"c1": claim3_stale, "c2": claim3_auth},
        )

        await session.commit()
        print("Database successfully reset and seeded with 3 canonical conflict scenarios!")


if __name__ == "__main__":
    asyncio.run(reset_and_seed())
