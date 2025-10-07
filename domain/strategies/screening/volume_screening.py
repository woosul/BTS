"""
거래량 기반 종목선정 전략
"""
from typing import Dict
from datetime import datetime

from domain.strategies.screening.base_screening import BaseScreeningStrategy, SymbolScore
from utils.logger import get_logger

logger = get_logger(__name__)


class VolumeScreening(BaseScreeningStrategy):
    """
    거래량 기반 스크리닝 전략

    파라미터:
        - amount_weight: 거래대금 가중치 (기본: 0.5)
        - surge_weight: 거래량 급증 가중치 (기본: 0.5)
        - threshold: 거래량 배수 임계값 (기본: 1.5)
        - period: 평균 계산 기간 (기본: 20일)
    """

    def __init__(self, parameters: Dict):
        super().__init__(parameters)

        # 가중치 설정
        self.amount_weight = float(parameters.get("amount_weight", 0.5))
        self.surge_weight = float(parameters.get("surge_weight", 0.5))

        # 임계값 설정
        self.threshold = float(parameters.get("threshold", 1.5))
        self.period = int(parameters.get("period", 20))

    def calculate_score(self, symbol: str, market_data: Dict) -> SymbolScore:
        volume_24h = market_data.get("volume_24h", 0)
        volume_change = market_data.get("volume_change_24h", 0)

        # 거래대금 점수 (10억 기준)
        volume_score = min(volume_24h / 1000000000, 1.0)

        # 거래량 급증 점수 (임계값 기준)
        surge_score = min(volume_change / (self.threshold * 100), 1.0)

        # 가중 평균
        total_score = (
            volume_score * self.amount_weight +
            surge_score * self.surge_weight
        ) * 100

        return SymbolScore(
            symbol=symbol,
            score=total_score,
            details={
                "volume_24h": volume_24h,
                "volume_change": volume_change,
                "volume_score": volume_score * 100,
                "surge_score": surge_score * 100,
                "amount_weight": self.amount_weight,
                "surge_weight": self.surge_weight
            },
            timestamp=datetime.now()
        )

    def validate_parameters(self) -> bool:
        """파라미터 검증"""
        if not (0 <= self.amount_weight <= 1):
            raise ValueError("amount_weight는 0~1 사이여야 합니다")
        if not (0 <= self.surge_weight <= 1):
            raise ValueError("surge_weight는 0~1 사이여야 합니다")

        total_weight = self.amount_weight + self.surge_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"가중치 합은 1.0이어야 합니다: {total_weight}")

        if self.threshold <= 0:
            raise ValueError("threshold는 0보다 커야 합니다")
        if self.period <= 0:
            raise ValueError("period는 0보다 커야 합니다")

        return True
