"""
BTS 지갑 Repository

지갑 데이터 접근 계층
"""
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.orm import Session

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import WalletORM, AssetHoldingORM
from core.enums import WalletType
from core.exceptions import RecordNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)


class WalletRepository(BaseRepository[WalletORM]):
    """지갑 Repository"""

    def __init__(self, db: Session):
        super().__init__(WalletORM, db)

    def create_wallet(
        self,
        name: str,
        wallet_type: WalletType,
        initial_balance: Decimal = Decimal("0")
    ) -> WalletORM:
        """
        지갑 생성

        Args:
            name: 지갑 이름
            wallet_type: 지갑 유형
            initial_balance: 초기 잔고

        Returns:
            WalletORM: 생성된 지갑
        """
        wallet = self.create(
            name=name,
            wallet_type=wallet_type,
            balance_krw=initial_balance
        )
        logger.info(f"지갑 생성 완료: {wallet.name} (잔고: {initial_balance:,.0f} KRW)")
        return wallet

    def get_by_name(self, name: str) -> Optional[WalletORM]:
        """
        이름으로 지갑 조회

        Args:
            name: 지갑 이름

        Returns:
            Optional[WalletORM]: 지갑 또는 None
        """
        return self.get_by_field("name", name)

    def update_balance(self, wallet_id: int, new_balance: Decimal) -> WalletORM:
        """
        잔고 업데이트

        Args:
            wallet_id: 지갑 ID
            new_balance: 새로운 잔고

        Returns:
            WalletORM: 업데이트된 지갑
        """
        wallet = self.update(wallet_id, balance_krw=new_balance)
        logger.debug(f"지갑 잔고 업데이트: {wallet.name} -> {new_balance:,.0f} KRW")
        return wallet

    def get_virtual_wallets(self) -> List[WalletORM]:
        """
        가상지갑 목록 조회

        Returns:
            List[WalletORM]: 가상지갑 목록
        """
        return self.filter_by(wallet_type=WalletType.VIRTUAL)

    def get_real_wallets(self) -> List[WalletORM]:
        """
        실제지갑 목록 조회

        Returns:
            List[WalletORM]: 실제지갑 목록
        """
        return self.filter_by(wallet_type=WalletType.REAL)


class AssetHoldingRepository(BaseRepository[AssetHoldingORM]):
    """자산 보유 Repository"""

    def __init__(self, db: Session):
        super().__init__(AssetHoldingORM, db)

    def get_holding(
        self,
        wallet_id: int,
        symbol: str
    ) -> Optional[AssetHoldingORM]:
        """
        특정 지갑의 자산 보유 조회

        Args:
            wallet_id: 지갑 ID
            symbol: 심볼

        Returns:
            Optional[AssetHoldingORM]: 보유 내역 또는 None
        """
        holdings = self.filter_by(wallet_id=wallet_id, symbol=symbol)
        return holdings[0] if holdings else None

    def get_wallet_holdings(self, wallet_id: int) -> List[AssetHoldingORM]:
        """
        지갑의 모든 자산 보유 조회

        Args:
            wallet_id: 지갑 ID

        Returns:
            List[AssetHoldingORM]: 보유 내역 목록
        """
        return self.filter_by(wallet_id=wallet_id)

    def update_holding(
        self,
        wallet_id: int,
        symbol: str,
        quantity: Decimal,
        avg_price: Decimal
    ) -> AssetHoldingORM:
        """
        자산 보유 업데이트 또는 생성

        Args:
            wallet_id: 지갑 ID
            symbol: 심볼
            quantity: 수량
            avg_price: 평균가

        Returns:
            AssetHoldingORM: 보유 내역
        """
        holding = self.get_holding(wallet_id, symbol)

        if holding:
            # 업데이트
            holding = self.update(
                holding.id,
                quantity=quantity,
                avg_price=avg_price
            )
            logger.debug(f"자산 업데이트: {symbol} -> {quantity:.8f}")
        else:
            # 생성
            holding = self.create(
                wallet_id=wallet_id,
                symbol=symbol,
                quantity=quantity,
                avg_price=avg_price
            )
            logger.info(f"자산 추가: {symbol} -> {quantity:.8f}")

        return holding

    def remove_holding(self, wallet_id: int, symbol: str) -> bool:
        """
        자산 보유 삭제

        Args:
            wallet_id: 지갑 ID
            symbol: 심볼

        Returns:
            bool: 삭제 성공 여부
        """
        holding = self.get_holding(wallet_id, symbol)
        if holding:
            self.delete(holding.id)
            logger.info(f"자산 삭제: {symbol}")
            return True
        return False


if __name__ == "__main__":
    from infrastructure.database.connection import get_db_session

    print("=== 지갑 Repository 테스트 ===")

    with get_db_session() as db:
        # 지갑 Repository
        wallet_repo = WalletRepository(db)

        # 지갑 생성
        wallet = wallet_repo.create_wallet(
            name="테스트 가상지갑",
            wallet_type=WalletType.VIRTUAL,
            initial_balance=Decimal("10000000")
        )
        print(f"\n1. 지갑 생성: {wallet.name} (ID: {wallet.id})")

        # 지갑 조회
        found = wallet_repo.get_by_id(wallet.id)
        print(f"\n2. 지갑 조회: {found.name} - {found.balance_krw:,.0f} KRW")

        # 자산 보유 Repository
        holding_repo = AssetHoldingRepository(db)

        # 자산 추가
        holding = holding_repo.update_holding(
            wallet_id=wallet.id,
            symbol="BTC",
            quantity=Decimal("0.1"),
            avg_price=Decimal("50000000")
        )
        print(f"\n3. 자산 추가: {holding.symbol} - {holding.quantity:.8f}")

        # 보유 조회
        all_holdings = holding_repo.get_wallet_holdings(wallet.id)
        print(f"\n4. 보유 자산: {len(all_holdings)}개")
        for h in all_holdings:
            print(f"   - {h.symbol}: {h.quantity:.8f} @ {h.avg_price:,.0f} KRW")
