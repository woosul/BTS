"""
BTS 지갑 서비스

지갑 비즈니스 로직 처리
Streamlit과 FastAPI에서 공통 사용
"""
from typing import List, Optional, Dict
from decimal import Decimal
from sqlalchemy.orm import Session

from infrastructure.repositories.wallet_repository import (
    WalletRepository,
    AssetHoldingRepository
)
from infrastructure.database.models import WalletORM, AssetHoldingORM
from domain.entities.wallet import Wallet
from core.models import (
    WalletCreate,
    WalletResponse,
    WalletUpdate,
    AssetBalance
)
from core.enums import WalletType, TransactionType
from core.exceptions import (
    WalletNotFoundError,
    InsufficientFundsError,
    InvalidTransactionError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class WalletService:
    """
    지갑 서비스

    FastAPI/Streamlit 공통 사용:
    - FastAPI: Depends(get_db)로 세션 주입
    - Streamlit: get_db_session() 컨텍스트 매니저 사용
    """

    def __init__(self, db: Session):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.holding_repo = AssetHoldingRepository(db)

    # ===== 지갑 관리 =====
    def create_wallet(self, wallet_data: WalletCreate) -> WalletResponse:
        """
        지갑 생성

        Args:
            wallet_data: 지갑 생성 데이터

        Returns:
            WalletResponse: 생성된 지갑 정보
        """
        # 지갑 생성
        wallet_orm = self.wallet_repo.create_wallet(
            name=wallet_data.name,
            wallet_type=wallet_data.wallet_type,
            initial_balance=wallet_data.initial_balance
        )

        logger.info(f"지갑 생성: {wallet_orm.name} (ID: {wallet_orm.id})")

        return self._to_response(wallet_orm)

    def get_wallet(self, wallet_id: int) -> WalletResponse:
        """
        지갑 조회

        Args:
            wallet_id: 지갑 ID

        Returns:
            WalletResponse: 지갑 정보

        Raises:
            WalletNotFoundError: 지갑을 찾을 수 없음
        """
        wallet_orm = self.wallet_repo.get_by_id(wallet_id)
        if not wallet_orm:
            raise WalletNotFoundError(
                "지갑을 찾을 수 없습니다",
                {"wallet_id": wallet_id}
            )

        return self._to_response(wallet_orm)

    def get_all_wallets(
        self,
        wallet_type: Optional[WalletType] = None
    ) -> List[WalletResponse]:
        """
        지갑 목록 조회

        Args:
            wallet_type: 지갑 유형 필터 (선택)

        Returns:
            List[WalletResponse]: 지갑 목록
        """
        if wallet_type == WalletType.VIRTUAL:
            wallets = self.wallet_repo.get_virtual_wallets()
        elif wallet_type == WalletType.REAL:
            wallets = self.wallet_repo.get_real_wallets()
        else:
            wallets = self.wallet_repo.get_all()

        return [self._to_response(w) for w in wallets]

    def update_wallet(
        self,
        wallet_id: int,
        wallet_data: WalletUpdate
    ) -> WalletResponse:
        """
        지갑 정보 업데이트

        Args:
            wallet_id: 지갑 ID
            wallet_data: 업데이트 데이터

        Returns:
            WalletResponse: 업데이트된 지갑 정보
        """
        # 지갑 존재 확인
        wallet_orm = self.wallet_repo.get_by_id_or_raise(wallet_id)

        # 업데이트
        update_dict = wallet_data.model_dump(exclude_unset=True)
        if update_dict:
            wallet_orm = self.wallet_repo.update(wallet_id, **update_dict)

        logger.info(f"지갑 업데이트: {wallet_orm.name}")
        return self._to_response(wallet_orm)

    def delete_wallet(self, wallet_id: int) -> bool:
        """
        지갑 삭제

        Args:
            wallet_id: 지갑 ID

        Returns:
            bool: 삭제 성공 여부
        """
        success = self.wallet_repo.delete(wallet_id)
        if success:
            logger.info(f"지갑 삭제: ID {wallet_id}")
        return success

    # ===== 잔고 관리 =====
    def deposit(
        self,
        wallet_id: int,
        amount: Decimal,
        description: str = ""
    ) -> WalletResponse:
        """
        입금

        Args:
            wallet_id: 지갑 ID
            amount: 입금액
            description: 설명

        Returns:
            WalletResponse: 업데이트된 지갑 정보
        """
        wallet_orm = self.wallet_repo.get_by_id_or_raise(wallet_id)

        # 도메인 엔티티로 변환하여 비즈니스 로직 실행
        wallet = self._to_entity(wallet_orm)
        new_balance = wallet.deposit(amount, description)

        # DB 업데이트
        wallet_orm = self.wallet_repo.update_balance(wallet_id, new_balance)

        logger.info(f"입금 완료: {wallet_orm.name} +{amount:,.0f} KRW")
        return self._to_response(wallet_orm)

    def withdraw(
        self,
        wallet_id: int,
        amount: Decimal,
        description: str = ""
    ) -> WalletResponse:
        """
        출금

        Args:
            wallet_id: 지갑 ID
            amount: 출금액
            description: 설명

        Returns:
            WalletResponse: 업데이트된 지갑 정보

        Raises:
            InsufficientFundsError: 잔고 부족
        """
        wallet_orm = self.wallet_repo.get_by_id_or_raise(wallet_id)

        wallet = self._to_entity(wallet_orm)
        new_balance = wallet.withdraw(amount, description)

        wallet_orm = self.wallet_repo.update_balance(wallet_id, new_balance)

        logger.info(f"출금 완료: {wallet_orm.name} -{amount:,.0f} KRW")
        return self._to_response(wallet_orm)

    # ===== 자산 관리 =====
    def add_asset(
        self,
        wallet_id: int,
        symbol: str,
        quantity: Decimal,
        price: Decimal
    ) -> AssetBalance:
        """
        자산 추가 (매수)

        Args:
            wallet_id: 지갑 ID
            symbol: 심볼
            quantity: 수량
            price: 가격

        Returns:
            AssetBalance: 자산 잔고
        """
        # 기존 보유 조회
        holding = self.holding_repo.get_holding(wallet_id, symbol)

        if holding:
            # 평균 단가 계산
            old_quantity = holding.quantity
            old_avg_price = holding.avg_price
            new_quantity = old_quantity + quantity
            new_avg_price = (
                (old_quantity * old_avg_price + quantity * price) / new_quantity
            )
        else:
            new_quantity = quantity
            new_avg_price = price

        # 보유 업데이트
        holding = self.holding_repo.update_holding(
            wallet_id=wallet_id,
            symbol=symbol,
            quantity=new_quantity,
            avg_price=new_avg_price
        )

        logger.info(f"자산 추가: {symbol} +{quantity:.8f}")

        return AssetBalance(
            symbol=holding.symbol,
            quantity=holding.quantity,
            avg_price=holding.avg_price,
            current_price=price,  # 현재가는 별도 조회 필요
            total_value=holding.quantity * price,
            profit_loss=Decimal("0"),  # 추후 계산
            profit_loss_rate=Decimal("0")
        )

    def remove_asset(
        self,
        wallet_id: int,
        symbol: str,
        quantity: Decimal
    ) -> Optional[AssetBalance]:
        """
        자산 제거 (매도)

        Args:
            wallet_id: 지갑 ID
            symbol: 심볼
            quantity: 수량

        Returns:
            Optional[AssetBalance]: 남은 자산 잔고 (전량 매도 시 None)

        Raises:
            InsufficientFundsError: 보유 수량 부족
        """
        holding = self.holding_repo.get_holding(wallet_id, symbol)
        if not holding:
            raise InsufficientFundsError(
                f"{symbol} 보유 내역이 없습니다",
                {"symbol": symbol}
            )

        if holding.quantity < quantity:
            raise InsufficientFundsError(
                f"{symbol} 보유 수량이 부족합니다",
                {
                    "symbol": symbol,
                    "required": quantity,
                    "available": holding.quantity
                }
            )

        new_quantity = holding.quantity - quantity

        if new_quantity == 0:
            # 전량 매도
            self.holding_repo.remove_holding(wallet_id, symbol)
            logger.info(f"자산 전량 매도: {symbol}")
            return None
        else:
            # 일부 매도
            holding = self.holding_repo.update_holding(
                wallet_id=wallet_id,
                symbol=symbol,
                quantity=new_quantity,
                avg_price=holding.avg_price
            )
            logger.info(f"자산 제거: {symbol} -{quantity:.8f}")

            return AssetBalance(
                symbol=holding.symbol,
                quantity=holding.quantity,
                avg_price=holding.avg_price,
                current_price=holding.avg_price,
                total_value=holding.quantity * holding.avg_price,
                profit_loss=Decimal("0"),
                profit_loss_rate=Decimal("0")
            )

    def get_asset_holdings(self, wallet_id: int) -> List[AssetBalance]:
        """
        지갑의 자산 보유 목록 조회

        Args:
            wallet_id: 지갑 ID

        Returns:
            List[AssetBalance]: 자산 목록
        """
        holdings = self.holding_repo.get_wallet_holdings(wallet_id)

        return [
            AssetBalance(
                symbol=h.symbol,
                quantity=h.quantity,
                avg_price=h.avg_price,
                current_price=h.avg_price,  # 실시간 가격은 별도 조회 필요
                total_value=h.quantity * h.avg_price,
                profit_loss=Decimal("0"),
                profit_loss_rate=Decimal("0")
            )
            for h in holdings
        ]

    # ===== 변환 메서드 =====
    def _to_entity(self, wallet_orm: WalletORM) -> Wallet:
        """ORM → 도메인 엔티티 변환"""
        wallet = Wallet(
            id=wallet_orm.id,
            name=wallet_orm.name,
            wallet_type=wallet_orm.wallet_type,
            balance_krw=wallet_orm.balance_krw,
            created_at=wallet_orm.created_at,
            updated_at=wallet_orm.updated_at
        )

        # 자산 보유 로드
        holdings = self.holding_repo.get_wallet_holdings(wallet_orm.id)
        for h in holdings:
            wallet._holdings[h.symbol] = {
                "quantity": h.quantity,
                "avg_price": h.avg_price,
                "current_price": h.avg_price,
            }

        return wallet

    def _to_response(self, wallet_orm: WalletORM) -> WalletResponse:
        """ORM → Response 모델 변환"""
        # 총 자산 가치 계산
        holdings = self.holding_repo.get_wallet_holdings(wallet_orm.id)
        asset_value = sum(
            h.quantity * h.avg_price for h in holdings
        )
        total_value = wallet_orm.balance_krw + asset_value

        return WalletResponse(
            id=wallet_orm.id,
            name=wallet_orm.name,
            wallet_type=wallet_orm.wallet_type,
            balance_krw=wallet_orm.balance_krw,
            total_value_krw=total_value,
            created_at=wallet_orm.created_at,
            updated_at=wallet_orm.updated_at
        )


if __name__ == "__main__":
    from infrastructure.database.connection import get_db_session

    print("=== 지갑 서비스 테스트 ===")

    with get_db_session() as db:
        service = WalletService(db)

        # 지갑 생성
        wallet_data = WalletCreate(
            name="테스트 가상지갑",
            wallet_type=WalletType.VIRTUAL,
            initial_balance=Decimal("10000000")
        )
        wallet = service.create_wallet(wallet_data)
        print(f"\n1. 지갑 생성: {wallet.name} (ID: {wallet.id})")
        print(f"   잔고: {wallet.balance_krw:,.0f} KRW")

        # 입금
        wallet = service.deposit(wallet.id, Decimal("5000000"), "추가 입금")
        print(f"\n2. 입금 후: {wallet.balance_krw:,.0f} KRW")

        # 자산 추가
        asset = service.add_asset(
            wallet.id,
            "BTC",
            Decimal("0.1"),
            Decimal("50000000")
        )
        print(f"\n3. 자산 추가: {asset.symbol} - {asset.quantity:.8f}")

        # 보유 조회
        holdings = service.get_asset_holdings(wallet.id)
        print(f"\n4. 보유 자산: {len(holdings)}개")
        for h in holdings:
            print(f"   - {h.symbol}: {h.quantity:.8f} @ {h.avg_price:,.0f} KRW")

        # 지갑 조회
        wallet = service.get_wallet(wallet.id)
        print(f"\n5. 총 자산: {wallet.total_value_krw:,.0f} KRW")
