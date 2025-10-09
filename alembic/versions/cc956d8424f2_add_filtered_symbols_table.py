"""add_filtered_symbols_table

Revision ID: cc956d8424f2
Revises: dd76ab31bbc4
Create Date: 2025-10-09 13:09:06.859760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc956d8424f2'
down_revision: Union[str, Sequence[str], None] = 'dd76ab31bbc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'filtered_symbols',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('filtered_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_filtered_symbols_symbol', 'filtered_symbols', ['symbol'])
    op.create_index('ix_filtered_symbols_filtered_at', 'filtered_symbols', ['filtered_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_filtered_symbols_filtered_at')
    op.drop_index('ix_filtered_symbols_symbol')
    op.drop_table('filtered_symbols')
