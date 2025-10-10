"""
BTS 환경설정 모듈

Pydantic Settings를 사용한 환경변수 관리
FastAPI와 Streamlit에서 공통으로 사용 가능
"""
from typing import Literal
from decimal import Decimal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    애플리케이션 전역 설정

    .env 파일에서 자동으로 환경변수 로드
    타입 검증 및 기본값 제공
    """

    # ===== Upbit API 설정 =====
    upbit_access_key: str = Field(
        default="",
        description="Upbit Access Key"
    )
    upbit_secret_key: str = Field(
        default="",
        description="Upbit Secret Key"
    )

    # ===== OpenAI API 설정 =====
    openai_api_key: str = Field(
        default="",
        description="OpenAI API Key"
    )
    openai_model: str = Field(
        default="gpt-4o",
        description=(
            "OpenAI 모델 버전\n"
            "사용 가능 모델:\n"
            "  - gpt-4o (추천, 최신, 빠름)\n"
            "  - gpt-4o-mini (빠르고 저렴)\n"
            "  - gpt-4-turbo (강력)\n"
            "  - gpt-3.5-turbo (가장 저렴)"
        )
    )
    openai_fallback_model: str = Field(
        default="gpt-4o-mini",
        description=(
            "Fallback 모델 (기본 모델 실패 시 자동 전환)\n"
            "빠르고 저렴한 gpt-4o-mini 권장"
        )
    )
    openai_max_tokens: int = Field(
        default=1024,
        description="OpenAI API 응답 최대 토큰 수"
    )

    # ===== Claude API 설정 (AI 평가 시스템) =====
    claude_api_key: str = Field(
        default="",
        description="Claude API Key for AI evaluation"
    )
    claude_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description=(
            "Claude 모델 버전\n"
            "사용 가능 모델:\n"
            "  - claude-3-5-sonnet-20241022 (추천, 최신)\n"
            "  - claude-3-5-haiku-20241022 (빠르고 저렴)\n"
            "  - claude-3-opus-20240229 (가장 강력)\n"
            "  - claude-3-sonnet-20240229\n"
            "  - claude-3-haiku-20240307"
        )
    )
    claude_fallback_model: str = Field(
        default="claude-3-5-haiku-20241022",
        description=(
            "Fallback 모델 (기본 모델 실패 시 자동 전환)\n"
            "빠르고 저렴한 haiku 모델 권장"
        )
    )
    claude_max_tokens: int = Field(
        default=1024,
        description="Claude API 응답 최대 토큰 수"
    )

    # ===== AI 평가 캐시 설정 =====
    ai_cache_enabled: bool = Field(
        default=True,
        description="AI 평가 결과 캐싱 활성화"
    )
    ai_cache_ttl_minutes: int = Field(
        default=15,
        description="AI 평가 캐시 유효 시간 (분)"
    )

    # ===== AI 데이터 요약 설정 =====
    ai_max_candles: int = Field(
        default=20,
        description="AI로 전송할 최대 캔들 개수 (토큰 최적화)"
    )

    # ===== AI 제공자 선택 =====
    ai_provider: Literal["claude", "openai"] = Field(
        default="claude",
        description=(
            "AI 제공자 선택\n"
            "  - claude: Anthropic Claude (추천)\n"
            "  - openai: OpenAI GPT"
        )
    )

    # ===== 트레이딩 모드 설정 =====
    trading_mode: Literal["paper", "live"] = Field(
        default="paper",
        description="거래 모드: paper(모의투자) 또는 live(실거래)"
    )

    # ===== 초기 자본금 설정 =====
    initial_balance: Decimal = Field(
        default=Decimal("10000000"),
        description="모의투자 초기 자본금 (KRW)"
    )

    # ===== 데이터베이스 설정 =====
    database_url: str = Field(
        default="sqlite:///./data/bts.db",
        description="데이터베이스 연결 URL"
    )

    # ===== 로깅 설정 =====
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        # default="INFO",
        default="DEBUG",
        description="로그 레벨"
    )
    log_file: str = Field(
        default="./logs/bts.log",
        description="로그 파일 경로"
    )

    # ===== 백테스팅 설정 =====
    backtest_slippage: Decimal = Field(
        default=Decimal("0.001"),
        description="백테스팅 슬리피지 (0.1%)"
    )
    backtest_commission: Decimal = Field(
        default=Decimal("0.0005"),
        description="백테스팅 수수료 (0.05%)"
    )

    # ===== 전략 설정 =====
    strategy_update_interval: int = Field(
        default=60,
        description="전략 업데이트 주기 (초)"
    )

    # ===== Pydantic Settings 설정 =====
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, v: str) -> str:
        """거래 모드 검증"""
        if v not in ["paper", "live"]:
            raise ValueError("trading_mode는 'paper' 또는 'live'여야 합니다")
        return v

    @field_validator("initial_balance")
    @classmethod
    def validate_initial_balance(cls, v: Decimal) -> Decimal:
        """초기 자본금 검증"""
        if v <= 0:
            raise ValueError("initial_balance는 0보다 커야 합니다")
        return v

    def is_paper_trading(self) -> bool:
        """모의투자 모드 여부"""
        return self.trading_mode == "paper"

    def is_live_trading(self) -> bool:
        """실거래 모드 여부"""
        return self.trading_mode == "live"

    def get_absolute_database_url(self) -> str:
        """절대 경로로 변환된 데이터베이스 URL 반환"""
        if self.database_url.startswith("sqlite:///"):
            # 상대 경로 추출
            rel_path = self.database_url.replace("sqlite:///", "")
            if rel_path.startswith("./"):
                # 프로젝트 루트 기준으로 절대 경로 생성
                project_root = Path(__file__).parent.parent
                abs_path = project_root / rel_path.lstrip("./")
                return f"sqlite:///{abs_path}"
        return self.database_url


# 전역 설정 인스턴스
settings = Settings()


# 설정 확인을 위한 헬퍼 함수
def get_settings() -> Settings:
    """
    설정 인스턴스 반환

    FastAPI 의존성 주입에서 사용:
        @app.get("/")
        def root(config: Settings = Depends(get_settings)):
            return {"mode": config.trading_mode}
    """
    return settings


if __name__ == "__main__":
    # 설정 테스트
    print("=== BTS 설정 정보 ===")
    print(f"거래 모드: {settings.trading_mode}")
    print(f"초기 자본금: {settings.initial_balance:,.0f} KRW")
    print(f"데이터베이스: {settings.database_url}")
    print(f"로그 레벨: {settings.log_level}")
    print(f"Upbit API 키 설정: {'✓' if settings.upbit_access_key else '✗'}")
    print(f"OpenAI API 키 설정: {'✓' if settings.openai_api_key else '✗'}")
    print(f"Claude API 키 설정: {'✓' if settings.claude_api_key else '✗'}")
    print(f"\n=== AI 설정 ===")
    print(f"AI 제공자: {settings.ai_provider}")
    print(f"AI 캐시 활성화: {settings.ai_cache_enabled}")
    print(f"AI 캐시 TTL: {settings.ai_cache_ttl_minutes}분")
    if settings.ai_provider == "claude":
        print(f"Claude 모델: {settings.claude_model}")
        print(f"Claude Fallback: {settings.claude_fallback_model}")
    else:
        print(f"OpenAI 모델: {settings.openai_model}")
        print(f"OpenAI Fallback: {settings.openai_fallback_model}")
