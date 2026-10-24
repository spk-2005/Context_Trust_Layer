"""add_folders_workspace

Revision ID: 7ecf91711f29
Revises: aafacd791d21
Create Date: 2026-10-23 14:55:08.628050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ecf91711f29'
down_revision: Union[str, Sequence[str], None] = 'aafacd791d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create folders table with composite candidate key and depth check
    op.create_table(
        'folders',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('depth', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_system', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
        sa.Column('folder_type', sa.String(length=50), server_default=sa.text("'general'"), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_folders_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_folders_creator', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'id', name='uq_folders_org_id'),
        sa.CheckConstraint('depth >= 0 AND depth <= 6', name='chk_folders_depth')
    )

    # 2. Self-referencing composite foreign key ensuring same-tenant hierarchy
    op.create_foreign_key(
        'fk_folders_parent_same_tenant',
        'folders',
        'folders',
        ['organization_id', 'parent_id'],
        ['organization_id', 'id'],
        ondelete='RESTRICT'
    )

    # 3. Root normalized name unique index (parent_id IS NULL)
    op.execute("""
        CREATE UNIQUE INDEX uq_folders_root_normalized_name
        ON folders (organization_id, lower(trim(name)))
        WHERE parent_id IS NULL;
    """)

    # 4. Sibling normalized name unique index (parent_id IS NOT NULL)
    op.execute("""
        CREATE UNIQUE INDEX uq_folders_sibling_normalized_name
        ON folders (organization_id, parent_id, lower(trim(name)))
        WHERE parent_id IS NOT NULL;
    """)

    # 5. Strict single system Inbox per organization partial unique index
    op.execute("""
        CREATE UNIQUE INDEX uq_folders_single_system_inbox
        ON folders (organization_id)
        WHERE is_system = TRUE AND folder_type = 'inbox';
    """)

    # 6. Performance indexes
    op.create_index('idx_folders_org_parent', 'folders', ['organization_id', 'parent_id'])
    op.create_index('idx_folders_org_depth', 'folders', ['organization_id', 'depth'])

    # 7. Add folder_id to documents with same-tenant composite foreign key
    op.add_column('documents', sa.Column('folder_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_documents_folder_same_tenant',
        'documents',
        'folders',
        ['organization_id', 'folder_id'],
        ['organization_id', 'id'],
        ondelete='RESTRICT'
    )
    op.create_index('idx_documents_org_folder', 'documents', ['organization_id', 'folder_id'])

    # 8. Idempotent Data Migration: ensure every organization has a system Inbox
    op.execute("""
        INSERT INTO folders (id, organization_id, name, depth, is_system, folder_type, created_at, updated_at)
        SELECT gen_random_uuid(), o.id, 'Inbox', 0, TRUE, 'inbox', NOW(), NOW()
        FROM organizations o
        WHERE NOT EXISTS (
            SELECT 1 FROM folders f
            WHERE f.organization_id = o.id AND f.is_system = TRUE AND f.folder_type = 'inbox'
        );
    """)

    # 9. Assign any existing unfiled documents to their organization's Inbox
    op.execute("""
        UPDATE documents d
        SET folder_id = f.id
        FROM folders f
        WHERE d.organization_id = f.organization_id
          AND f.is_system = TRUE
          AND f.folder_type = 'inbox'
          AND d.folder_id IS NULL;
    """)


def downgrade() -> None:
    # 1. Drop foreign key and column from documents
    op.drop_constraint('fk_documents_folder_same_tenant', 'documents', type_='foreignkey')
    op.drop_index('idx_documents_org_folder', table_name='documents')
    op.drop_column('documents', 'folder_id')

    # 2. Drop folders indexes & table
    op.execute("DROP INDEX IF EXISTS uq_folders_single_system_inbox;")
    op.execute("DROP INDEX IF EXISTS uq_folders_sibling_normalized_name;")
    op.execute("DROP INDEX IF EXISTS uq_folders_root_normalized_name;")
    op.drop_index('idx_folders_org_depth', table_name='folders')
    op.drop_index('idx_folders_org_parent', table_name='folders')
    op.drop_constraint('fk_folders_parent_same_tenant', 'folders', type_='foreignkey')
    op.drop_table('folders')

