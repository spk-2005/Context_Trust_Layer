"""phase7_evidence_and_claim_structures

Revision ID: d4e82b79a102
Revises: 7ecf91711f29
Create Date: 2026-11-07 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e82b79a102'
down_revision: Union[str, Sequence[str], None] = '7ecf91711f29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Phase 7 structured fields to claims table
    op.add_column('claims', sa.Column('validation_status', sa.String(length=50), nullable=True))
    op.add_column('claims', sa.Column('extraction_status', sa.String(length=50), nullable=True))
    op.add_column('claims', sa.Column('conditions_data', sa.JSON(), nullable=True))
    op.add_column('claims', sa.Column('exceptions_data', sa.JSON(), nullable=True))
    op.add_column('claims', sa.Column('source_version', sa.String(length=50), nullable=True))
    op.add_column('claims', sa.Column('evidence_relationships', sa.JSON(), nullable=True))
    op.add_column('claims', sa.Column('locator_data', sa.JSON(), nullable=True))

    # 2. Add Phase 7 structured fields to claim_evidence table
    op.add_column('claim_evidence', sa.Column('source_version', sa.String(length=50), nullable=True))
    op.add_column('claim_evidence', sa.Column('locator_data', sa.JSON(), nullable=True))
    op.add_column('claim_evidence', sa.Column('relationship_type', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('claim_evidence', 'relationship_type')
    op.drop_column('claim_evidence', 'locator_data')
    op.drop_column('claim_evidence', 'source_version')

    op.drop_column('claims', 'locator_data')
    op.drop_column('claims', 'evidence_relationships')
    op.drop_column('claims', 'source_version')
    op.drop_column('claims', 'exceptions_data')
    op.drop_column('claims', 'conditions_data')
    op.drop_column('claims', 'extraction_status')
    op.drop_column('claims', 'validation_status')
