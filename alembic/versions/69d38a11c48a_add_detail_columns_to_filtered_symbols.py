"""add_detail_columns_to_filtered_symbols

Revision ID: 69d38a11c48a
Revises: 3d7a3508fc68
Create Date: 2025-10-10 10:23:15.808032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69d38a11c48a'
down_revision: Union[str, Sequence[str], None] = '3d7a3508fc68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add detail columns to filtered_symbols table
    op.add_column('filtered_symbols', sa.Column('korean_name', sa.String(length=100), nullable=True))
    op.add_column('filtered_symbols', sa.Column('trading_value', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('filtered_symbols', sa.Column('market_cap', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('filtered_symbols', sa.Column('listing_days', sa.Integer(), nullable=True))
    op.add_column('filtered_symbols', sa.Column('current_price', sa.Numeric(precision=20, scale=8), nullable=True))
    op.add_column('filtered_symbols', sa.Column('volatility', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('filtered_symbols', sa.Column('spread', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('filtered_symbols', sa.Column('note', sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop detail columns from filtered_symbols table
    op.drop_column('filtered_symbols', 'note')
    op.drop_column('filtered_symbols', 'spread')
    op.drop_column('filtered_symbols', 'volatility')
    op.drop_column('filtered_symbols', 'current_price')
    op.drop_column('filtered_symbols', 'listing_days')
    op.drop_column('filtered_symbols', 'market_cap')
    op.drop_column('filtered_symbols', 'trading_value')
    op.drop_column('filtered_symbols', 'korean_name')
