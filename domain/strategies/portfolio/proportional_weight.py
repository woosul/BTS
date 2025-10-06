"""
BTS 비율 배분 포트폴리오 전략

종목별 가중치에 따라 차등 배분
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


class ProportionalWeightPortfolio(BasePortfolioStrategy):
    """
    비율 배분 포트폴리오

    종목별로 다른 가중치를 적용하여 배분
    - 순위 기반: 상위 종목에 더 많은 비중
    - 사용자 지정: 수동으로 비중 설정
    """

    def __init__(
        self,
        id: int,
        name: str = "Proportional Weight Portfolio",
        description: str = "비율 배분 포트폴리오",
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "min_allocation": 10000,
            "max_positions": 10,
            "reserve_ratio": 0.1,
            "rebalance_threshold": 0.1,  # 10% 이상 차이 시 리밸런싱
            "weight_mode": "rank",  # rank 또는 custom
            "custom_weights": {},  # {symbol: weight}
            "rank_weights": [0.3, 0.25, 0.2, 0.15, 0.1],  # 1위부터 5위까지 비중
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, default_params)

        self.rebalance_threshold = Decimal(str(self.parameters["rebalance_threshold"]))
        self.weight_mode = self.parameters["weight_mode"]
        self.custom_weights = {
            k: Decimal(str(v))
            for k, v in self.parameters.get("custom_weights", {}).items()
        }
        self.rank_weights = [
            Decimal(str(w))
            for w in self.parameters.get("rank_weights", [])
        ]

    def calculate_allocation(
        self,
        total_balance: Decimal,
        selected_symbols: List[str],
        current_positions: Optional[Dict[str, Position]] = None,
        market_data: Optional[Dict[str, List[OHLCV]]] = None
    ) -> AllocationResult:
        """
        비율 배분 계산

        Args:
            total_balance: 총 사용 가능 자금
            selected_symbols: 선정된 심볼 리스트 (순위순)
            current_positions: 현재 보유 포지션
            market_data: 시장 데이터

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

        # 가중치 계산
        if self.weight_mode == "custom":
            weights = self._calculate_custom_weights(selected_symbols)
        else:  # rank
            weights = self._calculate_rank_weights(selected_symbols)

        # 비중 정규화
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {
                symbol: weight / total_weight
                for symbol, weight in weights.items()
            }
        else:
            # 가중치가 없으면 균등 배분
            weights = {
                symbol: Decimal("1") / len(selected_symbols)
                for symbol in selected_symbols
            }

        # 금액 배분
        allocations = {
            symbol: available * weight
            for symbol, weight in weights.items()
        }

        # 제약 조건 적용
        allocations = self.apply_constraints(total_balance, allocations)

        # 최종 비중 재계산
        final_weights = self.calculate_weights(allocations)

        logger.info(
            f"비율 배분 완료 | 종목 수: {len(allocations)} | "
            f"모드: {self.weight_mode}"
        )

        return AllocationResult(
            allocations=allocations,
            weights=final_weights,
            metadata={
                "strategy": "proportional_weight",
                "weight_mode": self.weight_mode,
                "num_positions": len(allocations),
                "total_allocated": float(sum(allocations.values())),
                "reserve": float(reserve)
            }
        )

    def _calculate_rank_weights(
        self,
        selected_symbols: List[str]
    ) -> Dict[str, Decimal]:
        """
        순위 기반 가중치 계산

        Args:
            selected_symbols: 선정된 심볼 (순위순)

        Returns:
            Dict[str, Decimal]: 가중치
        """
        weights = {}

        for i, symbol in enumerate(selected_symbols):
            if i < len(self.rank_weights):
                weights[symbol] = self.rank_weights[i]
            else:
                # 정의된 순위를 초과하면 마지막 가중치 사용 또는 0
                if self.rank_weights:
                    weights[symbol] = self.rank_weights[-1] / 2
                else:
                    weights[symbol] = Decimal("0")

        return weights

    def _calculate_custom_weights(
        self,
        selected_symbols: List[str]
    ) -> Dict[str, Decimal]:
        """
        사용자 지정 가중치 사용

        Args:
            selected_symbols: 선정된 심볼

        Returns:
            Dict[str, Decimal]: 가중치
        """
        weights = {}

        for symbol in selected_symbols:
            if symbol in self.custom_weights:
                weights[symbol] = self.custom_weights[symbol]
            else:
                # 지정되지 않은 종목은 균등 배분
                weights[symbol] = Decimal("1")

        return weights

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

    def validate_parameters(self) -> bool:
        """파라미터 검증"""
        errors = []

        # 베이스 검증
        try:
            super().validate_parameters()
        except Exception as e:
            errors.append(str(e))

        # 모드 검증
        if self.weight_mode not in ["rank", "custom"]:
            errors.append("weight_mode는 'rank' 또는 'custom'이어야 합니다")

        # 순위 가중치 검증
        if self.weight_mode == "rank":
            if not self.rank_weights:
                errors.append("rank 모드에서는 rank_weights가 필요합니다")

            # 가중치 합계가 1에 가까운지 확인
            if self.rank_weights:
                total = sum(self.rank_weights)
                if abs(total - Decimal("1")) > Decimal("0.1"):
                    logger.warning(f"순위 가중치 합계가 1과 다릅니다: {total}")

        # 사용자 지정 가중치 검증
        if self.weight_mode == "custom":
            if not self.custom_weights:
                errors.append("custom 모드에서는 custom_weights가 필요합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "비율 배분 포트폴리오 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def __repr__(self) -> str:
        return (
            f"<ProportionalWeightPortfolio(name={self.name}, "
            f"mode={self.weight_mode}, max_positions={self.max_positions})>"
        )


if __name__ == "__main__":
    print("=== 비율 배분 포트폴리오 테스트 ===")

    # 순위 기반 포트폴리오
    print("\n[순위 기반 배분]")
    portfolio_rank = ProportionalWeightPortfolio(
        id=1,
        parameters={
            "weight_mode": "rank",
            "rank_weights": [0.30, 0.25, 0.20, 0.15, 0.10],  # 1~5위 비중
            "max_positions": 5,
            "reserve_ratio": 0.1,
        }
    )

    portfolio_rank.validate_parameters()

    total_balance = Decimal("10000000")  # 1천만원
    selected_symbols = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-ADA", "KRW-SOL"]

    result_rank = portfolio_rank.calculate_allocation(
        total_balance=total_balance,
        selected_symbols=selected_symbols
    )

    print(f"\n총 자금: {total_balance:,.0f} KRW")
    print(f"배분 결과 (순위순):")

    for i, symbol in enumerate(selected_symbols):
        amount = result_rank.get_allocation(symbol)
        weight = result_rank.get_weight(symbol)
        print(f"  {i+1}위 {symbol}: {amount:,.0f} KRW ({weight:.2%})")

    # 사용자 지정 포트폴리오
    print("\n[사용자 지정 배분]")
    portfolio_custom = ProportionalWeightPortfolio(
        id=2,
        parameters={
            "weight_mode": "custom",
            "custom_weights": {
                "KRW-BTC": 0.40,
                "KRW-ETH": 0.30,
                "KRW-XRP": 0.20,
                "KRW-ADA": 0.10,
            },
            "max_positions": 5,
            "reserve_ratio": 0.1,
        }
    )

    portfolio_custom.validate_parameters()

    result_custom = portfolio_custom.calculate_allocation(
        total_balance=total_balance,
        selected_symbols=selected_symbols
    )

    print(f"\n배분 결과 (사용자 지정):")

    for symbol in selected_symbols:
        amount = result_custom.get_allocation(symbol)
        weight = result_custom.get_weight(symbol)
        if amount > 0:
            print(f"  {symbol}: {amount:,.0f} KRW ({weight:.2%})")
