"""
BTS Claude API Client

Claude API 통합 클라이언트
"""
from typing import Dict, List, Optional
from decimal import Decimal
import json
import os

try:
    import anthropic
except ImportError:
    anthropic = None

from config.settings import settings
from infrastructure.ai.base_ai_client import BaseAIClient
from utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeClient(BaseAIClient):
    """
    Claude API 클라이언트

    전략 평가를 위한 AI 분석 제공
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Claude 클라이언트 초기화

        Args:
            api_key: Claude API 키 (None이면 settings에서 로드)
            model: Claude 모델 (None이면 settings에서 로드)
            fallback_model: Fallback 모델 (None이면 settings에서 로드)
            max_tokens: 최대 토큰 수 (None이면 settings에서 로드)
        """
        if anthropic is None:
            raise ImportError(
                "anthropic 패키지가 설치되지 않았습니다. "
                "pip install anthropic 으로 설치하세요."
            )

        # settings에서 기본값 로드
        self.api_key = api_key or settings.claude_api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Claude API 키가 설정되지 않았습니다. "
                ".env 파일에 CLAUDE_API_KEY를 설정하거나 인자로 전달하세요."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model or settings.claude_model
        self.fallback_model = fallback_model or settings.claude_fallback_model
        self.max_tokens = max_tokens or settings.claude_max_tokens

        logger.info(
            f"Claude 클라이언트 초기화 완료 | "
            f"모델: {self.model} | "
            f"Fallback: {self.fallback_model} | "
            f"최대 토큰: {self.max_tokens}"
        )

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
        """
        prompt = self._build_entry_prompt(symbol, summary_data, strategy_signals)

        # 기본 모델로 시도
        result = self._call_api_with_fallback(prompt, "entry", symbol)
        return result

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
        profit_pct = ((current_price - entry_price) / entry_price) * 100

        prompt = self._build_exit_prompt(
            symbol,
            entry_price,
            current_price,
            profit_pct,
            holding_period,
            summary_data,
            strategy_signals
        )

        # 기본 모델로 시도
        result = self._call_api_with_fallback(prompt, "exit", symbol)
        return result

    def _call_api_with_fallback(
        self,
        prompt: str,
        eval_type: str,
        symbol: str
    ) -> Dict:
        """
        Fallback을 지원하는 API 호출

        Args:
            prompt: 평가 프롬프트
            eval_type: 평가 타입 (entry|exit)
            symbol: 거래 심볼

        Returns:
            Dict: 평가 결과
        """
        models_to_try = [self.model, self.fallback_model]

        for idx, model in enumerate(models_to_try):
            try:
                is_fallback = idx > 0

                if is_fallback:
                    logger.warning(
                        f"Fallback 모델로 재시도 | {symbol} | "
                        f"{self.model} → {model}"
                    )

                response = self.client.messages.create(
                    model=model,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                # 응답 파싱
                content = response.content[0].text
                result = json.loads(content)

                # 성공 로그
                model_info = f"(Fallback: {model})" if is_fallback else f"(모델: {model})"
                logger.info(
                    f"{eval_type.capitalize()} 평가 완료 | {symbol} | "
                    f"추천: {result.get('recommendation', 'N/A')} | "
                    f"확신도: {result.get('confidence', 0)}% | "
                    f"{model_info}"
                )

                # Fallback 사용 여부 메타데이터에 추가
                if is_fallback:
                    result["_fallback_used"] = True
                    result["_model_used"] = model

                return result

            except json.JSONDecodeError as e:
                logger.error(f"AI 응답 파싱 실패 ({model}): {e}")
                if idx == len(models_to_try) - 1:
                    # 모든 모델 시도 실패
                    return {
                        "recommendation": "hold",
                        "confidence": 50,
                        "reasoning": "AI 응답 파싱 실패 (모든 모델)",
                        "warnings": "JSON 형식 오류"
                    }
                # 다음 모델로 계속

            except Exception as e:
                logger.error(f"Claude API 호출 실패 ({model}): {e}")
                if idx == len(models_to_try) - 1:
                    # 모든 모델 시도 실패
                    return {
                        "recommendation": "hold",
                        "confidence": 50,
                        "reasoning": f"API 호출 실패 (모든 모델): {str(e)}",
                        "warnings": "API 호출 오류"
                    }
                # 다음 모델로 계속

        # 이론상 여기 도달 불가
        return {
            "recommendation": "hold",
            "confidence": 50,
            "reasoning": "알 수 없는 오류",
            "warnings": "평가 실패"
        }

    def _build_entry_prompt(
        self,
        symbol: str,
        summary_data: Dict,
        strategy_signals: List[Dict]
    ) -> str:
        """매수 평가 프롬프트 생성"""
        return f"""당신은 암호화폐 전문 트레이더입니다.
다음 데이터를 분석하여 매수 시그널을 평가해주세요.

## 심볼
{symbol}

## 시장 데이터
{json.dumps(summary_data, indent=2, ensure_ascii=False)}

## 전략 시그널
{json.dumps(strategy_signals, indent=2, ensure_ascii=False)}

다음 형식의 JSON으로만 답변하세요:
{{
  "recommendation": "buy|sell|hold",
  "confidence": 75,
  "reasoning": "간결한 분석 이유 (2-3문장)",
  "warnings": "주의사항 또는 리스크 (선택사항)"
}}

중요:
- recommendation: buy(매수), sell(매도), hold(보류) 중 하나
- confidence: 0-100 사이 정수
- reasoning: 핵심만 간결하게
- 반드시 JSON 형식으로만 응답
"""

    def _build_exit_prompt(
        self,
        symbol: str,
        entry_price: Decimal,
        current_price: Decimal,
        profit_pct: Decimal,
        holding_period: int,
        summary_data: Dict,
        strategy_signals: List[Dict]
    ) -> str:
        """매도 평가 프롬프트 생성"""
        return f"""당신은 암호화폐 전문 트레이더입니다.
다음 보유 포지션의 매도 시점을 평가해주세요.

## 심볼
{symbol}

## 포지션 정보
- 진입가: {entry_price:,.0f} KRW
- 현재가: {current_price:,.0f} KRW
- 손익률: {profit_pct:.2f}%
- 보유 기간: {holding_period}시간

## 시장 데이터
{json.dumps(summary_data, indent=2, ensure_ascii=False)}

## 매도 전략 시그널
{json.dumps(strategy_signals, indent=2, ensure_ascii=False)}

다음 형식의 JSON으로만 답변하세요:
{{
  "recommendation": "sell|hold",
  "confidence": 75,
  "reasoning": "간결한 분석 이유 (2-3문장)",
  "suggested_action": "익절|손절|추가 보유|부분 매도 등"
}}

중요:
- recommendation: sell(매도), hold(보류) 중 하나
- confidence: 0-100 사이 정수
- reasoning: 핵심만 간결하게
- 반드시 JSON 형식으로만 응답
"""

    def batch_evaluate(
        self,
        evaluations: List[Dict]
    ) -> List[Dict]:
        """
        배치 평가 (여러 종목 동시 평가)

        Args:
            evaluations: 평가 요청 리스트

        Returns:
            List[Dict]: 평가 결과 리스트
        """
        results = []

        for eval_request in evaluations:
            eval_type = eval_request.get("type", "entry")

            if eval_type == "entry":
                result = self.evaluate_entry_signal(
                    symbol=eval_request["symbol"],
                    summary_data=eval_request["summary_data"],
                    strategy_signals=eval_request["strategy_signals"]
                )
            else:  # exit
                result = self.evaluate_exit_signal(
                    symbol=eval_request["symbol"],
                    entry_price=eval_request["entry_price"],
                    current_price=eval_request["current_price"],
                    holding_period=eval_request.get("holding_period", 0),
                    summary_data=eval_request["summary_data"],
                    strategy_signals=eval_request["strategy_signals"]
                )

            results.append(result)

        return results

    def __repr__(self) -> str:
        return f"<ClaudeClient(model={self.model}, max_tokens={self.max_tokens})>"


if __name__ == "__main__":
    print("=== Claude Client 테스트 ===")

    # API 키 확인
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("❌ CLAUDE_API_KEY 환경변수가 설정되지 않았습니다")
        print("   .env 파일에 CLAUDE_API_KEY를 설정하세요")
        exit(1)

    try:
        # 클라이언트 초기화
        client = ClaudeClient()
        print(f"✓ Claude 클라이언트 초기화 성공")
        print(f"  모델: {client.model}")

        # 테스트 데이터
        summary_data = {
            "symbol": "KRW-BTC",
            "current_price": 85000000,
            "price_change_24h": 2.5,
            "indicators": {
                "rsi": 65.5,
                "macd": 150000,
                "bb_position": "middle"
            }
        }

        strategy_signals = [
            {"strategy": "MACD", "signal": "buy", "confidence": 0.75},
            {"strategy": "RSI", "signal": "hold", "confidence": 0.60}
        ]

        # 매수 평가 테스트
        print("\n[매수 평가 테스트]")
        result = client.evaluate_entry_signal(
            symbol="KRW-BTC",
            summary_data=summary_data,
            strategy_signals=strategy_signals
        )

        print(f"\n결과:")
        print(f"  추천: {result.get('recommendation', 'N/A')}")
        print(f"  확신도: {result.get('confidence', 0)}%")
        print(f"  이유: {result.get('reasoning', 'N/A')}")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
