"""
필터 프로파일 엔티티

스크리닝 전 종목 필터링을 위한 프로파일 관리
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FilterCondition(BaseModel):
    """개별 필터 조건"""
    enabled: bool = Field(default=True, description="필터 사용 여부")
    
    # 1) 상장폐지 필터
    exclude_delisting: bool = Field(default=True, description="상장폐지 예정 종목 제외")
    
    # 2) 거래정지 필터
    exclude_suspended: bool = Field(default=True, description="거래정지 종목 제외")
    
    # 3) 거래대금 필터
    min_trading_value: Optional[float] = Field(default=None, description="최소 거래대금 (KRW)")
    
    # 4) 시가총액 필터
    min_market_cap: Optional[float] = Field(default=None, description="최소 시가총액 (KRW)")
    max_market_cap: Optional[float] = Field(default=None, description="최대 시가총액 (KRW)")
    
    # 5) 상장기간 필터
    min_listing_days: Optional[int] = Field(default=None, description="최소 상장 일수")
    
    # 6) 가격범위 필터
    min_price: Optional[float] = Field(default=None, description="최소 가격 (KRW)")
    max_price: Optional[float] = Field(default=None, description="최대 가격 (KRW)")
    
    # 7) 변동성 필터
    min_volatility: Optional[float] = Field(default=None, description="최소 변동성 (%, 7일 기준)")
    max_volatility: Optional[float] = Field(default=None, description="최대 변동성 (%, 7일 기준)")
    
    # 8) 스프레드 필터
    max_spread: Optional[float] = Field(default=None, description="최대 스프레드 (%)")


class FilterProfile(BaseModel):
    """필터 프로파일"""
    id: Optional[int] = None
    name: str = Field(..., description="프로파일 이름")
    description: Optional[str] = Field(default=None, description="프로파일 설명")
    market: str = Field(..., description="대상 시장 (KRW/BTC)")
    
    # 필터 조건
    conditions: FilterCondition = Field(default_factory=FilterCondition)
    
    # 메타데이터
    is_active: bool = Field(default=True, description="활성화 여부")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class FilterProfileCreate(BaseModel):
    """필터 프로파일 생성 DTO"""
    name: str
    description: Optional[str] = None
    market: str
    conditions: FilterCondition = Field(default_factory=FilterCondition)
    is_active: bool = True


class FilterProfileUpdate(BaseModel):
    """필터 프로파일 수정 DTO"""
    name: Optional[str] = None
    description: Optional[str] = None
    market: Optional[str] = None
    conditions: Optional[FilterCondition] = None
    is_active: Optional[bool] = None


class FilterStats(BaseModel):
    """필터링 통계"""
    stage_name: str
    symbols_before: int
    symbols_after: int
    filtered_count: int
    filtered_percentage: float
    execution_time_ms: float
