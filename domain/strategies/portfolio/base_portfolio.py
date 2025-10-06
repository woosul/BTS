"""
BTS 포트폴리오 전략 베이스 클래스

모든 포트폴리오 전략의 기반이 되는 추상 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from core.models import OHLCV
from core.exceptions import StrategyError
from utils.logger import get_logger

logger = get_logger(__name__)


class Position:
    """포지션 정보"""
    def __init__(
        self,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        current_price: Decimal,
        value: Decimal
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = current_price
        self.value = value

    @property
    def profit_loss(self) -> Decimal:
        """손익"""
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def profit_loss_pct(self) -> Decimal:
        """손익률 (%)"""
        if self.entry_price == 0:
            return Decimal("0")
        return ((self.current_price - self.entry_price) / self.entry_price) * 100


class AllocationResult:
    """자금 배분 결과"""
    def __init__(
        self,
        allocations: Dict[str, Decimal],  # {symbol: 배분 금액}
        weights: Dict[str, Decimal],      # {symbol: 비중 (0-1)}
        metadata: Optional[Dict] = None
    ):
        self.allocations = allocations
        self.weights = weights
        self.metadata = metadata or {}

    def get_allocation(self, symbol: str) -> Decimal:
        """특정 심볼의 배분 금액 조회"""
        return self.allocations.get(symbol, Decimal("0"))

    def get_weight(self, symbol: str) -> Decimal:
        """특정 심볼의 비중 조회"""
        return self.weights.get(symbol, Decimal("0"))


class BasePortfolioStrategy(ABC):
    """
    포트폴리오 전략 베이스 클래스

    자금 배분 및 리밸런싱 로직
    """

    def __init__(
        self,
        id: int,
        name: str,
        description: str = "",
        parameters: Optional[Dict] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.parameters = parameters or {}

        # 공통 파라미터
        self.min_allocation = Decimal(str(parameters.get("min_allocation", 10000)))  # 최소 배분 금액
        self.max_positions = int(parameters.get("max_positions", 10))  # 최대 보유 종목 수
        self.reserve_ratio = Decimal(str(parameters.get("reserve_ratio", 0.1)))  # 현금 보유 비율

        logger.info(f"포트폴리오 전략 초기화: {self.name}")

    @abstractmethod
    def calculate_allocation(
        self,
        total_balance: Decimal,
        selected_symbols: List[str],
        current_positions: Optional[Dict[str, Position]] = None,
        market_data: Optional[Dict[str, List[OHLCV]]] = None
    ) -> AllocationResult:
        """
        자금 배분 계산

        Args:
            total_balance: 총 사용 가능 자금
            selected_symbols: 선정된 심볼 리스트
            current_positions: 현재 보유 포지션
            market_data: 시장 데이터 (심볼별 OHLCV)

        Returns:
            AllocationResult: 배분 결과
        """
        pass

    @abstractmethod
    def should_rebalance(
        self,
        current_positions: Dict[str, Position],
        target_allocations: Dict[str, Decimal]
    ) -> bool:
        """
        리밸런싱 필요 여부 판단

        Args:
            current_positions: 현재 포지션
            target_allocations: 목표 배분 금액

        Returns:
            bool: 리밸런싱 필요 여부
        """
        pass

    def validate_parameters(self) -> bool:
        """
        파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            StrategyError: 파라미터가 유효하지 않은 경우
        """
        errors = []

        if self.min_allocation < 0:
            errors.append("min_allocation은 0 이상이어야 합니다")

        if self.max_positions <= 0:
            errors.append("max_positions는 0보다 커야 합니다")

        if not (0 <= self.reserve_ratio < 1):
            errors.append("reserve_ratio는 0과 1 사이여야 합니다")

        if errors:
            raise StrategyError(
                "포트폴리오 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def apply_constraints(
        self,
        total_balance: Decimal,
        allocations: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """
        제약 조건 적용

        Args:
            total_balance: 총 자금
            allocations: 초기 배분

        Returns:
            Dict[str, Decimal]: 제약 조건 적용 후 배분
        """
        # 1. 예비 자금 확보
        reserve = total_balance * self.reserve_ratio
        available = total_balance - reserve

        # 2. 최대 종목 수 제한
        if len(allocations) > self.max_positions:
            # 배분 금액 상위 N개만 선택
            sorted_allocs = sorted(
                allocations.items(),
                key=lambda x: x[1],
                reverse=True
            )
            allocations = dict(sorted_allocs[:self.max_positions])

        # 3. 최소 배분 금액 제한
        allocations = {
            symbol: amount
            for symbol, amount in allocations.items()
            if amount >= self.min_allocation
        }

        # 4. 총액 조정 (사용 가능 자금 내로)
        total_allocated = sum(allocations.values())
        if total_allocated > available:
            scale_factor = available / total_allocated
            allocations = {
                symbol: amount * scale_factor
                for symbol, amount in allocations.items()
            }

        return allocations

    def calculate_weights(
        self,
        allocations: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """
        배분 금액에서 비중 계산

        Args:
            allocations: 배분 금액

        Returns:
            Dict[str, Decimal]: 비중 (0-1)
        """
        total = sum(allocations.values())
        if total == 0:
            return {symbol: Decimal("0") for symbol in allocations.keys()}

        return {
            symbol: amount / total
            for symbol, amount in allocations.items()
        }

    def calculate_position_value(
        self,
        positions: Dict[str, Position]
    ) -> Decimal:
        """
        포지션 총 가치 계산

        Args:
            positions: 포지션 정보

        Returns:
            Decimal: 총 가치
        """
        return sum(pos.value for pos in positions.values())

    def calculate_divergence(
        self,
        current_weights: Dict[str, Decimal],
        target_weights: Dict[str, Decimal]
    ) -> Decimal:
        """
        현재 비중과 목표 비중 간 차이 계산

        Args:
            current_weights: 현재 비중
            target_weights: 목표 비중

        Returns:
            Decimal: 총 차이 (절댓값 합)
        """
        all_symbols = set(current_weights.keys()) | set(target_weights.keys())

        total_divergence = Decimal("0")
        for symbol in all_symbols:
            current = current_weights.get(symbol, Decimal("0"))
            target = target_weights.get(symbol, Decimal("0"))
            total_divergence += abs(current - target)

        return total_divergence

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(id={self.id}, name={self.name}, "
            f"max_positions={self.max_positions})>"
        )
