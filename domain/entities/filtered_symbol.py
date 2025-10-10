"""
필터링된 종목 엔티티
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class FilteredSymbol(BaseModel):
    """필터링된 종목 엔티티"""
    
    id: Optional[int] = None
    symbol: str = Field(..., description="종목 코드 (예: KRW-BTC)")
    profile_name: Optional[str] = Field(None, description="필터 프로파일명")
    filtered_at: datetime = Field(default_factory=datetime.now, description="필터링 시각")
    
    # 필터링 결과 상세 데이터
    korean_name: Optional[str] = Field(None, description="종목 한글명")
    trading_value: Optional[Decimal] = Field(None, description="거래대금")
    market_cap: Optional[Decimal] = Field(None, description="시가총액")
    listing_days: Optional[int] = Field(None, description="상장기간 (일)")
    current_price: Optional[Decimal] = Field(None, description="현재가")
    volatility: Optional[Decimal] = Field(None, description="변동성 (%)")
    spread: Optional[Decimal] = Field(None, description="스프레드 (%)")
    note: Optional[str] = Field(None, description="비고")
    
    class Config:
        from_attributes = True
