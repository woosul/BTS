"""
필터링된 종목 엔티티
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FilteredSymbol(BaseModel):
    """필터링된 종목 엔티티"""
    
    id: Optional[int] = None
    symbol: str = Field(..., description="종목 코드 (예: KRW-BTC)")
    profile_name: Optional[str] = Field(None, description="필터 프로파일명")
    filtered_at: datetime = Field(default_factory=datetime.now, description="필터링 시각")
    
    class Config:
        from_attributes = True
