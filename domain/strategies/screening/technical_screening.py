"""
기술지표 복합 종목선정 전략
"""
from typing import Dict
from datetime import datetime

from domain.strategies.screening.base_screening import BaseScreeningStrategy, SymbolScore


class TechnicalScreening(BaseScreeningStrategy):
    """기술지표 복합 스크리닝 (RSI + MACD + 이동평균)"""

    def calculate_score(self, symbol: str, market_data: Dict) -> SymbolScore:
        indicators = market_data.get("indicators", {})

        # RSI 점수 (40-60 구간이 좋음)
        rsi = indicators.get("rsi", 50)
        rsi_score = 1.0 - abs(rsi - 50) / 50

        # MACD 점수 (양수면 상승, 음수면 하락)
        macd_value = indicators.get("macd", {}).get("value", 0)
        macd_signal = indicators.get("macd", {}).get("signal", 0)
        macd_score = 1.0 if macd_value > macd_signal else 0.0

        # 이동평균 정배열 점수
        ma_20 = indicators.get("ma_20", 0)
        ma_60 = indicators.get("ma_60", 0)
        current_price = market_data.get("price", 0)

        ma_score = 0.0
        if current_price > ma_20 > ma_60:
            ma_score = 1.0
        elif current_price > ma_20 or ma_20 > ma_60:
            ma_score = 0.5

        total_score = (rsi_score * 0.3 + macd_score * 0.4 + ma_score * 0.3) * 100

        return SymbolScore(
            symbol=symbol,
            score=total_score,
            details={
                "rsi": rsi,
                "macd_value": macd_value,
                "macd_signal": macd_signal,
                "ma_20": ma_20,
                "ma_60": ma_60,
                "rsi_score": rsi_score * 100,
                "macd_score": macd_score * 100,
                "ma_score": ma_score * 100
            },
            timestamp=datetime.now()
        )

    def validate_parameters(self) -> bool:
        return True
