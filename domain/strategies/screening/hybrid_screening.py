"""
BTS 하이브리드 종목선정 전략

여러 스크리닝 전략을 가중치로 조합하여 종합 점수 산출
"""
from typing import Dict, List, Optional
from datetime import datetime

from domain.strategies.screening.base_screening import BaseScreeningStrategy, SymbolScore
from domain.strategies.screening.momentum_screening import MomentumScreening
from domain.strategies.screening.volume_screening import VolumeScreening
from domain.strategies.screening.technical_screening import TechnicalScreening
from utils.logger import get_logger

logger = get_logger(__name__)


class HybridScreening(BaseScreeningStrategy):
    """
    하이브리드 스크리닝 전략

    복수의 스크리닝 전략을 조합하여 가중 평균으로 최종 점수 산출

    파라미터:
        - strategy_weights: 각 전략별 가중치
          예: {"momentum": 0.4, "volume": 0.3, "technical": 0.3}
        - momentum_*: 모멘텀 전략 파라미터
        - volume_*: 거래량 전략 파라미터
        - technical_*: 기술지표 전략 파라미터
        - min_score: 최소 점수 (이 점수 이상만 선정)
    """

    def __init__(self, parameters: Dict):
        """
        하이브리드 스크리닝 전략 초기화

        Args:
            parameters: 전략 파라미터
        """
        # 기본 파라미터
        default_params = {
            # 전략 가중치
            "strategy_weights": {
                "momentum": 0.40,
                "volume": 0.30,
                "technical": 0.30,
            },
            # Momentum 세부 설정
            "momentum_price_weight": 0.4,
            "momentum_volume_weight": 0.3,
            "momentum_rsi_weight": 0.3,
            "momentum_period_1d": True,
            "momentum_period_7d": True,
            "momentum_period_30d": True,
            "momentum_period_1d_weight": 0.5,
            "momentum_period_7d_weight": 0.3,
            "momentum_period_30d_weight": 0.2,
            # Volume 세부 설정
            "volume_amount_weight": 0.5,
            "volume_surge_weight": 0.5,
            "volume_threshold": 1.5,  # 평균 대비 배수
            "volume_period": 20,  # 평균 계산 기간
            # Technical 세부 설정
            "technical_rsi_weight": 0.3,
            "technical_macd_weight": 0.4,
            "technical_ma_weight": 0.3,
            "technical_rsi": True,
            "technical_macd": True,
            "technical_ma": True,
            "technical_rsi_period": 14,
            "technical_macd_fast": 12,
            "technical_macd_slow": 26,
            "technical_macd_signal": 9,
            "technical_ma_short": 20,
            "technical_ma_long": 60,
            # 최소 점수
            "min_score": 0.5,
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(default_params)

        self.strategy_weights = self.parameters["strategy_weights"]
        self.min_score = self.parameters["min_score"]

        # 서브 전략들 초기화
        self.sub_strategies: Dict[str, BaseScreeningStrategy] = {}
        self._initialize_sub_strategies()

    def _initialize_sub_strategies(self):
        """서브 전략 초기화"""
        # Momentum 전략
        if "momentum" in self.strategy_weights:
            self.sub_strategies["momentum"] = MomentumScreening(
                parameters={
                    "price_weight": self.parameters.get("momentum_price_weight", 0.4),
                    "volume_weight": self.parameters.get("momentum_volume_weight", 0.3),
                    "rsi_weight": self.parameters.get("momentum_rsi_weight", 0.3),
                    "period_1d": self.parameters.get("momentum_period_1d", True),
                    "period_7d": self.parameters.get("momentum_period_7d", True),
                    "period_30d": self.parameters.get("momentum_period_30d", True),
                    "period_1d_weight": self.parameters.get("momentum_period_1d_weight", 0.5),
                    "period_7d_weight": self.parameters.get("momentum_period_7d_weight", 0.3),
                    "period_30d_weight": self.parameters.get("momentum_period_30d_weight", 0.2),
                }
            )

        # Volume 전략
        if "volume" in self.strategy_weights:
            self.sub_strategies["volume"] = VolumeScreening(
                parameters={
                    "amount_weight": self.parameters.get("volume_amount_weight", 0.5),
                    "surge_weight": self.parameters.get("volume_surge_weight", 0.5),
                    "threshold": self.parameters.get("volume_threshold", 1.5),
                    "period": self.parameters.get("volume_period", 20),
                }
            )

        # Technical 전략
        if "technical" in self.strategy_weights:
            self.sub_strategies["technical"] = TechnicalScreening(
                parameters={
                    "rsi_weight": self.parameters.get("technical_rsi_weight", 0.3),
                    "macd_weight": self.parameters.get("technical_macd_weight", 0.4),
                    "ma_weight": self.parameters.get("technical_ma_weight", 0.3),
                    "use_rsi": self.parameters.get("technical_rsi", True),
                    "use_macd": self.parameters.get("technical_macd", True),
                    "use_ma": self.parameters.get("technical_ma", True),
                    "rsi_period": self.parameters.get("technical_rsi_period", 14),
                    "macd_fast": self.parameters.get("technical_macd_fast", 12),
                    "macd_slow": self.parameters.get("technical_macd_slow", 26),
                    "macd_signal": self.parameters.get("technical_macd_signal", 9),
                    "ma_short": self.parameters.get("technical_ma_short", 20),
                    "ma_long": self.parameters.get("technical_ma_long", 60),
                }
            )

        logger.info(f"하이브리드 스크리닝 초기화: {len(self.sub_strategies)}개 서브 전략")

    def calculate_score(self, symbol: str, market_data: Dict) -> SymbolScore:
        """
        하이브리드 점수 계산

        각 서브 전략의 점수를 가중 평균하여 종합 점수 산출

        Args:
            symbol: 심볼 (예: KRW-BTC)
            market_data: 시장 데이터

        Returns:
            SymbolScore: 종목 점수
        """
        scores = {}
        details = {}
        total_weight = 0.0

        # 1. Momentum 점수
        if "momentum" in self.sub_strategies and "momentum" in self.strategy_weights:
            try:
                momentum_score_obj = self.sub_strategies["momentum"].calculate_score(symbol, market_data)
                weight = self.strategy_weights["momentum"]
                scores["momentum"] = momentum_score_obj.score * weight
                total_weight += weight

                # 세부 정보 저장
                details["momentum_score"] = momentum_score_obj.score
                details["momentum_weight"] = weight
                details.update({f"momentum_{k}": v for k, v in momentum_score_obj.details.items()})
            except Exception as e:
                logger.warning(f"{symbol} - Momentum 점수 계산 실패: {e}")

        # 2. Volume 점수
        if "volume" in self.sub_strategies and "volume" in self.strategy_weights:
            try:
                volume_score_obj = self.sub_strategies["volume"].calculate_score(symbol, market_data)
                weight = self.strategy_weights["volume"]
                scores["volume"] = volume_score_obj.score * weight
                total_weight += weight

                details["volume_score"] = volume_score_obj.score
                details["volume_weight"] = weight
                details.update({f"volume_{k}": v for k, v in volume_score_obj.details.items()})
            except Exception as e:
                logger.warning(f"{symbol} - Volume 점수 계산 실패: {e}")

        # 3. Technical 점수
        if "technical" in self.sub_strategies and "technical" in self.strategy_weights:
            try:
                technical_score_obj = self.sub_strategies["technical"].calculate_score(symbol, market_data)
                weight = self.strategy_weights["technical"]
                scores["technical"] = technical_score_obj.score * weight
                total_weight += weight

                details["technical_score"] = technical_score_obj.score
                details["technical_weight"] = weight
                details.update({f"technical_{k}": v for k, v in technical_score_obj.details.items()})
            except Exception as e:
                logger.warning(f"{symbol} - Technical 점수 계산 실패: {e}")

        # 4. 종합 점수 계산 (가중 평균)
        if total_weight > 0:
            final_score = sum(scores.values()) / total_weight
        else:
            logger.warning(f"{symbol} - 가중치 합계가 0입니다")
            final_score = 0.0

        details["final_score"] = final_score
        details["total_weight"] = total_weight

        logger.debug(
            f"{symbol} 하이브리드 점수: {final_score:.2%} | "
            f"상세: {', '.join(f'{k}={v:.2%}' for k, v in scores.items())}"
        )

        return SymbolScore(
            symbol=symbol,
            score=final_score,
            details=details,
            timestamp=datetime.now()
        )

    def validate_parameters(self) -> bool:
        """
        하이브리드 파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            ValueError: 파라미터가 유효하지 않은 경우
        """
        errors = []

        # 가중치 합계 검증
        total_weight = sum(self.strategy_weights.values())
        if not (0.99 <= total_weight <= 1.01):  # 부동소수점 오차 허용
            errors.append(f"전략 가중치 합계가 1이 아닙니다: {total_weight}")

        # 각 가중치 검증
        for name, weight in self.strategy_weights.items():
            if not (0 <= weight <= 1):
                errors.append(f"{name} 가중치가 0-1 범위를 벗어남: {weight}")

        # 최소 점수 검증
        if not (0 <= self.min_score <= 1):
            errors.append(f"min_score는 0-1 범위여야 합니다: {self.min_score}")

        # 서브 전략 검증
        for strategy_name, strategy in self.sub_strategies.items():
            try:
                strategy.validate_parameters()
            except Exception as e:
                errors.append(f"{strategy_name} 전략 검증 실패: {e}")

        if errors:
            raise ValueError(f"하이브리드 스크리닝 파라미터 검증 실패: {', '.join(errors)}")

        return True

    def get_strategy_details(self) -> Dict:
        """
        전략 상세 정보 조회

        Returns:
            Dict: 전략 가중치 및 설정
        """
        return {
            "weights": self.strategy_weights,
            "min_score": self.min_score,
            "sub_strategies": [s.name for s in self.sub_strategies.values()],
        }

    def __repr__(self) -> str:
        weights_str = ", ".join(f"{k}={v:.0%}" for k, v in self.strategy_weights.items())
        return (
            f"<HybridScreening(name={self.name}, "
            f"weights=[{weights_str}], min_score={self.min_score:.0%})>"
        )
