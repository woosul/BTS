"""
BTS AI Evaluation Service

AI 기반 전략 평가 서비스
"""
from typing import Dict, List, Optional
from decimal import Decimal

from infrastructure.ai.base_ai_client import BaseAIClient
from infrastructure.ai.claude_client import ClaudeClient
from infrastructure.ai.openai_client import OpenAIClient
from infrastructure.ai.data_summarizer import DataSummarizer
from infrastructure.ai.evaluation_cache import EvaluationCache
from core.models import OHLCV, StrategySignalData
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AIEvaluationService:
    """
    AI 평가 서비스

    전략 시그널을 AI로 평가하여 최종 결정 지원
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        cache_ttl_minutes: Optional[int] = None,
        max_candles: Optional[int] = None
    ):
        """
        초기화

        Args:
            provider: AI 제공자 ("claude" 또는 "openai", None이면 settings에서 로드)
            api_key: API 키 (None이면 settings에서 로드)
            enable_cache: 캐시 활성화 여부 (None이면 settings에서 로드)
            cache_ttl_minutes: 캐시 유효 시간 (None이면 settings에서 로드)
            max_candles: 최대 캔들 수 (None이면 settings에서 로드)
        """
        # settings에서 기본값 로드
        self.provider = provider or settings.ai_provider
        self.enable_cache = enable_cache if enable_cache is not None else settings.ai_cache_enabled
        ttl = cache_ttl_minutes or settings.ai_cache_ttl_minutes
        candles = max_candles or settings.ai_max_candles

        # AI 클라이언트 초기화
        if self.provider == "claude":
            self.ai_client: BaseAIClient = ClaudeClient(api_key=api_key)
        elif self.provider == "openai":
            self.ai_client: BaseAIClient = OpenAIClient(api_key=api_key)
        else:
            raise ValueError(
                f"지원하지 않는 AI 제공자: {self.provider}. "
                "'claude' 또는 'openai'를 선택하세요."
            )

        self.summarizer = DataSummarizer(max_candles=candles)

        if self.enable_cache:
            self.cache = EvaluationCache(ttl_minutes=ttl)
        else:
            self.cache = None

        logger.info(
            f"AI 평가 서비스 초기화 완료 | "
            f"제공자: {self.provider} | "
            f"캐시: {self.enable_cache} | "
            f"TTL: {ttl}분 | "
            f"캔들 수: {candles}"
        )

    def evaluate_entry(
        self,
        symbol: str,
        ohlcv_data: List[OHLCV],
        strategy_signals: List[StrategySignalData],
        use_cache: bool = True
    ) -> Dict:
        """
        매수 시그널 AI 평가

        Args:
            symbol: 거래 심볼
            ohlcv_data: OHLCV 데이터
            strategy_signals: 전략 시그널 리스트
            use_cache: 캐시 사용 여부

        Returns:
            Dict: AI 평가 결과
        """
        # 데이터 요약
        indicators = self._extract_indicators(strategy_signals)
        summary_data = self.summarizer.summarize_ohlcv(
            symbol=symbol,
            ohlcv_data=ohlcv_data,
            indicators=indicators
        )

        # 전략 시그널 요약
        signal_summary = []
        for signal_data in strategy_signals:
            signal_summary.append({
                "strategy": signal_data.metadata.get("strategy", "Unknown"),
                "signal": signal_data.signal.value,
                "confidence": float(signal_data.confidence)
            })

        # 캐시 확인
        if use_cache and self.enable_cache and self.cache:
            context_hash = EvaluationCache.hash_context({
                "summary": summary_data,
                "signals": signal_summary
            })

            cached_result = self.cache.get(symbol, "entry", context_hash)
            if cached_result:
                logger.info(f"캐시된 평가 사용 | {symbol}")
                return cached_result

        # AI 평가
        result = self.ai_client.evaluate_entry_signal(
            symbol=symbol,
            summary_data=summary_data,
            strategy_signals=signal_summary
        )

        # 캐시 저장
        if use_cache and self.enable_cache and self.cache:
            self.cache.set(symbol, "entry", context_hash, result)

        return result

    def evaluate_exit(
        self,
        symbol: str,
        entry_price: Decimal,
        current_price: Decimal,
        holding_period: int,
        ohlcv_data: List[OHLCV],
        strategy_signals: List[StrategySignalData],
        use_cache: bool = True
    ) -> Dict:
        """
        매도 시그널 AI 평가

        Args:
            symbol: 거래 심볼
            entry_price: 진입 가격
            current_price: 현재 가격
            holding_period: 보유 기간
            ohlcv_data: OHLCV 데이터
            strategy_signals: 전략 시그널 리스트
            use_cache: 캐시 사용 여부

        Returns:
            Dict: AI 평가 결과
        """
        # 데이터 요약
        indicators = self._extract_indicators(strategy_signals)
        indicators["profit_loss_pct"] = ((current_price - entry_price) / entry_price) * 100

        summary_data = self.summarizer.summarize_ohlcv(
            symbol=symbol,
            ohlcv_data=ohlcv_data,
            indicators=indicators
        )

        # 전략 시그널 요약
        signal_summary = []
        for signal_data in strategy_signals:
            signal_summary.append({
                "strategy": signal_data.metadata.get("strategy", "Unknown"),
                "signal": signal_data.signal.value,
                "confidence": float(signal_data.confidence),
                "reason": signal_data.metadata.get("reason", "")
            })

        # 캐시 확인
        if use_cache and self.enable_cache and self.cache:
            context_hash = EvaluationCache.hash_context({
                "entry_price": float(entry_price),
                "current_price": float(current_price),
                "summary": summary_data,
                "signals": signal_summary
            })

            cached_result = self.cache.get(symbol, "exit", context_hash)
            if cached_result:
                logger.info(f"캐시된 평가 사용 | {symbol}")
                return cached_result

        # AI 평가
        result = self.ai_client.evaluate_exit_signal(
            symbol=symbol,
            entry_price=entry_price,
            current_price=current_price,
            holding_period=holding_period,
            summary_data=summary_data,
            strategy_signals=signal_summary
        )

        # 캐시 저장
        if use_cache and self.enable_cache and self.cache:
            self.cache.set(symbol, "exit", context_hash, result)

        return result

    def combine_signals(
        self,
        strategy_signal: StrategySignalData,
        ai_evaluation: Dict,
        strategy_weight: float = 0.6,
        ai_weight: float = 0.4
    ) -> StrategySignalData:
        """
        전략 시그널과 AI 평가 결합

        Args:
            strategy_signal: 전략 시그널
            ai_evaluation: AI 평가 결과
            strategy_weight: 전략 가중치
            ai_weight: AI 가중치

        Returns:
            StrategySignalData: 결합된 시그널
        """
        from core.enums import StrategySignal

        # AI 추천을 시그널로 변환
        ai_recommendation = ai_evaluation.get("recommendation", "hold")
        ai_confidence = Decimal(str(ai_evaluation.get("confidence", 50))) / 100

        # 시그널 매핑
        signal_map = {
            "buy": StrategySignal.BUY,
            "sell": StrategySignal.SELL,
            "hold": StrategySignal.HOLD
        }
        ai_signal = signal_map.get(ai_recommendation, StrategySignal.HOLD)

        # 불일치 확인
        if strategy_signal.signal != ai_signal:
            logger.warning(
                f"시그널 불일치 | 전략: {strategy_signal.signal.value} | "
                f"AI: {ai_signal.value}"
            )

        # 최종 확신도 계산 (가중 평균)
        final_confidence = (
            strategy_signal.confidence * Decimal(str(strategy_weight)) +
            ai_confidence * Decimal(str(ai_weight))
        )

        # 최종 시그널 결정 (확신도가 높은 쪽)
        if strategy_signal.confidence >= ai_confidence:
            final_signal = strategy_signal.signal
        else:
            final_signal = ai_signal

        # 메타데이터 업데이트
        combined_metadata = strategy_signal.metadata.copy()
        combined_metadata.update({
            "ai_evaluation": ai_evaluation,
            "strategy_confidence": float(strategy_signal.confidence),
            "ai_confidence": float(ai_confidence),
            "final_confidence": float(final_confidence),
            "combined": True
        })

        return StrategySignalData(
            signal=final_signal,
            confidence=final_confidence,
            price=strategy_signal.price,
            timestamp=strategy_signal.timestamp,
            indicators=strategy_signal.indicators,
            metadata=combined_metadata
        )

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
        return self.ai_client.batch_evaluate(evaluations)

    def invalidate_cache(self, symbol: Optional[str] = None):
        """
        캐시 무효화

        Args:
            symbol: 특정 심볼만 무효화 (None이면 전체)
        """
        if self.enable_cache and self.cache:
            self.cache.invalidate(symbol)

    def cleanup_cache(self):
        """만료된 캐시 정리"""
        if self.enable_cache and self.cache:
            self.cache.cleanup_expired()

    def get_cache_stats(self) -> Optional[Dict]:
        """캐시 통계 조회"""
        if self.enable_cache and self.cache:
            return self.cache.get_stats()
        return None

    def _extract_indicators(
        self,
        strategy_signals: List[StrategySignalData]
    ) -> Dict:
        """
        전략 시그널에서 지표 추출

        Args:
            strategy_signals: 전략 시그널 리스트

        Returns:
            Dict: 통합된 지표
        """
        indicators = {}

        for signal_data in strategy_signals:
            if signal_data.indicators:
                indicators.update(signal_data.indicators)

        return indicators

    def __repr__(self) -> str:
        cache_info = ""
        if self.enable_cache and self.cache:
            stats = self.cache.get_stats()
            cache_info = f", cache={stats['total_entries']}"

        return f"<AIEvaluationService(provider={self.provider}{cache_info})>"


if __name__ == "__main__":
    print("=== AI Evaluation Service 테스트 ===")

    from datetime import datetime, timedelta
    from core.enums import StrategySignal

    # 테스트 데이터 생성
    test_ohlcv = []
    base_price = Decimal("50000000")
    base_time = datetime.now()

    for i in range(30):
        price = base_price + Decimal(str(i * 100000))
        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=price,
            high=price + Decimal("100000"),
            low=price - Decimal("100000"),
            close=price,
            volume=Decimal("100")
        )
        test_ohlcv.append(candle)

    # 테스트 전략 시그널
    test_signals = [
        StrategySignalData(
            signal=StrategySignal.BUY,
            confidence=Decimal("0.75"),
            price=Decimal("52000000"),
            timestamp=datetime.now(),
            indicators={"rsi": Decimal("65.5"), "macd": Decimal("150000")},
            metadata={"strategy": "MACD", "reason": "골든 크로스"}
        ),
        StrategySignalData(
            signal=StrategySignal.HOLD,
            confidence=Decimal("0.60"),
            price=Decimal("52000000"),
            timestamp=datetime.now(),
            indicators={"rsi": Decimal("65.5")},
            metadata={"strategy": "RSI", "reason": "중립 구간"}
        )
    ]

    try:
        # 서비스 초기화
        service = AIEvaluationService(enable_cache=True)
        print(f"✓ {service}")

        # 매수 평가
        print("\n[매수 평가]")
        result = service.evaluate_entry(
            symbol="KRW-BTC",
            ohlcv_data=test_ohlcv,
            strategy_signals=test_signals
        )

        print(f"추천: {result.get('recommendation', 'N/A')}")
        print(f"확신도: {result.get('confidence', 0)}%")
        print(f"이유: {result.get('reasoning', 'N/A')}")

        # 시그널 결합
        print("\n[시그널 결합]")
        combined = service.combine_signals(
            strategy_signal=test_signals[0],
            ai_evaluation=result
        )

        print(f"최종 시그널: {combined.signal.value}")
        print(f"최종 확신도: {combined.confidence:.2%}")
        print(f"전략 확신도: {combined.metadata['strategy_confidence']:.2%}")
        print(f"AI 확신도: {combined.metadata['ai_confidence']:.2%}")

        # 캐시 통계
        if stats := service.get_cache_stats():
            print(f"\n[캐시 통계]")
            for key, value in stats.items():
                print(f"  {key}: {value}")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
