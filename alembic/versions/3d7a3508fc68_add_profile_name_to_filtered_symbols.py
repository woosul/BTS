"""add_profile_name_to_filtered_symbols

Revision ID: 3d7a3508fc68
Revises: cc956d8424f2
Create Date: 2025-10-09 13:44:03.663016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d7a3508fc68'
down_revision: Union[str, Sequence[str], None] = 'cc956d8424f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # filtered_symbols 테이블에 profile_name 컬럼 추가
    op.add_column('filtered_symbols', sa.Column('profile_name', sa.String(100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # profile_name 컬럼 삭제
    op.drop_column('filtered_symbols', 'profile_name')
