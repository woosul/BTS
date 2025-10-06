"""
하이브리드 종목선정 전략 (복합 전략 가중치 조합)
"""
from typing import Dict, List
from datetime import datetime

from domain.strategies.screening.base_screening import BaseScreeningStrategy, SymbolScore


class HybridScreening(BaseScreeningStrategy):
    """
    하이브리드 스크리닝 (여러 전략 조합)

    파라미터:
        - strategies: 사용할 전략 목록
        - weights: 각 전략별 가중치
    """

    def __init__(self, parameters: Dict):
        super().__init__(parameters)
        self.strategies: List[BaseScreeningStrategy] = parameters.get("strategies", [])
        self.weights: List[float] = parameters.get("weights", [])

        if len(self.strategies) != len(self.weights):
            raise ValueError("전략 수와 가중치 수가 일치해야 합니다")

    def calculate_score(self, symbol: str, market_data: Dict) -> SymbolScore:
        total_score = 0.0
        details = {}

        for i, strategy in enumerate(self.strategies):
            score_obj = strategy.calculate_score(symbol, market_data)
            weighted_score = score_obj.score * self.weights[i]
            total_score += weighted_score

            details[f"{strategy.name}_score"] = score_obj.score
            details[f"{strategy.name}_weight"] = self.weights[i]

        return SymbolScore(
            symbol=symbol,
            score=total_score,
            details=details,
            timestamp=datetime.now()
        )

    def validate_parameters(self) -> bool:
        if sum(self.weights) != 1.0:
            raise ValueError(f"가중치 합은 1.0이어야 합니다: {sum(self.weights)}")
        return True
