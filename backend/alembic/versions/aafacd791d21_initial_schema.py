"""initial schema

Revision ID: aafacd791d21
Revises: 
Create Date: 2026-08-29 13:27:40.083893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aafacd791d21'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('active', 'suspended', 'deleted', name='organization_status'), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'data_owner', 'reviewer', 'developer', 'viewer', name='user_role'), server_default=sa.text("'viewer'"), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'deleted', 'processing', 'failed', name='record_status'), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_users_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'email', name='uq_users_org_email')
    )
    op.create_index('idx_users_organization', 'users', ['organization_id'], unique=False)

    # 3. data_sources
    op.create_table(
        'data_sources',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('authority_level', sa.Integer(), server_default=sa.text('50'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'deleted', 'processing', 'failed', name='record_status'), server_default=sa.text("'active'"), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('authority_level BETWEEN 0 AND 100', name='chk_authority_level'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_data_sources_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'source_type', 'external_id', name='uq_data_source_external')
    )
    op.create_index('idx_data_sources_organization', 'data_sources', ['organization_id'], unique=False)

    # 4. documents
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('content_uri', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'deleted', 'processing', 'failed', name='record_status'), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_documents_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], name='fk_documents_source', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'source_id', 'external_id', name='uq_document_external')
    )
    op.create_index('idx_documents_organization', 'documents', ['organization_id'], unique=False)
    op.create_index('idx_documents_source', 'documents', ['source_id'], unique=False)

    # 5. document_versions
    op.create_table(
        'document_versions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content_uri', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('modified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_document_versions_document', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'version_number', name='uq_document_version')
    )
    op.create_index('idx_document_versions_document', 'document_versions', ['document_id'], unique=False)
    op.create_index('uq_current_document_version', 'document_versions', ['document_id'], unique=True, postgresql_where=sa.text('is_current = TRUE'))

    # 6. claims
    op.create_table(
        'claims',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('document_version_id', sa.UUID(), nullable=False),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('predicate', sa.String(length=255), nullable=True),
        sa.Column('object', sa.Text(), nullable=True),
        sa.Column('claim_type', sa.String(length=50), nullable=True),
        sa.Column('extraction_method', sa.String(length=50), nullable=True),
        sa.Column('extraction_model', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('candidate', 'verified', 'rejected', 'outdated', 'conflicted', 'active', name='claim_status'), server_default=sa.text("'candidate'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], name='fk_claims_document_version', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_claims_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_claims_document_version', 'claims', ['document_version_id'], unique=False)
    op.create_index('idx_claims_organization', 'claims', ['organization_id'], unique=False)
    op.create_index('idx_claims_status', 'claims', ['status'], unique=False)

    # 7. claim_evidence
    op.create_table(
        'claim_evidence',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('claim_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section', sa.String(length=500), nullable=True),
        sa.Column('text_span', sa.Text(), nullable=False),
        sa.Column('start_offset', sa.Integer(), nullable=True),
        sa.Column('end_offset', sa.Integer(), nullable=True),
        sa.Column('evidence_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('page_number IS NULL OR page_number > 0', name='chk_page_number'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], name='fk_claim_evidence_claim', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_claim_evidence_document', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. claim_validity
    op.create_table(
        'claim_validity',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('claim_id', sa.UUID(), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
        sa.Column('validity_status', sa.String(length=50), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from', name='chk_validity_range'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], name='fk_claim_validity_claim', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. claim_trust_scores
    op.create_table(
        'claim_trust_scores',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('claim_id', sa.UUID(), nullable=False),
        sa.Column('source_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('freshness_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('evidence_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('consistency_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('authority_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('human_score', sa.Numeric(precision=5, scale=4), server_default=sa.text('0.0000'), nullable=False),
        sa.Column('overall_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('scoring_model', sa.String(length=100), nullable=True),
        sa.Column('scoring_version', sa.String(length=50), nullable=True),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('authority_score BETWEEN 0 AND 1', name='chk_authority_score'),
        sa.CheckConstraint('consistency_score BETWEEN 0 AND 1', name='chk_consistency_score'),
        sa.CheckConstraint('evidence_score BETWEEN 0 AND 1', name='chk_evidence_score'),
        sa.CheckConstraint('freshness_score BETWEEN 0 AND 1', name='chk_freshness_score'),
        sa.CheckConstraint('human_score BETWEEN 0 AND 1', name='chk_human_score'),
        sa.CheckConstraint('overall_score BETWEEN 0 AND 1', name='chk_overall_score'),
        sa.CheckConstraint('source_score BETWEEN 0 AND 1', name='chk_source_score'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], name='fk_trust_scores_claim', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_claim_trust_claim', 'claim_trust_scores', ['claim_id'], unique=False)
    op.create_index('idx_claim_trust_overall', 'claim_trust_scores', [sa.literal_column('overall_score DESC')], unique=False)

    # 10. claim_conflicts
    op.create_table(
        'claim_conflicts',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('claim_a_id', sa.UUID(), nullable=False),
        sa.Column('claim_b_id', sa.UUID(), nullable=False),
        sa.Column('conflict_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('resolution_status', sa.Enum('detected', 'human_review_required', 'resolved', 'dismissed', name='conflict_status'), server_default=sa.text("'detected'"), nullable=False),
        sa.Column('resolved_claim_id', sa.UUID(), nullable=True),
        sa.Column('resolved_by', sa.UUID(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('claim_a_id <> claim_b_id', name='chk_different_claims'),
        sa.CheckConstraint('confidence BETWEEN 0 AND 1', name='chk_conflict_confidence'),
        sa.ForeignKeyConstraint(['claim_a_id'], ['claims.id'], name='fk_conflict_claim_a', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claim_b_id'], ['claims.id'], name='fk_conflict_claim_b', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], name='fk_conflict_resolved_by', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_claim_id'], ['claims.id'], name='fk_conflict_resolved_claim', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_conflicts_claim_a', 'claim_conflicts', ['claim_a_id'], unique=False)
    op.create_index('idx_conflicts_claim_b', 'claim_conflicts', ['claim_b_id'], unique=False)
    op.create_index('idx_conflicts_status', 'claim_conflicts', ['resolution_status'], unique=False)
    op.create_index('uq_claim_conflict_pair', 'claim_conflicts', [sa.literal_column('LEAST(claim_a_id, claim_b_id)'), sa.literal_column('GREATEST(claim_a_id, claim_b_id)')], unique=True)

    # 11. agents
    op.create_table(
        'agents',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agent_type', sa.String(length=50), nullable=True),
        sa.Column('model_provider', sa.String(length=100), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'deleted', 'processing', 'failed', name='record_status'), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_agents_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agents_organization', 'agents', ['organization_id'], unique=False)

    # 12. agent_requests
    op.create_table(
        'agent_requests',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('trust_threshold', sa.Numeric(precision=5, scale=4), server_default=sa.text('0.8000'), nullable=False),
        sa.Column('max_results', sa.Integer(), server_default=sa.text('10'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('max_results > 0', name='chk_max_results'),
        sa.CheckConstraint('trust_threshold BETWEEN 0 AND 1', name='chk_trust_threshold'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], name='fk_agent_requests_agent', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_agent_requests_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_requests_agent', 'agent_requests', ['agent_id'], unique=False)
    op.create_index('idx_agent_requests_organization', 'agent_requests', ['organization_id'], unique=False)

    # 13. agent_context_items
    op.create_table(
        'agent_context_items',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('request_id', sa.UUID(), nullable=False),
        sa.Column('claim_id', sa.UUID(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('trust_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('included', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.Column('exclusion_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('rank > 0', name='chk_context_rank'),
        sa.CheckConstraint('trust_score IS NULL OR (trust_score BETWEEN 0 AND 1)', name='chk_context_trust_score'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], name='fk_context_claim', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['request_id'], ['agent_requests.id'], name='fk_context_request', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id', 'claim_id', name='uq_request_claim')
    )
    op.create_index('idx_context_items_claim', 'agent_context_items', ['claim_id'], unique=False)
    op.create_index('idx_context_items_request', 'agent_context_items', ['request_id'], unique=False)

    # 14. human_reviews
    op.create_table(
        'human_reviews',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('reviewer_id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('decision', sa.Enum('approve', 'reject', 'override', 'mark_outdated', 'merge', 'escalate', name='review_decision'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('previous_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('new_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('new_score IS NULL OR (new_score BETWEEN 0 AND 1)', name='chk_new_score'),
        sa.CheckConstraint('previous_score IS NULL OR (previous_score BETWEEN 0 AND 1)', name='chk_previous_score'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_human_reviews_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], name='fk_human_reviews_reviewer', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_human_reviews_organization', 'human_reviews', ['organization_id'], unique=False)
    op.create_index('idx_human_reviews_target', 'human_reviews', ['target_type', 'target_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_human_reviews_target', table_name='human_reviews')
    op.drop_index('idx_human_reviews_organization', table_name='human_reviews')
    op.drop_table('human_reviews')
    op.drop_index('idx_context_items_request', table_name='agent_context_items')
    op.drop_index('idx_context_items_claim', table_name='agent_context_items')
    op.drop_table('agent_context_items')
    op.drop_index('idx_agent_requests_organization', table_name='agent_requests')
    op.drop_index('idx_agent_requests_agent', table_name='agent_requests')
    op.drop_table('agent_requests')
    op.drop_index('idx_agents_organization', table_name='agents')
    op.drop_table('agents')
    op.drop_index('uq_claim_conflict_pair', table_name='claim_conflicts')
    op.drop_index('idx_conflicts_status', table_name='claim_conflicts')
    op.drop_index('idx_conflicts_claim_b', table_name='claim_conflicts')
    op.drop_index('idx_conflicts_claim_a', table_name='claim_conflicts')
    op.drop_table('claim_conflicts')
    op.drop_table('claim_validity')
    op.drop_index('idx_claim_trust_overall', table_name='claim_trust_scores')
    op.drop_index('idx_claim_trust_claim', table_name='claim_trust_scores')
    op.drop_table('claim_trust_scores')
    op.drop_table('claim_evidence')
    op.drop_index('idx_claims_status', table_name='claims')
    op.drop_index('idx_claims_organization', table_name='claims')
    op.drop_index('idx_claims_document_version', table_name='claims')
    op.drop_table('claims')
    op.drop_index('uq_current_document_version', table_name='document_versions', postgresql_where=sa.text('is_current = TRUE'))
    op.drop_index('idx_document_versions_document', table_name='document_versions')
    op.drop_table('document_versions')
    op.drop_index('idx_documents_source', table_name='documents')
    op.drop_index('idx_documents_organization', table_name='documents')
    op.drop_table('documents')
    op.drop_index('idx_data_sources_organization', table_name='data_sources')
    op.drop_table('data_sources')
    op.drop_index('idx_users_organization', table_name='users')
    op.drop_table('users')
    op.drop_table('organizations')
