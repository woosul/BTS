"""
BTS 환경설정 모듈

Pydantic Settings를 사용한 환경변수 관리
FastAPI와 Streamlit에서 공통으로 사용 가능
"""
from typing import Literal
from decimal import Decimal
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
        default="INFO",
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
