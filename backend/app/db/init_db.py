import logging
from sqlalchemy import text
from app.db.database import engine

logger = logging.getLogger(__name__)


async def init_db_schema():
    """Ensure all required tables and columns exist in PostgreSQL."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS user_activity_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            user_name VARCHAR(255) NOT NULL DEFAULT 'System',
            user_role VARCHAR(50) NOT NULL DEFAULT 'system',
            action_type VARCHAR(100) NOT NULL,
            target_type VARCHAR(100) NOT NULL,
            target_id VARCHAR(255),
            target_title VARCHAR(500),
            domain VARCHAR(100) NOT NULL DEFAULT 'General',
            details JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_activity_organization ON user_activity_logs(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity_logs(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_activity_created_at ON user_activity_logs(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_activity_action_type ON user_activity_logs(action_type);",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS domain_whitelist JSONB DEFAULT '[]'::jsonb;",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS allowed_auth_methods JSONB DEFAULT '[]'::jsonb;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS title VARCHAR(100);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS domain VARCHAR(100) DEFAULT 'General';",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE SET NULL;",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS connection_config JSONB DEFAULT '{}'::jsonb;",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS domain VARCHAR(100) DEFAULT 'General';",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE SET NULL;",
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(100) DEFAULT 'all';",
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS domain VARCHAR(100) DEFAULT 'global';",
        """
        CREATE TABLE IF NOT EXISTS decision_evaluations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            audit_id VARCHAR(100) NOT NULL UNIQUE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            actor_id VARCHAR(100) NOT NULL,
            actor_role VARCHAR(100) NOT NULL,
            decision_prompt TEXT NOT NULL,
            verdict VARCHAR(50) NOT NULL,
            risk_level VARCHAR(50) NOT NULL,
            reasons JSONB DEFAULT '[]'::jsonb,
            preferred_source VARCHAR(255),
            suggested_action TEXT,
            context_items JSONB DEFAULT '[]'::jsonb,
            audit_token VARCHAR(64) NOT NULL,
            execution_ms NUMERIC(8,2) NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_decision_evaluations_org ON decision_evaluations(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_decision_evaluations_created_at ON decision_evaluations(created_at);",
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            user_name VARCHAR(255) NOT NULL DEFAULT 'Anonymous',
            user_role VARCHAR(50) NOT NULL DEFAULT 'developer',
            title VARCHAR(500) NOT NULL DEFAULT 'New Conversation',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_org_user ON chat_sessions(organization_id, user_id);",
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);",
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            metadata_json JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);",
        """
        CREATE TABLE IF NOT EXISTS webhook_subscriptions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            url VARCHAR(1000) NOT NULL,
            channel_type VARCHAR(50) NOT NULL DEFAULT 'slack',
            min_liability_threshold_usd NUMERIC(12,2) NOT NULL DEFAULT 5000.0,
            trigger_on_block BOOLEAN NOT NULL DEFAULT TRUE,
            trigger_on_review BOOLEAN NOT NULL DEFAULT TRUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            secret_token VARCHAR(255),
            last_triggered_at TIMESTAMPTZ,
            last_status_code INTEGER,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_webhooks_organization ON webhook_subscriptions(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhook_subscriptions(organization_id, is_active);",
        """
        CREATE TABLE IF NOT EXISTS webhook_dispatch_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            webhook_id UUID NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            liability_prevented_usd NUMERIC(12,2) NOT NULL DEFAULT 0.0,
            actor_id VARCHAR(100) NOT NULL DEFAULT 'system',
            verdict VARCHAR(50) NOT NULL,
            response_status INTEGER,
            response_body TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_dispatch_webhook ON webhook_dispatch_logs(webhook_id);",
        "CREATE INDEX IF NOT EXISTS idx_dispatch_org ON webhook_dispatch_logs(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_dispatch_created_at ON webhook_dispatch_logs(created_at);",
        """
        CREATE TABLE IF NOT EXISTS hitl_escalations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            audit_id VARCHAR(100) NOT NULL,
            actor_id VARCHAR(100) NOT NULL,
            actor_role VARCHAR(100) NOT NULL,
            action_prompt TEXT NOT NULL,
            reasons JSONB DEFAULT '[]'::jsonb,
            category VARCHAR(100) NOT NULL DEFAULT 'Operational Triage',
            liability_prevented_usd NUMERIC(12,2) NOT NULL DEFAULT 0.0,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            suggested_action TEXT,
            resolved_by_name VARCHAR(255),
            resolved_by_role VARCHAR(100),
            resolution_decision VARCHAR(50),
            resolution_notes TEXT,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_hitl_org ON hitl_escalations(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_hitl_status ON hitl_escalations(organization_id, status);",
        "CREATE INDEX IF NOT EXISTS idx_hitl_created_at ON hitl_escalations(created_at);",
    ]

    async with engine.begin() as conn:
        for stmt in statements:
            stmt_clean = stmt.strip()
            if stmt_clean:
                await conn.execute(text(stmt_clean))
    logger.info("Database schema initialized successfully.")
