"""
BTS RSI (Relative Strength Index) 전략

RSI 지표 기반 트레이딩 전략
"""
from typing import Dict, List
from decimal import Decimal
import pandas as pd
from datetime import datetime

from domain.strategies.base_strategy import BaseStrategy
from core.enums import StrategySignal, TimeFrame
from core.models import OHLCV, StrategySignalData
from core.exceptions import StrategyError, IndicatorCalculationError
from utils.logger import get_logger

logger = get_logger(__name__)


class RSIStrategy(BaseStrategy):
    """
    RSI 전략

    기본 규칙:
    - RSI < 과매도 기준 → 매수 시그널
    - RSI > 과매수 기준 → 매도 시그널
    - 그 외 → 보유

    파라미터:
    - rsi_period: RSI 기간 (기본 14)
    - oversold: 과매도 기준 (기본 30)
    - overbought: 과매수 기준 (기본 70)
    """

    def __init__(
        self,
        id: int,
        name: str = "RSI Strategy",
        description: str = "RSI 지표 기반 트레이딩 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
            "min_data_points": 30,
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(
            id=id,
            name=name,
            description=description,
            timeframe=timeframe,
            parameters=default_params
        )

    def validate_parameters(self) -> bool:
        """
        파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            StrategyError: 파라미터가 유효하지 않은 경우
        """
        rsi_period = self.get_parameter("rsi_period")
        oversold = self.get_parameter("oversold")
        overbought = self.get_parameter("overbought")

        # RSI 기간 검증
        if not isinstance(rsi_period, int) or rsi_period < 2:
            raise StrategyError(
                "RSI 기간은 2 이상의 정수여야 합니다",
                {"rsi_period": rsi_period}
            )

        # 과매도/과매수 기준 검증
        if not (0 < oversold < overbought < 100):
            raise StrategyError(
                "과매도 < 과매수 기준이어야 하며, 0-100 범위여야 합니다",
                {"oversold": oversold, "overbought": overbought}
            )

        logger.debug(f"파라미터 검증 완료: {self.parameters}")
        return True

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        RSI 지표 계산

        Args:
            ohlcv_data: OHLCV 데이터 리스트

        Returns:
            Dict: RSI 및 관련 지표

        Raises:
            IndicatorCalculationError: 지표 계산 실패
        """
        try:
            # OHLCV 데이터를 DataFrame으로 변환
            df = pd.DataFrame([
                {
                    "timestamp": candle.timestamp,
                    "open": float(candle.open),
                    "high": float(candle.high),
                    "low": float(candle.low),
                    "close": float(candle.close),
                    "volume": float(candle.volume),
                }
                for candle in ohlcv_data
            ])

            # RSI 계산
            rsi_period = self.get_parameter("rsi_period")
            df["rsi"] = self._calculate_rsi(df["close"], rsi_period)

            # 최신 값 추출
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            indicators = {
                "rsi": Decimal(str(latest["rsi"])),
                "rsi_previous": Decimal(str(previous["rsi"])),
                "price": Decimal(str(latest["close"])),
                "volume": Decimal(str(latest["volume"])),
            }

            logger.debug(f"RSI 계산 완료: {indicators['rsi']:.2f}")
            return indicators

        except Exception as e:
            logger.error(f"지표 계산 실패: {e}")
            raise IndicatorCalculationError(
                f"RSI 계산 실패: {str(e)}",
                {"error": str(e)}
            )

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """
        RSI 계산 로직

        Args:
            prices: 가격 시리즈
            period: RSI 기간

        Returns:
            pd.Series: RSI 값
        """
        # 가격 변화 계산
        delta = prices.diff()

        # 상승/하락 분리
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 평균 계산 (EMA 방식)
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        # RS 및 RSI 계산
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def generate_signal(
        self,
        symbol: str,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> StrategySignalData:
        """
        RSI 기반 시그널 생성

        Args:
            symbol: 거래 심볼
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표

        Returns:
            StrategySignalData: 시그널 데이터
        """
        rsi = indicators["rsi"]
        rsi_previous = indicators["rsi_previous"]
        oversold = Decimal(str(self.get_parameter("oversold")))
        overbought = Decimal(str(self.get_parameter("overbought")))

        # 시그널 결정
        signal = StrategySignal.HOLD
        signal_strength = Decimal("0")

        # 과매도 → 매수
        if rsi < oversold:
            signal = StrategySignal.BUY
            # RSI가 낮을수록 강한 매수 시그널
            signal_strength = (oversold - rsi) / oversold
            signal_strength = min(Decimal("1"), signal_strength)

        # 과매수 → 매도
        elif rsi > overbought:
            signal = StrategySignal.SELL
            # RSI가 높을수록 강한 매도 시그널
            signal_strength = (rsi - overbought) / (Decimal("100") - overbought)
            signal_strength = min(Decimal("1"), signal_strength)

        # 추세 강도 계산 (RSI 변화율)
        rsi_change = abs(rsi - rsi_previous)
        trend_strength = min(Decimal("1"), rsi_change / Decimal("10"))

        # 거래량 강도 (간단히 1로 설정, 추후 개선 가능)
        volume_strength = Decimal("1")

        # 확신도 계산
        confidence = self.calculate_confidence(
            signal_strength,
            trend_strength,
            volume_strength
        )

        # 시그널 데이터 생성
        signal_data = StrategySignalData(
            strategy_id=self.id,
            strategy_name=self.name,
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            indicators={
                "rsi": float(rsi),
                "rsi_previous": float(rsi_previous),
                "oversold": float(oversold),
                "overbought": float(overbought),
                "signal_strength": float(signal_strength),
                "price": float(indicators["price"]),
            },
            timestamp=datetime.now(),
        )

        return signal_data

    def get_minimum_data_points(self) -> int:
        """
        필요한 최소 데이터 개수

        RSI 계산을 위해 RSI 기간 * 2 정도 필요

        Returns:
            int: 최소 데이터 개수
        """
        rsi_period = self.get_parameter("rsi_period")
        return max(rsi_period * 2, 30)

    def __repr__(self) -> str:
        oversold = self.get_parameter("oversold")
        overbought = self.get_parameter("overbought")
        return (
            f"<RSIStrategy(id={self.id}, name={self.name}, "
            f"RSI({self.get_parameter('rsi_period')}), "
            f"과매도={oversold}, 과매수={overbought})>"
        )


if __name__ == "__main__":
    # RSI 전략 테스트
    print("=== RSI 전략 테스트 ===")

    # 전략 생성
    strategy = RSIStrategy(
        id=1,
        parameters={
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
        }
    )

    print(f"\n1. 전략 생성: {strategy}")
    print(f"   파라미터: {strategy.parameters}")

    # 파라미터 검증
    try:
        strategy.validate_parameters()
        print("\n2. 파라미터 검증: 통과")
    except StrategyError as e:
        print(f"\n2. 파라미터 검증 실패: {e}")

    # 전략 활성화
    strategy.activate()
    print(f"\n3. 전략 상태: {strategy.status.value}")

    # 샘플 OHLCV 데이터 생성
    sample_data = []
    base_price = Decimal("50000000")

    for i in range(50):
        # 간단한 가격 변동 시뮬레이션
        price_change = Decimal(str((i % 10 - 5) * 100000))
        close_price = base_price + price_change

        candle = OHLCV(
            symbol="KRW-BTC",
            timestamp=datetime.now(),
            open=close_price,
            high=close_price * Decimal("1.01"),
            low=close_price * Decimal("0.99"),
            close=close_price,
            volume=Decimal("100")
        )
        sample_data.append(candle)

    print(f"\n4. 샘플 데이터: {len(sample_data)}개 캔들")

    # 지표 계산
    try:
        indicators = strategy.calculate_indicators(sample_data)
        print(f"\n5. 계산된 지표:")
        print(f"   RSI: {indicators['rsi']:.2f}")
        print(f"   가격: {indicators['price']:,.0f} KRW")

        # 시그널 생성
        signal_data = strategy.generate_signal("KRW-BTC", sample_data, indicators)
        print(f"\n6. 생성된 시그널:")
        print(f"   시그널: {signal_data.signal.value.upper()}")
        print(f"   확신도: {signal_data.confidence:.2%}")

    except Exception as e:
        print(f"\n오류 발생: {e}")

    # 통계
    stats = strategy.get_statistics()
    print(f"\n7. 전략 통계:")
    print(f"   총 시그널: {stats['total_signals']}")
    print(f"   매수: {stats['buy_signals']}, 매도: {stats['sell_signals']}, 보유: {stats['hold_signals']}")
