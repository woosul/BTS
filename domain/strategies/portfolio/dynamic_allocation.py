"""
BTS 동적 배분 포트폴리오 전략

시장 상황에 따라 동적으로 비중 조정
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


class DynamicAllocationPortfolio(BasePortfolioStrategy):
    """
    동적 배분 포트폴리오

    시장 상황(변동성, 추세)에 따라 공격적/보수적 비중 조절
    - 변동성 높음 → 현금 비중 확대
    - 하락 추세 → 리스크 축소
    - 상승 추세 → 리스크 확대
    """

    def __init__(
        self,
        id: int,
        name: str = "Dynamic Allocation Portfolio",
        description: str = "동적 배분 포트폴리오",
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "min_allocation": 10000,
            "max_positions": 10,
            "base_reserve_ratio": 0.1,  # 기본 현금 비율
            "min_reserve_ratio": 0.05,   # 최소 현금 비율
            "max_reserve_ratio": 0.5,    # 최대 현금 비율
            "rebalance_threshold": 0.12,
            # 변동성 기준
            "volatility_period": 30,
            "low_volatility": 0.02,      # 낮은 변동성 기준
            "high_volatility": 0.05,     # 높은 변동성 기준
            # 추세 기준
            "trend_period": 20,
            "trend_threshold": 0.02,     # 추세 판단 기준 (2%)
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, default_params)

        self.rebalance_threshold = Decimal(str(self.parameters["rebalance_threshold"]))
        self.base_reserve_ratio = Decimal(str(self.parameters["base_reserve_ratio"]))
        self.min_reserve_ratio = Decimal(str(self.parameters["min_reserve_ratio"]))
        self.max_reserve_ratio = Decimal(str(self.parameters["max_reserve_ratio"]))

        self.volatility_period = int(self.parameters["volatility_period"])
        self.low_volatility = Decimal(str(self.parameters["low_volatility"]))
        self.high_volatility = Decimal(str(self.parameters["high_volatility"]))

        self.trend_period = int(self.parameters["trend_period"])
        self.trend_threshold = Decimal(str(self.parameters["trend_threshold"]))

    def calculate_allocation(
        self,
        total_balance: Decimal,
        selected_symbols: List[str],
        current_positions: Optional[Dict[str, Position]] = None,
        market_data: Optional[Dict[str, List[OHLCV]]] = None
    ) -> AllocationResult:
        """
        동적 배분 계산

        Args:
            total_balance: 총 사용 가능 자금
            selected_symbols: 선정된 심볼 리스트
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

        # 1. 시장 상황 분석
        market_condition = self._analyze_market_condition(market_data or {})

        # 2. 동적 예비금 비율 결정
        dynamic_reserve_ratio = self._calculate_dynamic_reserve(market_condition)

        # 3. 사용 가능 자금
        reserve = total_balance * dynamic_reserve_ratio
        available = total_balance - reserve

        # 4. 시장 상황에 따른 배분 전략
        if market_condition["overall_risk"] == "high":
            # 고위험: 보수적 배분 (상위 종목에 집중)
            allocations = self._conservative_allocation(available, selected_symbols[:5])
        elif market_condition["overall_risk"] == "low":
            # 저위험: 공격적 배분 (분산 투자)
            allocations = self._aggressive_allocation(available, selected_symbols)
        else:
            # 중위험: 균형 배분
            allocations = self._balanced_allocation(available, selected_symbols)

        # 5. 제약 조건 적용
        allocations = self.apply_constraints(total_balance, allocations)

        # 6. 비중 계산
        weights = self.calculate_weights(allocations)

        logger.info(
            f"동적 배분 완료 | 리스크: {market_condition['overall_risk']} | "
            f"현금비율: {dynamic_reserve_ratio:.2%} | "
            f"종목 수: {len(allocations)}"
        )

        return AllocationResult(
            allocations=allocations,
            weights=weights,
            metadata={
                "strategy": "dynamic_allocation",
                "num_positions": len(allocations),
                "total_allocated": float(sum(allocations.values())),
                "reserve": float(reserve),
                "reserve_ratio": float(dynamic_reserve_ratio),
                "market_condition": market_condition
            }
        )

    def _analyze_market_condition(self, market_data: Dict[str, List[OHLCV]]) -> Dict:
        """
        시장 상황 분석

        Args:
            market_data: 심볼별 OHLCV 데이터

        Returns:
            Dict: 시장 상황 정보
        """
        if not market_data:
            return {
                "avg_volatility": float(self.low_volatility),
                "avg_trend": 0.0,
                "overall_risk": "medium"
            }

        volatilities = []
        trends = []

        for symbol, ohlcv_data in market_data.items():
            if len(ohlcv_data) >= self.volatility_period:
                # 변동성 계산
                vol = self._calculate_volatility(ohlcv_data)
                volatilities.append(float(vol))

                # 추세 계산
                trend = self._calculate_trend(ohlcv_data)
                trends.append(float(trend))

        avg_volatility = sum(volatilities) / len(volatilities) if volatilities else float(self.low_volatility)
        avg_trend = sum(trends) / len(trends) if trends else 0.0

        # 전체 리스크 판단
        if avg_volatility > float(self.high_volatility) or avg_trend < -float(self.trend_threshold):
            overall_risk = "high"
        elif avg_volatility < float(self.low_volatility) and avg_trend > float(self.trend_threshold):
            overall_risk = "low"
        else:
            overall_risk = "medium"

        return {
            "avg_volatility": avg_volatility,
            "avg_trend": avg_trend,
            "overall_risk": overall_risk
        }

    def _calculate_volatility(self, ohlcv_data: List[OHLCV]) -> Decimal:
        """변동성 계산"""
        import math

        data = ohlcv_data[-self.volatility_period:]
        returns = []

        for i in range(1, len(data)):
            if data[i - 1].close > 0:
                ret = (data[i].close - data[i - 1].close) / data[i - 1].close
                returns.append(float(ret))

        if not returns:
            return self.low_volatility

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return Decimal(str(math.sqrt(variance)))

    def _calculate_trend(self, ohlcv_data: List[OHLCV]) -> Decimal:
        """추세 계산 (단순 이동평균 기준)"""
        if len(ohlcv_data) < self.trend_period:
            return Decimal("0")

        data = ohlcv_data[-self.trend_period:]

        # 현재가와 N일 전 가격 비교
        start_price = data[0].close
        end_price = data[-1].close

        if start_price == 0:
            return Decimal("0")

        return ((end_price - start_price) / start_price)

    def _calculate_dynamic_reserve(self, market_condition: Dict) -> Decimal:
        """동적 예비금 비율 계산"""
        base = self.base_reserve_ratio

        # 변동성에 따른 조정
        volatility = Decimal(str(market_condition["avg_volatility"]))
        if volatility > self.high_volatility:
            base += Decimal("0.2")  # 고변동성: 현금 증가
        elif volatility < self.low_volatility:
            base -= Decimal("0.05")  # 저변동성: 현금 감소

        # 추세에 따른 조정
        trend = Decimal(str(market_condition["avg_trend"]))
        if trend < -self.trend_threshold:
            base += Decimal("0.15")  # 하락 추세: 현금 증가
        elif trend > self.trend_threshold:
            base -= Decimal("0.05")  # 상승 추세: 현금 감소

        # 범위 제한
        return max(self.min_reserve_ratio, min(self.max_reserve_ratio, base))

    def _conservative_allocation(
        self,
        available: Decimal,
        symbols: List[str]
    ) -> Dict[str, Decimal]:
        """보수적 배분 (상위 종목 집중)"""
        allocations = {}
        weights = [0.40, 0.30, 0.20, 0.07, 0.03]  # 상위 집중

        for i, symbol in enumerate(symbols):
            if i < len(weights):
                allocations[symbol] = available * Decimal(str(weights[i]))

        return allocations

    def _aggressive_allocation(
        self,
        available: Decimal,
        symbols: List[str]
    ) -> Dict[str, Decimal]:
        """공격적 배분 (균등 분산)"""
        num_symbols = min(len(symbols), self.max_positions)
        amount_per_symbol = available / num_symbols

        return {symbol: amount_per_symbol for symbol in symbols[:num_symbols]}

    def _balanced_allocation(
        self,
        available: Decimal,
        symbols: List[str]
    ) -> Dict[str, Decimal]:
        """균형 배분 (순위 기반 차등)"""
        allocations = {}
        weights = [0.25, 0.20, 0.18, 0.15, 0.12, 0.10]  # 순위 기반

        for i, symbol in enumerate(symbols):
            if i < len(weights):
                allocations[symbol] = available * Decimal(str(weights[i]))
            elif i < self.max_positions:
                # 나머지는 소량 배분
                allocations[symbol] = available * Decimal("0.02")

        return allocations

    def should_rebalance(
        self,
        current_positions: Dict[str, Position],
        target_allocations: Dict[str, Decimal]
    ) -> bool:
        """리밸런싱 필요 여부 판단"""
        if not current_positions or not target_allocations:
            return False

        total_value = self.calculate_position_value(current_positions)
        current_weights = {
            symbol: pos.value / total_value
            for symbol, pos in current_positions.items()
        }

        target_weights = self.calculate_weights(target_allocations)
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
            f"<DynamicAllocationPortfolio(name={self.name}, "
            f"base_reserve={self.base_reserve_ratio:.2%})>"
        )


if __name__ == "__main__":
    print("=== 동적 배분 포트폴리오 테스트 ===")

    from datetime import datetime, timedelta
    import random

    # 다양한 시장 상황 생성
    def generate_market_scenario(volatility: float, trend: float, days: int) -> List[OHLCV]:
        data = []
        price = Decimal("50000000")
        base_time = datetime.now()

        for i in range(days):
            # 추세 + 변동성
            trend_change = trend / days
            random_change = random.gauss(0, volatility)
            price = price * (1 + Decimal(str(trend_change + random_change)))

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

    # 시나리오 1: 고변동성 + 하락 추세
    print("\n[시나리오 1: 고변동성 + 하락 추세]")
    market_data_high_risk = {
        "KRW-BTC": generate_market_scenario(0.06, -0.10, 60),
        "KRW-ETH": generate_market_scenario(0.05, -0.08, 60),
    }

    portfolio = DynamicAllocationPortfolio(id=1)
    portfolio.validate_parameters()

    result1 = portfolio.calculate_allocation(
        total_balance=Decimal("10000000"),
        selected_symbols=["KRW-BTC", "KRW-ETH", "KRW-XRP"],
        market_data=market_data_high_risk
    )

    print(f"시장 상황: {result1.metadata['market_condition']}")
    print(f"현금 비율: {result1.metadata['reserve_ratio']:.2%}")
    print(f"투자 금액: {result1.metadata['total_allocated']:,.0f} KRW")

    # 시나리오 2: 저변동성 + 상승 추세
    print("\n[시나리오 2: 저변동성 + 상승 추세]")
    market_data_low_risk = {
        "KRW-BTC": generate_market_scenario(0.015, 0.15, 60),
        "KRW-ETH": generate_market_scenario(0.012, 0.12, 60),
    }

    result2 = portfolio.calculate_allocation(
        total_balance=Decimal("10000000"),
        selected_symbols=["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-ADA", "KRW-SOL"],
        market_data=market_data_low_risk
    )

    print(f"시장 상황: {result2.metadata['market_condition']}")
    print(f"현금 비율: {result2.metadata['reserve_ratio']:.2%}")
    print(f"투자 금액: {result2.metadata['total_allocated']:,.0f} KRW")
    print(f"종목 수: {result2.metadata['num_positions']}")
