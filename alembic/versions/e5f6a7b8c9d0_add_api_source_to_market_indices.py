"""add api_source to market_indices

Revision ID: e5f6a7b8c9d0
Revises: dd76ab31bbc4
Create Date: 2025-10-18 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = '9fc017e185bd'  # change_market_indices_to_timeseries 이후
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    market_indices 테이블에 api_source 컬럼 추가
    - binance: Binance API에서 수집
    - coingecko: CoinGecko API에서 수집
    - null: 기존 데이터 또는 API 소스 없음
    """
    # api_source 컬럼 추가 (nullable)
    op.add_column('market_indices', sa.Column('api_source', sa.String(50), nullable=True))
    
    # 기존 coingecko_top_coins 데이터에 api_source 설정
    op.execute("""
        UPDATE market_indices 
        SET api_source = 'coingecko' 
        WHERE code = 'coingecko_top_coins'
    """)
    
    # 기존 binance_top_coins 데이터가 있다면 api_source 설정
    op.execute("""
        UPDATE market_indices 
        SET api_source = 'binance' 
        WHERE code = 'binance_top_coins'
    """)
    
    # 인덱스 생성 (api_source + created_at 복합 조회 최적화)
    op.create_index(
        'ix_market_indices_api_source_created_at',
        'market_indices',
        ['api_source', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    """api_source 컬럼 제거"""
    op.drop_index('ix_market_indices_api_source_created_at', table_name='market_indices')
    op.drop_column('market_indices', 'api_source')
