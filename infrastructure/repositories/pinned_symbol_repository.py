"""
지정 종목 리포지토리
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from domain.entities.pinned_symbol import PinnedSymbol


class PinnedSymbolRepository:
    """지정 종목 리포지토리"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_active(self, market: Optional[str] = None) -> List[PinnedSymbol]:
        """활성 지정 종목 조회"""
        query = self.db.query(PinnedSymbol).filter(PinnedSymbol.is_active == True)
        if market:
            query = query.filter(PinnedSymbol.market == market)
        return query.all()

    def get_by_symbol(self, symbol: str) -> Optional[PinnedSymbol]:
        """심볼로 지정 종목 조회"""
        return self.db.query(PinnedSymbol).filter(PinnedSymbol.symbol == symbol).first()

    def add(self, symbol: str, market: str) -> PinnedSymbol:
        """지정 종목 추가"""
        existing = self.get_by_symbol(symbol)
        if existing:
            # 이미 존재하면 활성화
            existing.is_active = True
            existing.market = market
            self.db.commit()
            return existing
        else:
            # 새로 추가
            pinned = PinnedSymbol(symbol=symbol, market=market)
            self.db.add(pinned)
            self.db.commit()
            self.db.refresh(pinned)
            return pinned

    def remove(self, symbol: str) -> bool:
        """지정 종목 제거 (비활성화)"""
        pinned = self.get_by_symbol(symbol)
        if pinned:
            pinned.is_active = False
            self.db.commit()
            return True
        return False

    def delete(self, symbol: str) -> bool:
        """지정 종목 완전 삭제"""
        pinned = self.get_by_symbol(symbol)
        if pinned:
            self.db.delete(pinned)
            self.db.commit()
            return True
        return False

    def clear_all(self, market: Optional[str] = None) -> int:
        """모든 지정 종목 비활성화"""
        query = self.db.query(PinnedSymbol).filter(PinnedSymbol.is_active == True)
        if market:
            query = query.filter(PinnedSymbol.market == market)
        count = query.count()
        query.update({"is_active": False})
        self.db.commit()
        return count
