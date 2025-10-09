"""
필터링된 종목 Repository
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import FilteredSymbolORM
from domain.entities.filtered_symbol import FilteredSymbol
from utils.logger import logger


class FilteredSymbolRepository(BaseRepository[FilteredSymbolORM]):
    """필터링된 종목 Repository"""
    
    def __init__(self, db: Session):
        super().__init__(FilteredSymbolORM, db)
    
    def save_symbols(self, symbols: List[str], profile_name: Optional[str] = None) -> bool:
        """
        필터링된 종목 목록 저장
        기존 데이터를 모두 삭제하고 새로 저장
        
        Args:
            symbols: 종목 코드 리스트
            profile_name: 필터 프로파일 명 (optional)
            
        Returns:
            성공 여부
        """
        try:
            # 1. 기존 데이터 모두 삭제
            deleted_count = self.db.query(FilteredSymbolORM).delete()
            logger.info(f"기존 필터링 결과 삭제: {deleted_count}개")
            
            # 2. 새로운 데이터 저장
            filtered_at = datetime.now()
            new_symbols = [
                FilteredSymbolORM(
                    symbol=symbol,
                    profile_name=profile_name,
                    filtered_at=filtered_at
                )
                for symbol in symbols
            ]
            
            self.db.add_all(new_symbols)
            self.db.commit()
            
            profile_info = f" (프로파일: {profile_name})" if profile_name else ""
            logger.info(f"필터링 결과 저장 완료: {len(symbols)}개 종목{profile_info}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"필터링 결과 저장 실패: {e}")
            return False
    
    def get_latest_symbols(self) -> List[str]:
        """
        저장된 최신 필터링 결과 조회
        
        Returns:
            종목 코드 리스트
        """
        try:
            symbols = self.db.query(FilteredSymbolORM.symbol)\
                .order_by(FilteredSymbolORM.filtered_at.desc())\
                .all()
            
            result = [symbol[0] for symbol in symbols]
            logger.info(f"저장된 필터링 결과 조회: {len(result)}개 종목")
            return result
            
        except Exception as e:
            logger.error(f"필터링 결과 조회 실패: {e}")
            return []
    
    def get_latest_filtered_at(self) -> Optional[datetime]:
        """
        마지막 필터링 시각 조회
        
        Returns:
            마지막 필터링 시각 (없으면 None)
        """
        try:
            result = self.db.query(FilteredSymbolORM.filtered_at)\
                .order_by(FilteredSymbolORM.filtered_at.desc())\
                .first()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"마지막 필터링 시각 조회 실패: {e}")
            return None
    
    def get_profile_name(self) -> Optional[str]:
        """
        저장된 필터링 결과의 프로파일명 조회
        
        Returns:
            프로파일명 (없으면 None)
        """
        try:
            result = self.db.query(FilteredSymbolORM.profile_name)\
                .order_by(FilteredSymbolORM.filtered_at.desc())\
                .first()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"프로파일명 조회 실패: {e}")
            return None
    
    def clear_all(self) -> bool:
        """
        모든 필터링 결과 삭제
        
        Returns:
            성공 여부
        """
        try:
            deleted_count = self.db.query(FilteredSymbolORM).delete()
            self.db.commit()
            
            logger.info(f"필터링 결과 전체 삭제: {deleted_count}개")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"필터링 결과 삭제 실패: {e}")
            return False
    
    def count(self) -> int:
        """
        저장된 종목 수 조회
        
        Returns:
            종목 수
        """
        try:
            return self.db.query(FilteredSymbolORM).count()
        except Exception as e:
            logger.error(f"종목 수 조회 실패: {e}")
            return 0
