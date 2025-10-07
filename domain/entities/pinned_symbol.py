"""
지정 종목 엔티티
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from infrastructure.database.connection import Base


class PinnedSymbol(Base):
    """지정 종목 엔티티"""
    __tablename__ = "pinned_symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False, unique=True, index=True)
    market = Column(String, nullable=False)  # KRW, BTC
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self):
        return f"<PinnedSymbol(symbol={self.symbol}, market={self.market}, is_active={self.is_active})>"
