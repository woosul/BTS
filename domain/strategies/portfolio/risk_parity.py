"""
BTS 리스크 패리티 포트폴리오 전략

각 자산의 리스크 기여도를 동일하게 배분
"""
from typing import Dict, List, Optional
from decimal import Decimal
import math

from domain.strategies.portfolio.base_portfolio import (
    BasePortfolioStrategy,
    Position,
    AllocationResult
)
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class RiskParityPortfolio(BasePortfolioStrategy):
    """
    리스크 패리티 포트폴리오

    각 자산의 변동성(리스크)에 반비례하여 배분
    변동성이 높은 자산은 적게, 낮은 자산은 많이 투자
    """

    def __init__(
        self,
        id: int,
        name: str = "Risk Parity Portfolio",
        description: str = "리스크 패리티 포트폴리오",
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "min_allocation": 10000,
            "max_positions": 10,
            "reserve_ratio": 0.1,
            "rebalance_threshold": 0.1,
            "volatility_period": 30,  # 변동성 계산 기간
            "default_volatility": 0.03,  # 기본 변동성 (3%)
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, default_params)

        self.rebalance_threshold = Decimal(str(self.parameters["rebalance_threshold"]))
        self.volatility_period = int(self.parameters["volatility_period"])
        self.default_volatility = Decimal(str(self.parameters["default_volatility"]))

    def calculate_allocation(
        self,
        total_balance: Decimal,
        selected_symbols: List[str],
        current_positions: Optional[Dict[str, Position]] = None,
        market_data: Optional[Dict[str, List[OHLCV]]] = None
    ) -> AllocationResult:
        """
        리스크 패리티 배분 계산

        Args:
            total_balance: 총 사용 가능 자금
            selected_symbols: 선정된 심볼 리스트
            current_positions: 현재 보유 포지션
            market_data: 시장 데이터 (변동성 계산용)

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

        # 각 종목의 변동성 계산
        volatilities = {}
        for symbol in selected_symbols:
            if market_data and symbol in market_data:
                vol = self._calculate_volatility(market_data[symbol])
            else:
                vol = self.default_volatility

            volatilities[symbol] = vol

        # 변동성의 역수로 가중치 계산
        inv_volatilities = {
            symbol: Decimal("1") / vol if vol > 0 else Decimal("1")
            for symbol, vol in volatilities.items()
        }

        total_inv_vol = sum(inv_volatilities.values())

        if total_inv_vol == 0:
            logger.warning("유효한 변동성이 없습니다. 균등 배분으로 대체")
            weights = {
                symbol: Decimal("1") / len(selected_symbols)
                for symbol in selected_symbols
            }
        else:
            # 리스크 패리티 가중치
            weights = {
                symbol: inv_vol / total_inv_vol
                for symbol, inv_vol in inv_volatilities.items()
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
            f"리스크 패리티 배분 완료 | 종목 수: {len(allocations)}"
        )

        return AllocationResult(
            allocations=allocations,
            weights=final_weights,
            metadata={
                "strategy": "risk_parity",
                "num_positions": len(allocations),
                "total_allocated": float(sum(allocations.values())),
                "reserve": float(reserve),
                "volatilities": {k: float(v) for k, v in volatilities.items()}
            }
        )

    def _calculate_volatility(self, ohlcv_data: List[OHLCV]) -> Decimal:
        """
        변동성 계산 (표준편차)

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Decimal: 변동성 (일별 수익률의 표준편차)
        """
        if len(ohlcv_data) < 2:
            return self.default_volatility

        # 기간 제한
        data = ohlcv_data[-self.volatility_period:] if len(ohlcv_data) > self.volatility_period else ohlcv_data

        # 일별 수익률 계산
        returns = []
        for i in range(1, len(data)):
            prev_close = data[i - 1].close
            curr_close = data[i].close

            if prev_close > 0:
                ret = (curr_close - prev_close) / prev_close
                returns.append(float(ret))

        if not returns:
            return self.default_volatility

        # 평균
        mean_return = sum(returns) / len(returns)

        # 분산
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)

        # 표준편차
        std_dev = math.sqrt(variance)

        return Decimal(str(std_dev))

    def should_rebalance(
        self,
        current_positions: Dict[str, Position],
        target_allocations: Dict[str, Decimal]
    ) -> bool:
        """리밸런싱 필요 여부 판단"""
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

        try:
            super().validate_parameters()
        except Exception as e:
            errors.append(str(e))

        if self.volatility_period <= 0:
            errors.append("volatility_period는 0보다 커야 합니다")

        if self.default_volatility <= 0:
            errors.append("default_volatility는 0보다 커야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "리스크 패리티 포트폴리오 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def __repr__(self) -> str:
        return (
            f"<RiskParityPortfolio(name={self.name}, "
            f"volatility_period={self.volatility_period})>"
        )


if __name__ == "__main__":
    print("=== 리스크 패리티 포트폴리오 테스트 ===")

    from datetime import datetime, timedelta
    import random

    # 테스트 데이터 생성 (서로 다른 변동성)
    def generate_ohlcv(base_price: Decimal, volatility: float, days: int) -> List[OHLCV]:
        data = []
        price = base_price
        base_time = datetime.now()

        for i in range(days):
            # 변동성에 따른 가격 변화
            change = random.gauss(0, volatility)
            price = price * (1 + Decimal(str(change)))

            candle = OHLCV(
                timestamp=base_time + timedelta(days=i),
                open=price,
                high=price * Decimal("1.01"),
                low=price * Decimal("0.99"),
                close=price,
                volume=Decimal("100")
            )
            data.append(candle)

        return data

    # 시장 데이터 생성 (변동성 차이)
    market_data = {
        "KRW-BTC": generate_ohlcv(Decimal("50000000"), 0.05, 60),   # 높은 변동성
        "KRW-ETH": generate_ohlcv(Decimal("3000000"), 0.04, 60),    # 중간 변동성
        "KRW-USDT": generate_ohlcv(Decimal("1300"), 0.01, 60),      # 낮은 변동성 (스테이블코인)
    }

    # 포트폴리오 생성
    portfolio = RiskParityPortfolio(
        id=1,
        parameters={
            "volatility_period": 30,
            "max_positions": 5,
            "reserve_ratio": 0.1,
        }
    )

    portfolio.validate_parameters()

    # 배분 계산
    total_balance = Decimal("10000000")  # 1천만원
    selected_symbols = list(market_data.keys())

    result = portfolio.calculate_allocation(
        total_balance=total_balance,
        selected_symbols=selected_symbols,
        market_data=market_data
    )

    print(f"\n총 자금: {total_balance:,.0f} KRW")
    print(f"\n배분 결과 (변동성 역순):")

    volatilities = result.metadata.get("volatilities", {})

    for symbol in sorted(selected_symbols, key=lambda s: volatilities.get(s, 0), reverse=True):
        amount = result.get_allocation(symbol)
        weight = result.get_weight(symbol)
        vol = volatilities.get(symbol, 0)

        print(f"\n{symbol}:")
        print(f"  변동성: {vol:.4f} ({vol * 100:.2f}%)")
        print(f"  배분: {amount:,.0f} KRW ({weight:.2%})")

    print(f"\n✓ 변동성이 높은 BTC는 적게, 낮은 USDT는 많이 배분됩니다")
