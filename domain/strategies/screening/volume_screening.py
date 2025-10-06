"""
거래량 기반 종목선정 전략
"""
from typing import Dict
from datetime import datetime

from domain.strategies.screening.base_screening import BaseScreeningStrategy, SymbolScore


class VolumeScreening(BaseScreeningStrategy):
    """거래량 기반 스크리닝"""

    def calculate_score(self, symbol: str, market_data: Dict) -> SymbolScore:
        volume_24h = market_data.get("volume_24h", 0)
        volume_change = market_data.get("volume_change_24h", 0)

        # 거래대금 점수
        volume_score = min(volume_24h / 1000000000, 1.0)  # 10억 기준

        # 거래량 급증 점수
        surge_score = min(volume_change / 200, 1.0)  # 200% 기준

        total_score = (volume_score * 0.5 + surge_score * 0.5) * 100

        return SymbolScore(
            symbol=symbol,
            score=total_score,
            details={
                "volume_24h": volume_24h,
                "volume_change": volume_change,
                "volume_score": volume_score * 100,
                "surge_score": surge_score * 100
            },
            timestamp=datetime.now()
        )

    def validate_parameters(self) -> bool:
        return True
