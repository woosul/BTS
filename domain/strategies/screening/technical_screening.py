"""
기술지표 복합 종목선정 전략
"""
from typing import Dict
from datetime import datetime

from domain.strategies.screening.base_screening import BaseScreeningStrategy, SymbolScore
from utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalScreening(BaseScreeningStrategy):
    """
    기술지표 복합 스크리닝 전략

    파라미터:
        - rsi_weight: RSI 가중치 (기본: 0.3)
        - macd_weight: MACD 가중치 (기본: 0.4)
        - ma_weight: 이동평균 가중치 (기본: 0.3)
        - use_rsi: RSI 사용 여부 (기본: True)
        - use_macd: MACD 사용 여부 (기본: True)
        - use_ma: 이동평균 사용 여부 (기본: True)
        - rsi_period: RSI 기간 (기본: 14)
        - macd_fast: MACD 단기 (기본: 12)
        - macd_slow: MACD 장기 (기본: 26)
        - macd_signal: MACD 시그널 (기본: 9)
        - ma_short: 단기 이동평균 (기본: 20)
        - ma_long: 장기 이동평균 (기본: 60)
    """

    def __init__(self, parameters: Dict):
        super().__init__(parameters)

        # 가중치 설정
        self.rsi_weight = float(parameters.get("rsi_weight", 0.3))
        self.macd_weight = float(parameters.get("macd_weight", 0.4))
        self.ma_weight = float(parameters.get("ma_weight", 0.3))

        # 사용 여부 설정
        self.use_rsi = bool(parameters.get("use_rsi", True))
        self.use_macd = bool(parameters.get("use_macd", True))
        self.use_ma = bool(parameters.get("use_ma", True))

        # RSI 상세 설정
        self.rsi_period = int(parameters.get("rsi_period", 14))

        # MACD 상세 설정
        self.macd_fast = int(parameters.get("macd_fast", 12))
        self.macd_slow = int(parameters.get("macd_slow", 26))
        self.macd_signal = int(parameters.get("macd_signal", 9))

        # 이동평균 상세 설정
        self.ma_short = int(parameters.get("ma_short", 20))
        self.ma_long = int(parameters.get("ma_long", 60))

    def calculate_score(self, symbol: str, market_data: Dict) -> SymbolScore:
        indicators = market_data.get("indicators", {})
        scores = {}
        total_weight = 0.0

        # RSI 점수 (40-60 구간이 좋음)
        if self.use_rsi:
            rsi = indicators.get("rsi", 50)
            rsi_score = 1.0 - abs(rsi - 50) / 50
            scores["rsi"] = rsi_score * self.rsi_weight
            total_weight += self.rsi_weight

        # MACD 점수 (양수면 상승, 음수면 하락)
        if self.use_macd:
            macd_value = indicators.get("macd", {}).get("value", 0)
            macd_signal = indicators.get("macd", {}).get("signal", 0)
            macd_score = 1.0 if macd_value > macd_signal else 0.0
            scores["macd"] = macd_score * self.macd_weight
            total_weight += self.macd_weight

        # 이동평균 정배열 점수
        if self.use_ma:
            ma_20 = indicators.get("ma_20", 0)
            ma_60 = indicators.get("ma_60", 0)
            current_price = market_data.get("price", 0)

            ma_score = 0.0
            if current_price > ma_20 > ma_60:
                ma_score = 1.0
            elif current_price > ma_20 or ma_20 > ma_60:
                ma_score = 0.5

            scores["ma"] = ma_score * self.ma_weight
            total_weight += self.ma_weight

        # 가중 평균
        if total_weight > 0:
            total_score = sum(scores.values()) / total_weight * 100
        else:
            logger.warning(f"{symbol} - 가중치 합계가 0입니다")
            total_score = 0.0

        return SymbolScore(
            symbol=symbol,
            score=total_score,
            details={
                "rsi": indicators.get("rsi", 50) if self.use_rsi else None,
                "macd_value": indicators.get("macd", {}).get("value", 0) if self.use_macd else None,
                "macd_signal": indicators.get("macd", {}).get("signal", 0) if self.use_macd else None,
                "ma_20": indicators.get("ma_20", 0) if self.use_ma else None,
                "ma_60": indicators.get("ma_60", 0) if self.use_ma else None,
                "rsi_score": scores.get("rsi", 0) / self.rsi_weight * 100 if self.use_rsi and self.rsi_weight > 0 else None,
                "macd_score": scores.get("macd", 0) / self.macd_weight * 100 if self.use_macd and self.macd_weight > 0 else None,
                "ma_score": scores.get("ma", 0) / self.ma_weight * 100 if self.use_ma and self.ma_weight > 0 else None
            },
            timestamp=datetime.now()
        )

    def validate_parameters(self) -> bool:
        """파라미터 검증"""
        if not (0 <= self.rsi_weight <= 1):
            raise ValueError("rsi_weight는 0~1 사이여야 합니다")
        if not (0 <= self.macd_weight <= 1):
            raise ValueError("macd_weight는 0~1 사이여야 합니다")
        if not (0 <= self.ma_weight <= 1):
            raise ValueError("ma_weight는 0~1 사이여야 합니다")

        # 사용하는 지표의 가중치 합계 검증
        active_weights = 0.0
        if self.use_rsi:
            active_weights += self.rsi_weight
        if self.use_macd:
            active_weights += self.macd_weight
        if self.use_ma:
            active_weights += self.ma_weight

        if active_weights > 0 and abs(active_weights - 1.0) > 0.01:
            raise ValueError(f"활성 지표의 가중치 합은 1.0이어야 합니다: {active_weights}")

        if not any([self.use_rsi, self.use_macd, self.use_ma]):
            raise ValueError("최소 1개 기술지표를 사용해야 합니다")

        return True
