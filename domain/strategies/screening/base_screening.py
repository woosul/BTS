"""
종목선정 전략 베이스 클래스

모든 스크리닝 전략이 상속받아야 하는 추상 베이스 클래스
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SymbolScore:
    """종목 점수"""
    symbol: str
    score: float
    details: Dict[str, float]  # 세부 점수
    timestamp: datetime


class BaseScreeningStrategy(ABC):
    """
    종목선정 전략 베이스 클래스

    모든 스크리닝 전략은 이 클래스를 상속받아 구현
    """

    def __init__(self, parameters: Dict):
        """
        전략 초기화

        Args:
            parameters: 전략 파라미터
        """
        self.parameters = parameters
        self.name = self.__class__.__name__
        logger.info(f"{self.name} 초기화: {parameters}")

    @abstractmethod
    def calculate_score(
        self,
        symbol: str,
        market_data: Dict
    ) -> SymbolScore:
        """
        종목별 점수 계산

        Args:
            symbol: 심볼 (예: KRW-BTC)
            market_data: 시장 데이터
                - price: 현재가
                - volume_24h: 24시간 거래량
                - price_change_24h: 24시간 가격 변동률
                - ohlcv: OHLCV 데이터 (리스트)
                - indicators: 계산된 기술지표

        Returns:
            SymbolScore: 종목 점수
        """
        pass

    @abstractmethod
    def validate_parameters(self) -> bool:
        """
        파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            ValueError: 파라미터가 올바르지 않을 때
        """
        pass

    def screen(
        self,
        symbols: List[str],
        market_data_dict: Dict[str, Dict],
        top_n: int = 10
    ) -> List[SymbolScore]:
        """
        종목 스크리닝 실행

        Args:
            symbols: 심볼 목록
            market_data_dict: 심볼별 시장 데이터
            top_n: 선정할 상위 종목 수

        Returns:
            List[SymbolScore]: 상위 N개 종목 점수 목록 (점수 내림차순)
        """
        logger.info(
            f"{self.name} 스크리닝 시작: "
            f"{len(symbols)}개 종목, top {top_n} 선정"
        )

        scores = []
        for symbol in symbols:
            if symbol not in market_data_dict:
                logger.warning(f"시장 데이터 없음: {symbol}")
                continue

            try:
                score = self.calculate_score(symbol, market_data_dict[symbol])
                scores.append(score)
            except Exception as e:
                logger.error(f"{symbol} 점수 계산 실패: {e}")
                continue

        # 점수 기준 정렬
        scores.sort(key=lambda x: x.score, reverse=True)

        top_symbols = scores[:top_n]

        logger.info(
            f"{self.name} 스크리닝 완료: "
            f"상위 {len(top_symbols)}개 종목 선정"
        )

        return top_symbols

    def get_info(self) -> Dict:
        """
        전략 정보 반환

        Returns:
            Dict: 전략 정보
        """
        return {
            "name": self.name,
            "parameters": self.parameters,
            "description": self.__doc__
        }
