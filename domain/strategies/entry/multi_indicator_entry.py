"""
BTS 멀티 지표 매수 전략

여러 기술 지표를 조합하여 매수 시그널 생성
- RSI, MACD, 볼린저 밴드, 거래량 등 복합 활용
- AND/OR 조합 모드 지원
"""
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from domain.strategies.entry.base_entry import BaseEntryStrategy
from core.enums import StrategySignal, TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_rsi, calculate_ema, calculate_sma

logger = get_logger(__name__)


class MultiIndicatorEntryStrategy(BaseEntryStrategy):
    """
    멀티 지표 매수 전략

    복수의 기술 지표를 조합하여 매수 시그널 생성
    - RSI 과매도
    - MACD 골든 크로스
    - 볼린저 밴드 하단 터치
    - 거래량 증가
    """

    def __init__(
        self,
        id: int,
        name: str = "Multi-Indicator Entry",
        description: str = "복합 지표 기반 매수 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            # RSI 설정
            "use_rsi": True,
            "rsi_period": 14,
            "rsi_oversold": 30,
            # MACD 설정
            "use_macd": True,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            # 볼린저 밴드 설정
            "use_bollinger": True,
            "bb_period": 20,
            "bb_std": 2.0,
            # 거래량 설정
            "use_volume": True,
            "volume_threshold": 1.5,  # 평균 대비 1.5배
            # 조합 모드
            "combination_mode": "AND",  # AND 또는 OR
            "min_indicators": 2,  # OR 모드일 때 최소 충족 지표 수
            # 기타
            "min_confidence": 0.7,
            "volume_check": False,  # 이미 지표에 포함
            "trend_check": True,
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        # 지표 사용 여부
        self.use_rsi = self.parameters["use_rsi"]
        self.use_macd = self.parameters["use_macd"]
        self.use_bollinger = self.parameters["use_bollinger"]
        self.use_volume = self.parameters["use_volume"]

        # 조합 모드
        self.combination_mode = self.parameters["combination_mode"]
        self.min_indicators = int(self.parameters["min_indicators"])

        # RSI 파라미터
        self.rsi_period = int(self.parameters["rsi_period"])
        self.rsi_oversold = Decimal(str(self.parameters["rsi_oversold"]))

        # MACD 파라미터
        self.macd_fast = int(self.parameters["macd_fast"])
        self.macd_slow = int(self.parameters["macd_slow"])
        self.macd_signal = int(self.parameters["macd_signal"])

        # 볼린저 밴드 파라미터
        self.bb_period = int(self.parameters["bb_period"])
        self.bb_std = float(self.parameters["bb_std"])

        # 거래량 파라미터
        self.volume_threshold = Decimal(str(self.parameters["volume_threshold"]))

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        복합 지표 계산

        Args:
            ohlcv_data: OHLCV 데이터 리스트

        Returns:
            Dict: 모든 지표 값

        Raises:
            IndicatorCalculationError: 지표 계산 실패 시
        """
        try:
            indicators = {}
            closes = [float(candle.close) for candle in ohlcv_data]

            # 1. RSI 계산
            if self.use_rsi:
                rsi_values = calculate_rsi(closes, self.rsi_period)
                indicators["rsi"] = Decimal(str(rsi_values[-1])) if rsi_values else Decimal("50")

            # 2. MACD 계산
            if self.use_macd:
                fast_ema = calculate_ema(closes, self.macd_fast)
                slow_ema = calculate_ema(closes, self.macd_slow)
                macd_line = [fast - slow for fast, slow in zip(fast_ema, slow_ema)]
                signal_line = calculate_ema(macd_line, self.macd_signal)

                indicators["macd"] = Decimal(str(macd_line[-1]))
                indicators["macd_signal"] = Decimal(str(signal_line[-1]))
                indicators["macd_histogram"] = indicators["macd"] - indicators["macd_signal"]
                indicators["prev_macd"] = Decimal(str(macd_line[-2])) if len(macd_line) > 1 else indicators["macd"]
                indicators["prev_macd_signal"] = Decimal(str(signal_line[-2])) if len(signal_line) > 1 else indicators["macd_signal"]

            # 3. 볼린저 밴드 계산
            if self.use_bollinger:
                sma = calculate_sma(closes, self.bb_period)
                current_sma = Decimal(str(sma[-1]))

                # 표준편차 계산
                std_dev = Decimal(str((
                    sum((Decimal(str(c)) - current_sma) ** 2 for c in closes[-self.bb_period:]) / self.bb_period
                ) ** Decimal("0.5")))

                indicators["bb_upper"] = current_sma + (std_dev * Decimal(str(self.bb_std)))
                indicators["bb_middle"] = current_sma
                indicators["bb_lower"] = current_sma - (std_dev * Decimal(str(self.bb_std)))

            # 4. 거래량 분석
            if self.use_volume:
                recent_volume = ohlcv_data[-1].volume
                avg_volume = sum(candle.volume for candle in ohlcv_data[-20:]) / 20
                indicators["volume_ratio"] = recent_volume / avg_volume if avg_volume > 0 else Decimal("1")

            # 현재 가격
            indicators["current_price"] = ohlcv_data[-1].close

            return indicators

        except Exception as e:
            logger.error(f"멀티 지표 계산 실패: {e}")
            raise IndicatorCalculationError(f"멀티 지표 계산 실패: {str(e)}")

    def check_entry_condition(
        self,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> tuple[bool, Decimal]:
        """
        복합 지표 매수 조건 체크

        Args:
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표들

        Returns:
            tuple: (매수 조건 만족 여부, 확신도)
        """
        signals = []
        confidences = []

        # 1. RSI 체크
        if self.use_rsi and "rsi" in indicators:
            rsi_signal, rsi_conf = self._check_rsi_signal(indicators)
            signals.append(rsi_signal)
            confidences.append(rsi_conf)

        # 2. MACD 체크
        if self.use_macd and "macd" in indicators:
            macd_signal, macd_conf = self._check_macd_signal(indicators)
            signals.append(macd_signal)
            confidences.append(macd_conf)

        # 3. 볼린저 밴드 체크
        if self.use_bollinger and "bb_lower" in indicators:
            bb_signal, bb_conf = self._check_bollinger_signal(indicators)
            signals.append(bb_signal)
            confidences.append(bb_conf)

        # 4. 거래량 체크
        if self.use_volume and "volume_ratio" in indicators:
            vol_signal, vol_conf = self._check_volume_signal(indicators)
            signals.append(vol_signal)
            confidences.append(vol_conf)

        # 조합 모드에 따라 판단
        if self.combination_mode == "AND":
            # 모든 지표가 매수 신호를 줘야 함
            entry_condition = all(signals)
            confidence = sum(confidences) / len(confidences) if confidences else Decimal("0.5")
        else:  # OR 모드
            # 최소 N개 이상의 지표가 매수 신호를 줘야 함
            true_count = sum(signals)
            entry_condition = true_count >= self.min_indicators
            # 확신도는 신호를 준 지표들의 평균
            active_confidences = [c for s, c in zip(signals, confidences) if s]
            confidence = sum(active_confidences) / len(active_confidences) if active_confidences else Decimal("0.5")

        return entry_condition, confidence

    def _check_rsi_signal(self, indicators: Dict) -> tuple[bool, Decimal]:
        """RSI 매수 신호 체크"""
        rsi = indicators["rsi"]
        signal = rsi < self.rsi_oversold
        # 과매도 정도에 따른 확신도
        if signal:
            conf = Decimal("0.7") + ((self.rsi_oversold - rsi) / self.rsi_oversold) * Decimal("0.3")
        else:
            conf = Decimal("0.3")
        return signal, conf

    def _check_macd_signal(self, indicators: Dict) -> tuple[bool, Decimal]:
        """MACD 매수 신호 체크 (골든 크로스)"""
        macd = indicators["macd"]
        macd_signal = indicators["macd_signal"]
        prev_macd = indicators["prev_macd"]
        prev_signal = indicators["prev_macd_signal"]

        golden_cross = (prev_macd <= prev_signal) and (macd > macd_signal)
        histogram_positive = indicators["macd_histogram"] > 0

        signal = golden_cross or histogram_positive
        conf = Decimal("0.75") if golden_cross else (Decimal("0.65") if histogram_positive else Decimal("0.4"))

        return signal, conf

    def _check_bollinger_signal(self, indicators: Dict) -> tuple[bool, Decimal]:
        """볼린저 밴드 매수 신호 체크 (하단 터치)"""
        current_price = indicators["current_price"]
        bb_lower = indicators["bb_lower"]
        bb_middle = indicators["bb_middle"]

        # 하단 밴드 터치 또는 근접
        distance_to_lower = (current_price - bb_lower) / (bb_middle - bb_lower) if bb_middle != bb_lower else Decimal("1")

        signal = distance_to_lower < Decimal("0.2")  # 하단 20% 이내
        conf = Decimal("0.7") + (Decimal("0.2") - distance_to_lower) if signal else Decimal("0.4")

        return signal, conf

    def _check_volume_signal(self, indicators: Dict) -> tuple[bool, Decimal]:
        """거래량 매수 신호 체크"""
        volume_ratio = indicators["volume_ratio"]
        signal = volume_ratio >= self.volume_threshold
        # 거래량 배수에 따른 확신도
        conf = min(Decimal("0.5") + volume_ratio * Decimal("0.2"), Decimal("0.9")) if signal else Decimal("0.3")

        return signal, conf

    def validate_parameters(self) -> bool:
        """
        멀티 지표 파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            StrategyError: 파라미터가 유효하지 않은 경우
        """
        errors = []

        if self.combination_mode not in ["AND", "OR"]:
            errors.append("combination_mode는 'AND' 또는 'OR'이어야 합니다")

        if self.combination_mode == "OR" and self.min_indicators < 1:
            errors.append("OR 모드에서 min_indicators는 1 이상이어야 합니다")

        # 최소 하나의 지표는 사용해야 함
        if not any([self.use_rsi, self.use_macd, self.use_bollinger, self.use_volume]):
            errors.append("최소 하나의 지표는 활성화해야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "멀티 지표 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """
        필요한 최소 데이터 개수

        Returns:
            int: 가장 긴 지표 기간 + 10
        """
        max_period = max(
            self.rsi_period if self.use_rsi else 0,
            self.macd_slow + self.macd_signal if self.use_macd else 0,
            self.bb_period if self.use_bollinger else 0,
            20  # 거래량 평균 계산용
        )
        return max_period + 10

    def __repr__(self) -> str:
        active_indicators = []
        if self.use_rsi:
            active_indicators.append("RSI")
        if self.use_macd:
            active_indicators.append("MACD")
        if self.use_bollinger:
            active_indicators.append("BB")
        if self.use_volume:
            active_indicators.append("VOL")

        return (
            f"<MultiIndicatorEntryStrategy(name={self.name}, "
            f"mode={self.combination_mode}, indicators={'+'.join(active_indicators)})>"
        )


if __name__ == "__main__":
    print("=== 멀티 지표 매수 전략 테스트 ===")

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

    # 멀티 지표 전략 생성 (AND 모드)
    strategy = MultiIndicatorEntryStrategy(
        id=1,
        parameters={
            "use_rsi": True,
            "use_macd": True,
            "use_bollinger": True,
            "use_volume": True,
            "combination_mode": "AND",
            "min_confidence": 0.65,
        }
    )

    # 전략 활성화
    strategy.activate()

    # 시그널 생성
    signal_data = strategy.analyze("KRW-BTC", test_data)

    print(f"\n시그널: {signal_data.signal.value.upper()}")
    print(f"확신도: {signal_data.confidence:.2%}")
    print(f"가격: {signal_data.price:,.0f} KRW")
    print(f"\n지표:")
    if "rsi" in signal_data.indicators:
        print(f"  RSI: {signal_data.indicators['rsi']:.2f}")
    if "macd" in signal_data.indicators:
        print(f"  MACD: {signal_data.indicators['macd']:.2f}")
        print(f"  Signal: {signal_data.indicators['macd_signal']:.2f}")
    if "bb_lower" in signal_data.indicators:
        print(f"  BB Lower: {signal_data.indicators['bb_lower']:,.0f}")
    if "volume_ratio" in signal_data.indicators:
        print(f"  Volume Ratio: {signal_data.indicators['volume_ratio']:.2f}")
