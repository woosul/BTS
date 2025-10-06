"""
BTS Base AI Client

AI 클라이언트 추상 베이스 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, List
from decimal import Decimal


class BaseAIClient(ABC):
    """
    AI 클라이언트 베이스 클래스

    Claude, OpenAI 등 다양한 AI 제공자를 위한 공통 인터페이스
    """

    @abstractmethod
    def evaluate_entry_signal(
        self,
        symbol: str,
        summary_data: Dict,
        strategy_signals: List[Dict]
    ) -> Dict:
        """
        매수 시그널 평가

        Args:
            symbol: 거래 심볼
            summary_data: 요약된 차트 데이터
            strategy_signals: 각 전략의 시그널

        Returns:
            Dict: AI 평가 결과
                {
                    "recommendation": "buy|sell|hold",
                    "confidence": 0-100,
                    "reasoning": "이유",
                    "warnings": "경고 (선택)"
                }
        """
        pass

    @abstractmethod
    def evaluate_exit_signal(
        self,
        symbol: str,
        entry_price: Decimal,
        current_price: Decimal,
        holding_period: int,
        summary_data: Dict,
        strategy_signals: List[Dict]
    ) -> Dict:
        """
        매도 시그널 평가

        Args:
            symbol: 거래 심볼
            entry_price: 진입 가격
            current_price: 현재 가격
            holding_period: 보유 기간
            summary_data: 요약된 차트 데이터
            strategy_signals: 각 전략의 시그널

        Returns:
            Dict: AI 평가 결과
        """
        pass

    @abstractmethod
    def batch_evaluate(
        self,
        evaluations: List[Dict]
    ) -> List[Dict]:
        """
        배치 평가

        Args:
            evaluations: 평가 요청 리스트

        Returns:
            List[Dict]: 평가 결과 리스트
        """
        pass
