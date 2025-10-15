"""
BTS 마켓 인덱스 Repository

시장 지수 데이터 접근 계층
"""
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import MarketIndexORM
from domain.entities.market_index import MarketIndex
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketIndexRepository(BaseRepository[MarketIndexORM]):
    """마켓 인덱스 Repository"""

    def __init__(self, db: Session):
        super().__init__(MarketIndexORM, db)

    def get_by_code(self, code: str) -> Optional[MarketIndexORM]:
        """
        코드로 지수 조회

        Args:
            code: 지수 코드

        Returns:
            Optional[MarketIndexORM]: 지수 또는 None
        """
        return self.get_by_field("code", code)

    def get_by_type(self, index_type: str) -> List[MarketIndexORM]:
        """
        타입으로 지수 목록 조회

        Args:
            index_type: 지수 타입 (upbit, global, coin, usd)

        Returns:
            List[MarketIndexORM]: 지수 목록
        """
        return self.filter_by(index_type=index_type)

    def upsert_index(
        self,
        index_type: str,
        code: str,
        name: str,
        value: Decimal,
        change: Decimal = Decimal("0"),
        change_rate: Decimal = Decimal("0"),
        extra_data: Optional[dict] = None,
        ttl_seconds: int = 300
    ) -> MarketIndexORM:
        """
        지수 업데이트 또는 생성 (Upsert)

        Args:
            index_type: 지수 타입
            code: 지수 코드
            name: 지수 이름
            value: 현재 값
            change: 변동값
            change_rate: 변동률
            extra_data: 추가 데이터
            ttl_seconds: TTL (초)

        Returns:
            MarketIndexORM: 지수
        """
        existing = self.get_by_code(code)

        extra_json = json.dumps(extra_data) if extra_data else None

        if existing:
            # 업데이트
            index = self.update(
                existing.id,
                index_type=index_type,
                name=name,
                value=value,
                change=change,
                change_rate=change_rate,
                extra_data=extra_json,
                ttl_seconds=ttl_seconds,
                updated_at=datetime.now()
            )
            logger.debug(f"지수 업데이트: {code} = {value:,.2f} ({change_rate:+.2f}%)")
        else:
            # 생성
            index = self.create(
                index_type=index_type,
                code=code,
                name=name,
                value=value,
                change=change,
                change_rate=change_rate,
                extra_data=extra_json,
                ttl_seconds=ttl_seconds
            )
            logger.info(f"지수 생성: {code} = {value:,.2f}")

        return index

    def get_valid_indices(self, index_type: Optional[str] = None) -> List[MarketIndexORM]:
        """
        유효한 지수 목록 조회 (TTL 내)

        Args:
            index_type: 지수 타입 (None이면 전체)

        Returns:
            List[MarketIndexORM]: 유효한 지수 목록
        """
        # TTL을 고려하여 만료되지 않은 지수만 조회
        if index_type:
            indices = self.get_by_type(index_type)
        else:
            indices = self.get_all()

        valid_indices = []
        for index in indices:
            expiry_time = index.updated_at + timedelta(seconds=index.ttl_seconds)
            if datetime.now() <= expiry_time:
                valid_indices.append(index)

        return valid_indices

    def get_expired_indices(self, index_type: Optional[str] = None) -> List[MarketIndexORM]:
        """
        만료된 지수 목록 조회

        Args:
            index_type: 지수 타입 (None이면 전체)

        Returns:
            List[MarketIndexORM]: 만료된 지수 목록
        """
        if index_type:
            indices = self.get_by_type(index_type)
        else:
            indices = self.get_all()

        expired_indices = []
        for index in indices:
            expiry_time = index.updated_at + timedelta(seconds=index.ttl_seconds)
            if datetime.now() > expiry_time:
                expired_indices.append(index)

        return expired_indices

    def delete_expired_indices(self) -> int:
        """
        만료된 지수 삭제

        Returns:
            int: 삭제된 개수
        """
        expired = self.get_expired_indices()
        count = 0

        for index in expired:
            self.delete(index.id)
            count += 1
            logger.debug(f"만료된 지수 삭제: {index.code}")

        if count > 0:
            logger.info(f"만료된 지수 {count}개 삭제 완료")

        return count

    def to_entity(self, orm: MarketIndexORM) -> MarketIndex:
        """
        ORM을 엔티티로 변환

        Args:
            orm: ORM 인스턴스

        Returns:
            MarketIndex: 엔티티
        """
        extra_data = None
        if orm.extra_data:
            try:
                extra_data = json.loads(orm.extra_data)
            except json.JSONDecodeError:
                logger.warning(f"지수 {orm.code}의 extra_data JSON 파싱 실패")
                extra_data = {}

        return MarketIndex(
            id=orm.id,
            index_type=orm.index_type,
            code=orm.code,
            name=orm.name,
            value=orm.value,
            change=orm.change,
            change_rate=orm.change_rate,
            extra_data=extra_data,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            ttl_seconds=orm.ttl_seconds
        )

    def bulk_upsert(self, indices: List[dict]) -> List[MarketIndexORM]:
        """
        여러 지수 일괄 업데이트/생성

        Args:
            indices: 지수 데이터 리스트
                [
                    {
                        'index_type': 'upbit',
                        'code': 'ubci',
                        'name': '업비트 종합 지수',
                        'value': 18000.50,
                        'change_rate': 0.84,
                        ...
                    },
                    ...
                ]

        Returns:
            List[MarketIndexORM]: 생성/업데이트된 지수 목록
        """
        results = []

        for index_data in indices:
            index = self.upsert_index(
                index_type=index_data['index_type'],
                code=index_data['code'],
                name=index_data['name'],
                value=Decimal(str(index_data['value'])),
                change=Decimal(str(index_data.get('change', 0))),
                change_rate=Decimal(str(index_data.get('change_rate', 0))),
                extra_data=index_data.get('extra_data'),
                ttl_seconds=index_data.get('ttl_seconds', 300)
            )
            results.append(index)

        logger.info(f"지수 일괄 업데이트 완료: {len(results)}개")
        return results


if __name__ == "__main__":
    from infrastructure.database.connection import get_db_session

    print("=== 마켓 인덱스 Repository 테스트 ===\n")

    with get_db_session() as db:
        repo = MarketIndexRepository(db)

        # 1. 업비트 지수 생성
        print("1. 업비트 지수 생성")
        ubci = repo.upsert_index(
            index_type="upbit",
            code="ubci",
            name="업비트 종합 지수",
            value=Decimal("18000.50"),
            change=Decimal("150.30"),
            change_rate=Decimal("0.84"),
            ttl_seconds=300
        )
        print(f"   {ubci}\n")

        # 2. 같은 지수 업데이트
        print("2. 지수 업데이트")
        ubci_updated = repo.upsert_index(
            index_type="upbit",
            code="ubci",
            name="업비트 종합 지수",
            value=Decimal("18100.00"),
            change=Decimal("250.30"),
            change_rate=Decimal("1.40")
        )
        print(f"   {ubci_updated}\n")

        # 3. 여러 지수 일괄 생성
        print("3. 여러 지수 일괄 생성")
        indices_data = [
            {
                'index_type': 'upbit',
                'code': 'ubmi',
                'name': '업비트 알트코인 지수',
                'value': 15000.20,
                'change_rate': 1.20
            },
            {
                'index_type': 'upbit',
                'code': 'ub10',
                'name': '업비트 10',
                'value': 20000.50,
                'change_rate': -0.50
            },
            {
                'index_type': 'global',
                'code': 'total_market_cap',
                'name': '총 시가총액',
                'value': 3500000000000,
                'extra_data': {'currency': 'USD'}
            }
        ]
        results = repo.bulk_upsert(indices_data)
        print(f"   생성된 지수: {len(results)}개\n")

        # 4. 타입별 조회
        print("4. 업비트 지수 조회")
        upbit_indices = repo.get_by_type("upbit")
        for idx in upbit_indices:
            print(f"   {idx.code}: {idx.value:,.2f} ({idx.change_rate:+.2f}%)")
        print()

        # 5. 유효한 지수 조회
        print("5. 유효한 지수 조회")
        valid = repo.get_valid_indices()
        print(f"   유효한 지수: {len(valid)}개\n")

        # 6. 코드로 조회
        print("6. 코드로 조회")
        ubci_found = repo.get_by_code("ubci")
        if ubci_found:
            print(f"   {ubci_found.code}: {ubci_found.value:,.2f}")
            entity = repo.to_entity(ubci_found)
            print(f"   엔티티 변환: {entity}\n")
