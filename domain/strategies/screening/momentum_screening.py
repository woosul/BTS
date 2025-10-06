"""
모멘텀 기반 종목선정 전략

가격 상승률, 거래량 증가율, RSI 모멘텀 등을 기반으로 종목 선정
"""
from typing import Dict
from datetime import datetime
import pandas as pd

from domain.strategies.screening.base_screening import BaseScreeningStrategy, SymbolScore
from utils.logger import get_logger

logger = get_logger(__name__)


class MomentumScreening(BaseScreeningStrategy):
    """
    모멘텀 기반 스크리닝 전략

    파라미터:
        - price_weight: 가격 상승률 가중치 (기본: 0.4)
        - volume_weight: 거래량 증가율 가중치 (기본: 0.3)
        - rsi_weight: RSI 모멘텀 가중치 (기본: 0.3)
        - lookback_days: 분석 기간 (기본: 7일)
    """

    def __init__(self, parameters: Dict):
        super().__init__(parameters)

        self.price_weight = float(parameters.get("price_weight", 0.4))
        self.volume_weight = float(parameters.get("volume_weight", 0.3))
        self.rsi_weight = float(parameters.get("rsi_weight", 0.3))
        self.lookback_days = int(parameters.get("lookback_days", 7))

    def calculate_score(self, symbol: str, market_data: Dict) -> SymbolScore:
        """
        모멘텀 점수 계산

        Args:
            symbol: 심볼
            market_data: 시장 데이터

        Returns:
            SymbolScore: 종목 점수
        """
        # 가격 변동률 점수
        price_change = market_data.get("price_change_24h", 0.0)
        price_score = self._normalize_score(price_change, -10, 30)  # -10% ~ +30%

        # 거래량 변동률 점수
        volume_change = market_data.get("volume_change_24h", 0.0)
        volume_score = self._normalize_score(volume_change, 0, 200)  # 0% ~ +200%

        # RSI 모멘텀 점수 (50 기준, 높을수록 상승 모멘텀)
        rsi = market_data.get("indicators", {}).get("rsi", 50)
        rsi_score = self._normalize_score(rsi, 30, 70)  # 30 ~ 70 구간

        # 가중 평균
        total_score = (
            price_score * self.price_weight +
            volume_score * self.volume_weight +
            rsi_score * self.rsi_weight
        )

        return SymbolScore(
            symbol=symbol,
            score=total_score * 100,  # 0~100 스케일
            details={
                "price_score": price_score * 100,
                "volume_score": volume_score * 100,
                "rsi_score": rsi_score * 100,
                "price_change_24h": price_change,
                "volume_change_24h": volume_change,
                "rsi": rsi
            },
            timestamp=datetime.now()
        )

    def _normalize_score(self, value: float, min_val: float, max_val: float) -> float:
        """
        점수 정규화 (0.0 ~ 1.0)

        Args:
            value: 값
            min_val: 최소값
            max_val: 최대값

        Returns:
            float: 정규화된 점수
        """
        if value <= min_val:
            return 0.0
        if value >= max_val:
            return 1.0
        return (value - min_val) / (max_val - min_val)

    def validate_parameters(self) -> bool:
        """파라미터 검증"""
        if not (0 <= self.price_weight <= 1):
            raise ValueError("price_weight는 0~1 사이여야 합니다")
        if not (0 <= self.volume_weight <= 1):
            raise ValueError("volume_weight는 0~1 사이여야 합니다")
        if not (0 <= self.rsi_weight <= 1):
            raise ValueError("rsi_weight는 0~1 사이여야 합니다")

        total_weight = self.price_weight + self.volume_weight + self.rsi_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"가중치 합은 1.0이어야 합니다: {total_weight}")

        return True
