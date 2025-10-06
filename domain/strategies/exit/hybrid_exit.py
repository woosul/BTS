"""
BTS 하이브리드 매도 전략

여러 매도 전략의 시그널을 가중 평균하여 최종 결정
"""
from typing import Dict, List, Optional
from decimal import Decimal

from domain.strategies.exit.base_exit import BaseExitStrategy
from domain.strategies.exit.fixed_target_exit import FixedTargetExitStrategy
from domain.strategies.exit.trailing_stop_exit import TrailingStopExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class HybridExitStrategy(BaseExitStrategy):
    """
    하이브리드 매도 전략

    복수의 매도 전략을 조합하여 가중 평균으로 최종 판단
    """

    def __init__(
        self,
        id: int,
        name: str = "Hybrid Exit",
        description: str = "복합 전략 가중 평균 매도",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            # 전략 가중치
            "strategy_weights": {
                "fixed_target": 0.40,
                "trailing_stop": 0.35,
                "rsi": 0.15,
                "time_based": 0.10,
            },
            # Fixed Target 설정
            "target_profit_pct": 15.0,
            "stop_loss_pct": -5.0,
            # Trailing Stop 설정
            "trailing_pct": 3.0,
            "activation_profit": 3.0,
            # RSI 설정
            "rsi_period": 14,
            "rsi_overbought": 75,
            # Time-based 설정
            "max_holding_periods": 72,  # 72시간
            # 최소 확신도
            "sell_threshold": 0.75,  # 이 점수 이상이면 매도
            "min_confidence": 0.75,
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        self.strategy_weights = self.parameters["strategy_weights"]
        self.sell_threshold = Decimal(str(self.parameters["sell_threshold"]))

        # 서브 전략들 초기화
        self.sub_strategies: Dict[str, BaseExitStrategy] = {}
        self._initialize_sub_strategies()

    def _initialize_sub_strategies(self):
        """서브 전략 초기화"""
        # Fixed Target 전략
        if "fixed_target" in self.strategy_weights:
            self.sub_strategies["fixed_target"] = FixedTargetExitStrategy(
                id=self.id * 100 + 1,
                name=f"{self.name}_FixedTarget",
                timeframe=self.timeframe,
                parameters={
                    "target_profit_pct": self.parameters["target_profit_pct"],
                    "stop_loss_pct": self.parameters["stop_loss_pct"],
                    "min_confidence": 0.5,
                }
            )

        # Trailing Stop 전략
        if "trailing_stop" in self.strategy_weights:
            self.sub_strategies["trailing_stop"] = TrailingStopExitStrategy(
                id=self.id * 100 + 2,
                name=f"{self.name}_TrailingStop",
                timeframe=self.timeframe,
                parameters={
                    "trailing_pct": self.parameters["trailing_pct"],
                    "activation_profit": self.parameters["activation_profit"],
                    "stop_loss_pct": self.parameters["stop_loss_pct"],
                    "min_confidence": 0.5,
                }
            )

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        모든 서브 전략의 지표 계산

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Dict: 모든 지표 값
        """
        indicators = {}

        # 각 서브 전략의 지표 계산
        for name, strategy in self.sub_strategies.items():
            try:
                sub_indicators = strategy.calculate_indicators(ohlcv_data)
                indicators[name] = sub_indicators
            except Exception as e:
                logger.warning(f"{name} 전략 지표 계산 실패: {e}")
                indicators[name] = {}

        # 추가 지표: RSI
        if "rsi" in self.strategy_weights:
            from utils.technical_indicators import calculate_rsi
            closes = [float(candle.close) for candle in ohlcv_data]
            rsi_values = calculate_rsi(closes, int(self.parameters["rsi_period"]))
            indicators["rsi"] = {
                "value": Decimal(str(rsi_values[-1])) if rsi_values else Decimal("50"),
                "overbought": Decimal(str(self.parameters["rsi_overbought"]))
            }

        return indicators

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        하이브리드 매도 조건 체크

        각 전략의 시그널을 가중 평균하여 종합 점수 계산

        Args:
            entry_price: 매수 가격
            current_price: 현재 가격
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표
            holding_period: 보유 기간

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        scores = {}
        total_weight = Decimal("0")

        # 1. Fixed Target 점수
        if "fixed_target" in self.sub_strategies and "fixed_target" in self.strategy_weights:
            fixed_score = self._calculate_fixed_target_score(
                entry_price, current_price, indicators.get("fixed_target", {})
            )
            weight = Decimal(str(self.strategy_weights["fixed_target"]))
            scores["fixed_target"] = fixed_score * weight
            total_weight += weight

        # 2. Trailing Stop 점수
        if "trailing_stop" in self.sub_strategies and "trailing_stop" in self.strategy_weights:
            trailing_score = self._calculate_trailing_stop_score(
                entry_price, current_price, indicators.get("trailing_stop", {}), holding_period
            )
            weight = Decimal(str(self.strategy_weights["trailing_stop"]))
            scores["trailing_stop"] = trailing_score * weight
            total_weight += weight

        # 3. RSI 점수
        if "rsi" in indicators and "rsi" in self.strategy_weights:
            rsi_score = self._calculate_rsi_score(indicators["rsi"])
            weight = Decimal(str(self.strategy_weights["rsi"]))
            scores["rsi"] = rsi_score * weight
            total_weight += weight

        # 4. Time-based 점수
        if "time_based" in self.strategy_weights:
            time_score = self._calculate_time_score(holding_period, entry_price, current_price)
            weight = Decimal(str(self.strategy_weights["time_based"]))
            scores["time_based"] = time_score * weight
            total_weight += weight

        # 5. 종합 점수 계산 (가중 평균)
        if total_weight > 0:
            final_score = sum(scores.values()) / total_weight
        else:
            final_score = Decimal("0.5")

        # 6. 매도 조건: 종합 점수가 임계값 이상
        exit_condition = final_score >= self.sell_threshold

        logger.debug(
            f"하이브리드 점수: {final_score:.2%} | "
            f"상세: {', '.join(f'{k}={v:.2%}' for k, v in scores.items())}"
        )

        return exit_condition, final_score, self._generate_reason(scores, final_score)

    def _calculate_fixed_target_score(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        indicators: Dict
    ) -> Decimal:
        """Fixed Target 점수 계산"""
        profit_pct = self.calculate_profit_loss_pct(entry_price, current_price)
        target_pct = Decimal(str(self.parameters["target_profit_pct"]))
        stop_pct = Decimal(str(self.parameters["stop_loss_pct"]))

        # 목표 달성 시 매도 점수 높음
        if profit_pct >= target_pct:
            return Decimal("1.0")

        # 손절 도달 시 매도 점수 높음
        if profit_pct <= stop_pct:
            return Decimal("1.0")

        # 중간 범위: 선형 보간
        if profit_pct > 0:
            return Decimal("0.5") + (profit_pct / target_pct) * Decimal("0.3")
        else:
            return Decimal("0.5") + (profit_pct / stop_pct) * Decimal("0.3")

    def _calculate_trailing_stop_score(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        indicators: Dict,
        holding_period: int
    ) -> Decimal:
        """Trailing Stop 점수 계산"""
        if "trailing_stop" not in self.sub_strategies:
            return Decimal("0.5")

        strategy = self.sub_strategies["trailing_stop"]

        # 현재가를 최고가로 업데이트
        if current_price > strategy.highest_price:
            strategy.highest_price = current_price

        # 트레일링 조건 체크
        profit_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        if profit_pct < strategy.activation_profit:
            return Decimal("0.3")  # 활성화 전

        if strategy.highest_price > 0:
            drawdown = ((current_price - strategy.highest_price) / strategy.highest_price) * 100

            if drawdown <= -strategy.trailing_pct:
                return Decimal("1.0")  # 트레일링 발동

            # 최고가 근처면 보유 점수
            return Decimal("0.4")

        return Decimal("0.5")

    def _calculate_rsi_score(self, rsi_indicators: Dict) -> Decimal:
        """RSI 점수 계산"""
        rsi = rsi_indicators.get("value", Decimal("50"))
        overbought = rsi_indicators.get("overbought", Decimal("75"))

        # 과매수 정도에 따른 점수
        if rsi >= overbought:
            excess = (rsi - overbought) / (Decimal("100") - overbought)
            return Decimal("0.7") + excess * Decimal("0.3")

        return Decimal("0.3")

    def _calculate_time_score(
        self,
        holding_period: int,
        entry_price: Decimal,
        current_price: Decimal
    ) -> Decimal:
        """Time-based 점수 계산"""
        max_periods = int(self.parameters["max_holding_periods"])
        profit_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        if holding_period >= max_periods:
            # 수익이면 매도 점수 높음
            return Decimal("0.9") if profit_pct > 0 else Decimal("0.7")

        # 시간 경과 비율
        time_ratio = Decimal(str(holding_period)) / Decimal(str(max_periods))

        # 보유 기간이 길수록 점수 증가
        return Decimal("0.3") + time_ratio * Decimal("0.4")

    def _generate_reason(self, scores: Dict, final_score: Decimal) -> str:
        """매도 이유 생성"""
        if not scores:
            return "조건 미충족"

        # 가장 높은 점수의 전략 찾기
        max_strategy = max(scores.items(), key=lambda x: x[1])

        reason_map = {
            "fixed_target": "목표가 또는 손절",
            "trailing_stop": "트레일링 스탑",
            "rsi": "RSI 과매수",
            "time_based": "보유 기간"
        }

        main_reason = reason_map.get(max_strategy[0], "복합 조건")

        return f"{main_reason} 주도 (종합 점수: {final_score:.2%})"

    def reset_execution_state(self):
        """실행 상태 초기화"""
        for strategy in self.sub_strategies.values():
            if hasattr(strategy, 'reset_execution_state'):
                strategy.reset_execution_state()
        logger.info(f"하이브리드 매도 상태 초기화: {self.name}")

    def validate_parameters(self) -> bool:
        """파라미터 검증"""
        errors = []

        # 가중치 합계 검증
        total_weight = sum(self.strategy_weights.values())
        if not (0.99 <= total_weight <= 1.01):
            errors.append(f"전략 가중치 합계가 1이 아닙니다: {total_weight}")

        # 임계값 검증
        if not (0 < self.sell_threshold <= 1):
            errors.append(f"sell_threshold는 0-1 범위여야 합니다")

        # 서브 전략 검증
        for strategy in self.sub_strategies.values():
            try:
                strategy.validate_parameters()
            except Exception as e:
                errors.append(f"서브 전략 검증 실패: {e}")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "Hybrid Exit 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """필요한 최소 데이터 개수"""
        min_points = 30
        for strategy in self.sub_strategies.values():
            min_points = max(min_points, strategy.get_minimum_data_points())
        return min_points

    def __repr__(self) -> str:
        weights_str = ", ".join(f"{k}={v:.0%}" for k, v in self.strategy_weights.items())
        return (
            f"<HybridExitStrategy(name={self.name}, "
            f"weights=[{weights_str}], threshold={self.sell_threshold:.0%})>"
        )


if __name__ == "__main__":
    print("=== 하이브리드 매도 전략 테스트 ===")

    from datetime import datetime, timedelta

    # 테스트 데이터 생성
    test_data = []
    base_price = Decimal("50000000")
    entry_price = Decimal("50000000")
    base_time = datetime.now()

    # 상승 후 소폭 하락 패턴
    for i in range(60):
        if i < 30:
            price = base_price + Decimal(str(i * 150000))  # 상승
        else:
            price = base_price + Decimal(str((60 - i) * 50000))  # 소폭 하락

        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=price,
            high=price + Decimal("50000"),
            low=price - Decimal("50000"),
            close=price,
            volume=Decimal("100")
        )
        test_data.append(candle)

    # 전략 생성
    strategy = HybridExitStrategy(
        id=1,
        parameters={
            "strategy_weights": {
                "fixed_target": 0.40,
                "trailing_stop": 0.35,
                "rsi": 0.15,
                "time_based": 0.10,
            },
            "sell_threshold": 0.75,
        }
    )

    strategy.activate()

    # 매도 평가
    signal_data = strategy.evaluate_exit(
        symbol="KRW-BTC",
        entry_price=entry_price,
        ohlcv_data=test_data,
        holding_period=55
    )

    print(f"\n시그널: {signal_data.signal.value.upper()}")
    print(f"확신도: {signal_data.confidence:.2%}")
    print(f"현재가: {signal_data.price:,.0f} KRW")
    print(f"손익률: {signal_data.indicators['profit_loss_pct']:.2f}%")
    print(f"이유: {signal_data.metadata.get('reason', 'N/A')}")

    print(f"\n전략 상세:")
    print(f"  가중치: {strategy.strategy_weights}")
    print(f"  매도 임계값: {strategy.sell_threshold:.0%}")
