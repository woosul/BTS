"""
BTS 하이브리드 매수 전략

여러 전략의 시그널을 가중 평균하여 최종 매수 결정
- 각 전략별 가중치 설정
- 스코어링 기반 종합 판단
"""
from typing import Dict, List, Optional, Type
from decimal import Decimal
from datetime import datetime

from domain.strategies.entry.base_entry import BaseEntryStrategy
from domain.strategies.entry.macd_entry import MACDEntryStrategy
from domain.strategies.entry.stochastic_entry import StochasticEntryStrategy
from core.enums import StrategySignal, TimeFrame
from core.models import OHLCV, StrategySignalData
from core.exceptions import StrategyError
from utils.logger import get_logger

logger = get_logger(__name__)


class HybridEntryStrategy(BaseEntryStrategy):
    """
    하이브리드 매수 전략

    복수의 매수 전략을 조합하여 가중 평균으로 최종 판단
    """

    def __init__(
        self,
        id: int,
        name: str = "Hybrid Entry",
        description: str = "복합 전략 가중 평균 매수",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            # 전략 가중치
            "strategy_weights": {
                "macd": 0.35,
                "stochastic": 0.30,
                "rsi": 0.20,
                "volume": 0.15,
            },
            # MACD 설정
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            # Stochastic 설정
            "stoch_k": 14,
            "stoch_d": 3,
            "stoch_smooth": 3,
            "stoch_oversold": 20,
            # RSI 설정
            "rsi_period": 14,
            "rsi_oversold": 30,
            # 거래량 설정
            "volume_threshold": 1.5,
            # 최소 확신도
            "min_confidence": 0.7,
            "buy_threshold": 0.65,  # 이 점수 이상이면 매수
            "volume_check": False,
            "trend_check": True,
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        self.strategy_weights = self.parameters["strategy_weights"]
        self.buy_threshold = Decimal(str(self.parameters["buy_threshold"]))

        # 서브 전략들 초기화
        self.sub_strategies: Dict[str, BaseEntryStrategy] = {}
        self._initialize_sub_strategies()

    def _initialize_sub_strategies(self):
        """서브 전략 초기화"""
        # MACD 전략
        if "macd" in self.strategy_weights:
            self.sub_strategies["macd"] = MACDEntryStrategy(
                id=self.id * 100 + 1,
                name=f"{self.name}_MACD",
                timeframe=self.timeframe,
                parameters={
                    "fast_period": self.parameters["macd_fast"],
                    "slow_period": self.parameters["macd_slow"],
                    "signal_period": self.parameters["macd_signal"],
                    "min_confidence": 0.5,  # 하이브리드에서 재계산
                }
            )

        # Stochastic 전략
        if "stochastic" in self.strategy_weights:
            self.sub_strategies["stochastic"] = StochasticEntryStrategy(
                id=self.id * 100 + 2,
                name=f"{self.name}_Stochastic",
                timeframe=self.timeframe,
                parameters={
                    "k_period": self.parameters["stoch_k"],
                    "d_period": self.parameters["stoch_d"],
                    "smooth": self.parameters["stoch_smooth"],
                    "oversold": self.parameters["stoch_oversold"],
                    "min_confidence": 0.5,
                }
            )

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        모든 서브 전략의 지표 계산

        Args:
            ohlcv_data: OHLCV 데이터 리스트

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
                "oversold": Decimal(str(self.parameters["rsi_oversold"]))
            }

        # 거래량 비율
        if "volume" in self.strategy_weights:
            recent_volume = ohlcv_data[-1].volume
            avg_volume = sum(candle.volume for candle in ohlcv_data[-20:]) / 20
            indicators["volume"] = {
                "ratio": recent_volume / avg_volume if avg_volume > 0 else Decimal("1"),
                "threshold": Decimal(str(self.parameters["volume_threshold"]))
            }

        return indicators

    def check_entry_condition(
        self,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> tuple[bool, Decimal]:
        """
        하이브리드 매수 조건 체크

        각 전략의 시그널을 가중 평균하여 종합 점수 계산

        Args:
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표들

        Returns:
            tuple: (매수 조건 만족 여부, 확신도)
        """
        scores = {}
        total_weight = Decimal("0")

        # 1. MACD 점수
        if "macd" in indicators and "macd" in self.strategy_weights:
            macd_score = self._calculate_macd_score(indicators["macd"])
            weight = Decimal(str(self.strategy_weights["macd"]))
            scores["macd"] = macd_score * weight
            total_weight += weight

        # 2. Stochastic 점수
        if "stochastic" in indicators and "stochastic" in self.strategy_weights:
            stoch_score = self._calculate_stochastic_score(indicators["stochastic"])
            weight = Decimal(str(self.strategy_weights["stochastic"]))
            scores["stochastic"] = stoch_score * weight
            total_weight += weight

        # 3. RSI 점수
        if "rsi" in indicators and "rsi" in self.strategy_weights:
            rsi_score = self._calculate_rsi_score(indicators["rsi"])
            weight = Decimal(str(self.strategy_weights["rsi"]))
            scores["rsi"] = rsi_score * weight
            total_weight += weight

        # 4. 거래량 점수
        if "volume" in indicators and "volume" in self.strategy_weights:
            volume_score = self._calculate_volume_score(indicators["volume"])
            weight = Decimal(str(self.strategy_weights["volume"]))
            scores["volume"] = volume_score * weight
            total_weight += weight

        # 5. 종합 점수 계산 (가중 평균)
        if total_weight > 0:
            final_score = sum(scores.values()) / total_weight
        else:
            final_score = Decimal("0.5")

        # 6. 매수 조건: 종합 점수가 임계값 이상
        entry_condition = final_score >= self.buy_threshold

        logger.debug(
            f"하이브리드 점수: {final_score:.2%} | "
            f"상세: {', '.join(f'{k}={v:.2%}' for k, v in scores.items())}"
        )

        return entry_condition, final_score

    def _calculate_macd_score(self, macd_indicators: Dict) -> Decimal:
        """MACD 점수 계산 (0-1)"""
        if not macd_indicators:
            return Decimal("0.5")

        macd = macd_indicators.get("macd", Decimal("0"))
        signal = macd_indicators.get("signal", Decimal("0"))
        histogram = macd_indicators.get("histogram", Decimal("0"))
        prev_macd = macd_indicators.get("prev_macd", macd)
        prev_signal = macd_indicators.get("prev_signal", signal)

        score = Decimal("0.5")

        # 골든 크로스
        if prev_macd <= prev_signal and macd > signal:
            score += Decimal("0.3")

        # 히스토그램 양수
        if histogram > 0:
            score += Decimal("0.2")

        return min(score, Decimal("1"))

    def _calculate_stochastic_score(self, stoch_indicators: Dict) -> Decimal:
        """Stochastic 점수 계산 (0-1)"""
        if not stoch_indicators:
            return Decimal("0.5")

        k = stoch_indicators.get("k", Decimal("50"))
        d = stoch_indicators.get("d", Decimal("50"))
        prev_k = stoch_indicators.get("prev_k", k)
        prev_d = stoch_indicators.get("prev_d", d)

        score = Decimal("0.5")

        # 골든 크로스
        if prev_k <= prev_d and k > d:
            score += Decimal("0.25")

        # 과매도 구간 (20 미만)
        if k < 20:
            score += (Decimal("20") - k) / Decimal("20") * Decimal("0.25")

        return min(score, Decimal("1"))

    def _calculate_rsi_score(self, rsi_indicators: Dict) -> Decimal:
        """RSI 점수 계산 (0-1)"""
        if not rsi_indicators:
            return Decimal("0.5")

        rsi = rsi_indicators.get("value", Decimal("50"))
        oversold = rsi_indicators.get("oversold", Decimal("30"))

        score = Decimal("0.5")

        # 과매도 정도에 따른 점수
        if rsi < oversold:
            score += (oversold - rsi) / oversold * Decimal("0.5")

        return min(score, Decimal("1"))

    def _calculate_volume_score(self, volume_indicators: Dict) -> Decimal:
        """거래량 점수 계산 (0-1)"""
        if not volume_indicators:
            return Decimal("0.5")

        ratio = volume_indicators.get("ratio", Decimal("1"))
        threshold = volume_indicators.get("threshold", Decimal("1.5"))

        score = Decimal("0.5")

        # 거래량 배수에 따른 점수
        if ratio >= threshold:
            score += min((ratio - threshold) / threshold, Decimal("0.5"))

        return min(score, Decimal("1"))

    def validate_parameters(self) -> bool:
        """
        하이브리드 파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            StrategyError: 파라미터가 유효하지 않은 경우
        """
        errors = []

        # 가중치 합계 검증
        total_weight = sum(self.strategy_weights.values())
        if not (0.99 <= total_weight <= 1.01):  # 부동소수점 오차 허용
            errors.append(f"전략 가중치 합계가 1이 아닙니다: {total_weight}")

        # 각 가중치 검증
        for name, weight in self.strategy_weights.items():
            if not (0 <= weight <= 1):
                errors.append(f"{name} 가중치가 0-1 범위를 벗어남: {weight}")

        # 임계값 검증
        if not (0 < self.buy_threshold < 1):
            errors.append(f"buy_threshold는 0-1 범위여야 합니다: {self.buy_threshold}")

        # 서브 전략 검증
        for strategy in self.sub_strategies.values():
            try:
                strategy.validate_parameters()
            except StrategyError as e:
                errors.append(f"서브 전략 검증 실패: {e}")

        if errors:
            raise StrategyError(
                "하이브리드 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """
        필요한 최소 데이터 개수

        Returns:
            int: 모든 서브 전략 중 최대값
        """
        min_points = 30
        for strategy in self.sub_strategies.values():
            min_points = max(min_points, strategy.get_minimum_data_points())
        return min_points

    def get_strategy_details(self) -> Dict:
        """
        전략 상세 정보 조회

        Returns:
            Dict: 전략 가중치 및 설정
        """
        return {
            "weights": self.strategy_weights,
            "buy_threshold": float(self.buy_threshold),
            "sub_strategies": [s.name for s in self.sub_strategies.values()],
        }

    def __repr__(self) -> str:
        weights_str = ", ".join(f"{k}={v:.0%}" for k, v in self.strategy_weights.items())
        return (
            f"<HybridEntryStrategy(name={self.name}, "
            f"weights=[{weights_str}], threshold={self.buy_threshold:.0%})>"
        )


if __name__ == "__main__":
    print("=== 하이브리드 매수 전략 테스트 ===")

    # 테스트 데이터 생성
    from datetime import timedelta

    test_data = []
    base_price = Decimal("50000000")
    base_time = datetime.now()

    for i in range(100):
        # 하락 후 반등 패턴
        if i < 60:
            price = base_price - Decimal(str(i * 30000))
        else:
            price = base_price - Decimal(str((120 - i) * 30000))

        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=price - Decimal("50000"),
            high=price + Decimal("100000"),
            low=price - Decimal("100000"),
            close=price,
            volume=Decimal("100") * (Decimal("2") if i > 60 else Decimal("1"))
        )
        test_data.append(candle)

    # 하이브리드 전략 생성
    strategy = HybridEntryStrategy(
        id=1,
        parameters={
            "strategy_weights": {
                "macd": 0.35,
                "stochastic": 0.30,
                "rsi": 0.20,
                "volume": 0.15,
            },
            "buy_threshold": 0.65,
            "min_confidence": 0.7,
        }
    )

    # 전략 활성화
    strategy.activate()

    # 시그널 생성
    signal_data = strategy.analyze("KRW-BTC", test_data)

    print(f"\n시그널: {signal_data.signal.value.upper()}")
    print(f"확신도: {signal_data.confidence:.2%}")
    print(f"가격: {signal_data.price:,.0f} KRW")

    print(f"\n전략 상세:")
    details = strategy.get_strategy_details()
    print(f"  가중치: {details['weights']}")
    print(f"  매수 임계값: {details['buy_threshold']:.0%}")
    print(f"  서브 전략: {', '.join(details['sub_strategies'])}")
