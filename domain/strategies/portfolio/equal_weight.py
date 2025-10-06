"""
BTS 균등 배분 포트폴리오 전략

모든 종목에 동일 금액 배분
"""
from typing import Dict, List, Optional
from decimal import Decimal

from domain.strategies.portfolio.base_portfolio import (
    BasePortfolioStrategy,
    Position,
    AllocationResult
)
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class EqualWeightPortfolio(BasePortfolioStrategy):
    """
    균등 배분 포트폴리오

    모든 종목에 동일한 금액 배분
    가장 단순하면서도 효과적인 전략
    """

    def __init__(
        self,
        id: int,
        name: str = "Equal Weight Portfolio",
        description: str = "균등 배분 포트폴리오",
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "min_allocation": 10000,
            "max_positions": 10,
            "reserve_ratio": 0.1,
            "rebalance_threshold": 0.05,  # 5% 이상 차이 시 리밸런싱
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, default_params)

        self.rebalance_threshold = Decimal(str(self.parameters["rebalance_threshold"]))

    def calculate_allocation(
        self,
        total_balance: Decimal,
        selected_symbols: List[str],
        current_positions: Optional[Dict[str, Position]] = None,
        market_data: Optional[Dict[str, List[OHLCV]]] = None
    ) -> AllocationResult:
        """
        균등 배분 계산

        Args:
            total_balance: 총 사용 가능 자금
            selected_symbols: 선정된 심볼 리스트
            current_positions: 현재 보유 포지션 (미사용)
            market_data: 시장 데이터 (미사용)

        Returns:
            AllocationResult: 배분 결과
        """
        if not selected_symbols:
            logger.warning("선정된 심볼이 없습니다")
            return AllocationResult(
                allocations={},
                weights={},
                metadata={"reason": "선정된 심볼 없음"}
            )

        # 예비 자금 제외
        reserve = total_balance * self.reserve_ratio
        available = total_balance - reserve

        # 균등 배분
        num_symbols = min(len(selected_symbols), self.max_positions)
        amount_per_symbol = available / num_symbols

        # 초기 배분
        allocations = {
            symbol: amount_per_symbol
            for symbol in selected_symbols[:num_symbols]
        }

        # 제약 조건 적용
        allocations = self.apply_constraints(total_balance, allocations)

        # 비중 계산
        weights = self.calculate_weights(allocations)

        logger.info(
            f"균등 배분 완료 | 종목 수: {len(allocations)} | "
            f"종목당 금액: {amount_per_symbol:,.0f} KRW"
        )

        return AllocationResult(
            allocations=allocations,
            weights=weights,
            metadata={
                "strategy": "equal_weight",
                "num_positions": len(allocations),
                "amount_per_symbol": float(amount_per_symbol),
                "total_allocated": float(sum(allocations.values())),
                "reserve": float(reserve)
            }
        )

    def should_rebalance(
        self,
        current_positions: Dict[str, Position],
        target_allocations: Dict[str, Decimal]
    ) -> bool:
        """
        리밸런싱 필요 여부 판단

        균등 배분에서는 각 종목의 비중이 목표(1/N)에서
        threshold 이상 벗어나면 리밸런싱

        Args:
            current_positions: 현재 포지션
            target_allocations: 목표 배분 금액

        Returns:
            bool: 리밸런싱 필요 여부
        """
        if not current_positions or not target_allocations:
            return False

        # 현재 비중 계산
        total_value = self.calculate_position_value(current_positions)
        current_weights = {
            symbol: pos.value / total_value
            for symbol, pos in current_positions.items()
        }

        # 목표 비중 계산
        target_weights = self.calculate_weights(target_allocations)

        # 차이 계산
        divergence = self.calculate_divergence(current_weights, target_weights)

        needs_rebalance = divergence > self.rebalance_threshold

        if needs_rebalance:
            logger.info(
                f"리밸런싱 필요 | 비중 차이: {divergence:.2%} > "
                f"임계값: {self.rebalance_threshold:.2%}"
            )

        return needs_rebalance

    def __repr__(self) -> str:
        return (
            f"<EqualWeightPortfolio(name={self.name}, "
            f"max_positions={self.max_positions}, "
            f"rebalance_threshold={self.rebalance_threshold:.2%})>"
        )


if __name__ == "__main__":
    print("=== 균등 배분 포트폴리오 테스트 ===")

    # 포트폴리오 생성
    portfolio = EqualWeightPortfolio(
        id=1,
        parameters={
            "max_positions": 5,
            "reserve_ratio": 0.1,
            "rebalance_threshold": 0.05,
        }
    )

    portfolio.validate_parameters()

    # 배분 계산
    total_balance = Decimal("10000000")  # 1천만원
    selected_symbols = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-ADA", "KRW-SOL"]

    result = portfolio.calculate_allocation(
        total_balance=total_balance,
        selected_symbols=selected_symbols
    )

    print(f"\n총 자금: {total_balance:,.0f} KRW")
    print(f"선정 종목: {selected_symbols}")
    print(f"\n배분 결과:")

    for symbol, amount in result.allocations.items():
        weight = result.get_weight(symbol)
        print(f"  {symbol}: {amount:,.0f} KRW ({weight:.2%})")

    print(f"\n메타데이터:")
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")

    # 리밸런싱 테스트
    print("\n=== 리밸런싱 테스트 ===")

    # 현재 포지션 (불균형 상태)
    current_positions = {
        "KRW-BTC": Position(
            symbol="KRW-BTC",
            quantity=Decimal("0.05"),
            entry_price=Decimal("50000000"),
            current_price=Decimal("60000000"),  # 20% 상승
            value=Decimal("3000000")
        ),
        "KRW-ETH": Position(
            symbol="KRW-ETH",
            quantity=Decimal("1"),
            entry_price=Decimal("1800000"),
            current_price=Decimal("1800000"),
            value=Decimal("1800000")
        ),
    }

    needs_rebalance = portfolio.should_rebalance(
        current_positions=current_positions,
        target_allocations=result.allocations
    )

    print(f"리밸런싱 필요: {needs_rebalance}")
