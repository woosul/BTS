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
        - period_1d: 1일 모멘텀 사용 여부 (기본: True)
        - period_7d: 7일 모멘텀 사용 여부 (기본: True)
        - period_30d: 30일 모멘텀 사용 여부 (기본: True)
    """

    def __init__(self, parameters: Dict):
        super().__init__(parameters)

        # 가중치 설정
        self.price_weight = float(parameters.get("price_weight", 0.4))
        self.volume_weight = float(parameters.get("volume_weight", 0.3))
        self.rsi_weight = float(parameters.get("rsi_weight", 0.3))

        # 기간 설정
        self.period_1d = bool(parameters.get("period_1d", True))
        self.period_7d = bool(parameters.get("period_7d", True))
        self.period_30d = bool(parameters.get("period_30d", True))

    def calculate_score(self, symbol: str, market_data: Dict) -> SymbolScore:
        """
        모멘텀 점수 계산

        Args:
            symbol: 심볼
            market_data: 시장 데이터

        Returns:
            SymbolScore: 종목 점수
        """
        # 기간별 가격 변동률 수집
        price_scores = []
        if self.period_1d:
            price_change_1d = market_data.get("price_change_24h", 0.0)
            price_scores.append(self._normalize_score(price_change_1d, -10, 30))
        if self.period_7d:
            price_change_7d = market_data.get("price_change_7d", 0.0)
            price_scores.append(self._normalize_score(price_change_7d, -20, 50))
        if self.period_30d:
            price_change_30d = market_data.get("price_change_30d", 0.0)
            price_scores.append(self._normalize_score(price_change_30d, -30, 100))

        # 평균 가격 점수
        price_score = sum(price_scores) / len(price_scores) if price_scores else 0.0

        # 거래량 변동률 점수 (활성 기간 중 최대값 활용)
        volume_scores = []
        if self.period_1d:
            volume_change_1d = market_data.get("volume_change_24h", 0.0)
            volume_scores.append(self._normalize_score(volume_change_1d, 0, 200))
        if self.period_7d:
            volume_change_7d = market_data.get("volume_change_7d", 0.0)
            volume_scores.append(self._normalize_score(volume_change_7d, 0, 300))
        if self.period_30d:
            volume_change_30d = market_data.get("volume_change_30d", 0.0)
            volume_scores.append(self._normalize_score(volume_change_30d, 0, 500))

        volume_score = max(volume_scores) if volume_scores else 0.0

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
                "price_change_1d": market_data.get("price_change_24h", 0.0),
                "price_change_7d": market_data.get("price_change_7d", 0.0),
                "price_change_30d": market_data.get("price_change_30d", 0.0),
                "volume_change_24h": market_data.get("volume_change_24h", 0.0),
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
