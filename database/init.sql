-- ============================================================
-- Context Trust Layer: PostgreSQL Database Schema (14 Tables)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. organizations
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(205) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL DEFAULT 'auditor',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. data_sources
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    external_id VARCHAR(255) NOT NULL UNIQUE,
    authority_level INTEGER NOT NULL DEFAULT 50,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    external_id VARCHAR(255),
    content_uri TEXT,
    content_hash VARCHAR(64) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. document_versions
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    content_uri TEXT,
    content_hash VARCHAR(64) NOT NULL,
    modified_at TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. claims
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    subject VARCHAR(100),
    predicate VARCHAR(100),
    object TEXT,
    claim_type VARCHAR(50) NOT NULL DEFAULT 'policy',
    extraction_method VARCHAR(50),
    extraction_model VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'verified',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7. claim_evidence
CREATE TABLE IF NOT EXISTS claim_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) DEFAULT 'direct_quote',
    page_number INTEGER,
    section TEXT,
    text_span TEXT NOT NULL,
    start_offset INTEGER,
    end_offset INTEGER,
    evidence_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8. claim_validity
CREATE TABLE IF NOT EXISTS claim_validity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    version VARCHAR(20) DEFAULT 'v1',
    is_current BOOLEAN NOT NULL DEFAULT true,
    validity_status VARCHAR(50) NOT NULL DEFAULT 'valid',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9. claim_trust_scores
CREATE TABLE IF NOT EXISTS claim_trust_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    source_score NUMERIC(3,2) DEFAULT 0.95,
    freshness_score NUMERIC(3,2) DEFAULT 0.90,
    evidence_score NUMERIC(3,2) DEFAULT 0.92,
    consistency_score NUMERIC(3,2) DEFAULT 0.88,
    authority_score NUMERIC(3,2) DEFAULT 0.95,
    human_score NUMERIC(3,2) DEFAULT 1.00,
    overall_score NUMERIC(3,2) NOT NULL DEFAULT 0.92,
    scoring_model VARCHAR(50) DEFAULT 'multi_factor_v1',
    scoring_version VARCHAR(20) DEFAULT '1.0.0',
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 10. claim_conflicts
CREATE TABLE IF NOT EXISTS claim_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_a_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    claim_b_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    conflict_type VARCHAR(50) NOT NULL DEFAULT 'value_mismatch',
    severity VARCHAR(20) NOT NULL DEFAULT 'high',
    confidence NUMERIC(3,2) DEFAULT 0.95,
    resolution_status VARCHAR(50) NOT NULL DEFAULT 'open',
    resolved_claim_id UUID REFERENCES claims(id) ON DELETE SET NULL,
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 11. agents
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_type VARCHAR(50) NOT NULL DEFAULT 'support_agent',
    model_provider VARCHAR(50) DEFAULT 'openai',
    model_name VARCHAR(100) DEFAULT 'gpt-4o',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 12. agent_requests
CREATE TABLE IF NOT EXISTS agent_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    trust_threshold NUMERIC(3,2) NOT NULL DEFAULT 0.85,
    max_results INTEGER DEFAULT 10,
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 13. agent_context_items
CREATE TABLE IF NOT EXISTS agent_context_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES agent_requests(id) ON DELETE CASCADE,
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL DEFAULT 1,
    trust_score NUMERIC(3,2) NOT NULL,
    included BOOLEAN NOT NULL DEFAULT true,
    exclusion_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 14. human_reviews
CREATE TABLE IF NOT EXISTS human_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    decision VARCHAR(50) NOT NULL DEFAULT 'approved',
    reason TEXT,
    previous_score NUMERIC(3,2),
    new_score NUMERIC(3,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- SEED DATA: Insert 1-2 realistic records into all 14 tables
-- ============================================================

DO $$
DECLARE
    v_org_id UUID := '11111111-1111-1111-1111-111111111111';
    v_user_id UUID := '22222222-2222-2222-2222-222222222222';
    v_source_jira_id UUID := '33333333-3333-3333-3333-333333333333';
    v_source_conf_id UUID := '44444444-4444-4444-4444-444444444444';
    v_doc_id UUID := '55555555-5555-5555-5555-555555555555';
    v_doc_version_1 UUID := '66666666-6666-6666-6666-666666666661';
    v_doc_version_2 UUID := '66666666-6666-6666-6666-666666666662';
    v_claim_1 UUID := '77777777-7777-7777-7777-777777777771';
    v_claim_2 UUID := '77777777-7777-7777-7777-777777777772';
    v_agent_id UUID := '88888888-8888-8888-8888-888888888888';
    v_request_id UUID := '99999999-9999-9999-9999-999999999999';
BEGIN
    -- 1. organizations
    INSERT INTO organizations (id, name, slug, status)
    VALUES (v_org_id, 'demo', 'demo', 'active')
    ON CONFLICT (id) DO NOTHING;

    -- 2. users
    INSERT INTO users (id, organization_id, name, email, role, status)
    VALUES (v_user_id, v_org_id, 'Sarah Chen (Lead Auditor)', 'sarah.chen@demo.local', 'reviewer', 'active')
    ON CONFLICT (id) DO NOTHING;

    -- 3. data_sources
    INSERT INTO data_sources (id, organization_id, name, source_type, external_id, authority_level, status)
    VALUES 
        (v_source_conf_id, v_org_id, 'Enterprise Policy Confluence', 'confluence', 'CONF-SPACE-FINANCE', 95, 'active'),
        (v_source_jira_id, v_org_id, 'Support Operations Jira', 'jira', 'JIRA-PROJECT-SUPP', 60, 'active')
    ON CONFLICT (id) DO NOTHING;

    -- 4. documents
    INSERT INTO documents (id, organization_id, source_id, title, document_type, external_id, content_uri, content_hash, status)
    VALUES (v_doc_id, v_org_id, v_source_conf_id, 'Enterprise Customer Refund Policy', 'confluence_page', 'FIN-POL-2026', 's3://context-trust-docs/demo/fin_policy_2026.md', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'active')
    ON CONFLICT (id) DO NOTHING;

    -- 5. document_versions
    INSERT INTO document_versions (id, document_id, version_number, content_uri, content_hash, is_current)
    VALUES 
        (v_doc_version_1, v_doc_id, 1, 's3://context-trust-docs/demo/fin_policy_v1.md', 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0', false),
        (v_doc_version_2, v_doc_id, 2, 's3://context-trust-docs/demo/fin_policy_v2.md', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', true)
    ON CONFLICT (id) DO NOTHING;

    -- 6. claims
    INSERT INTO claims (id, organization_id, document_version_id, claim_text, subject, predicate, object, claim_type, status)
    VALUES 
        (v_claim_1, v_org_id, v_doc_version_1, 'Customers are eligible for automated refunds up to ₹25,000 without supervisor approval.', 'Customer', 'eligible_for_automated_refund', '₹25,000', 'refund_limit', 'outdated'),
        (v_claim_2, v_org_id, v_doc_version_2, 'Standard automated refund limit is capped at ₹10,000. Higher amounts require VP signoff.', 'Customer', 'eligible_for_automated_refund', '₹10,000', 'refund_limit', 'verified')
    ON CONFLICT (id) DO NOTHING;

    -- 7. claim_evidence
    INSERT INTO claim_evidence (claim_id, document_id, evidence_type, section, text_span, start_offset, end_offset, evidence_hash)
    VALUES 
        (v_claim_2, v_doc_id, 'direct_quote', 'Section 3.2 - Automated Thresholds', 'Standard automated refund limit is capped at ₹10,000.', 120, 175, '8f4c281e0123456789abcdef0123456789abcdef0123456789abcdef01234567')
    ON CONFLICT DO NOTHING;

    -- 8. claim_validity
    INSERT INTO claim_validity (claim_id, valid_from, valid_until, version, is_current, validity_status)
    VALUES 
        (v_claim_1, '2025-01-01 00:00:00+00', '2026-08-27 23:59:59+00', 'v1.0', false, 'expired'),
        (v_claim_2, '2026-08-28 00:00:00+00', '2027-12-31 23:59:59+00', 'v2.0', true, 'valid')
    ON CONFLICT DO NOTHING;

    -- 9. claim_trust_scores
    INSERT INTO claim_trust_scores (claim_id, source_score, freshness_score, evidence_score, consistency_score, authority_score, human_score, overall_score)
    VALUES 
        (v_claim_2, 0.98, 0.99, 0.95, 0.92, 0.98, 1.00, 0.96)
    ON CONFLICT DO NOTHING;

    -- 10. claim_conflicts
    INSERT INTO claim_conflicts (claim_a_id, claim_b_id, conflict_type, severity, confidence, resolution_status, resolved_claim_id, resolved_by)
    VALUES 
        (v_claim_1, v_claim_2, 'value_mismatch', 'high', 0.99, 'resolved', v_claim_2, v_user_id)
    ON CONFLICT DO NOTHING;

    -- 11. agents
    INSERT INTO agents (id, organization_id, name, description, agent_type, model_provider, model_name, status)
    VALUES 
        (v_agent_id, v_org_id, 'Billing & Refund Resolution Agent', 'Autonomous agent processing customer billing dispute tickets.', 'billing_agent', 'openai', 'gpt-4o', 'active')
    ON CONFLICT (id) DO NOTHING;

    -- 12. agent_requests
    INSERT INTO agent_requests (id, organization_id, agent_id, query, trust_threshold, max_results, status, completed_at)
    VALUES 
        (v_request_id, v_org_id, v_agent_id, 'What is the maximum allowed automated refund for India customers?', 0.85, 5, 'completed', now())
    ON CONFLICT (id) DO NOTHING;

    -- 13. agent_context_items
    INSERT INTO agent_context_items (request_id, claim_id, rank, trust_score, included, exclusion_reason)
    VALUES 
        (v_request_id, v_claim_2, 1, 0.96, true, NULL),
        (v_request_id, v_claim_1, 2, 0.30, false, 'STALE_CONTEXT: Claim superseded by V2 policy')
    ON CONFLICT DO NOTHING;

    -- 14. human_reviews
    INSERT INTO human_reviews (organization_id, reviewer_id, target_type, target_id, decision, reason, previous_score, new_score)
    VALUES 
        (v_org_id, v_user_id, 'claim', v_claim_2, 'approve', 'Validated against CFO official memo published on 2026-08-28.', 0.90, 0.96)
    ON CONFLICT DO NOTHING;
END $$;
