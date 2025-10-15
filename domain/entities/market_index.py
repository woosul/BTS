"""
BTS 마켓 인덱스 도메인 엔티티

시장 지수 데이터를 캐싱하여 빠른 조회 제공
"""
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal

from utils.logger import get_logger

logger = get_logger(__name__)


class MarketIndex:
    """
    마켓 인덱스 도메인 엔티티

    비즈니스 규칙:
    - 각 지수는 고유한 code를 가짐
    - 데이터는 일정 시간 후 만료됨 (TTL)
    - 업데이트 시 이전 값과 비교하여 변동 계산
    """

    # 지수 타입
    TYPE_UPBIT = "upbit"  # 업비트 지수 (UBCI, UBMI, UB10, UB30)
    TYPE_GLOBAL = "global"  # 글로벌 지수 (시가총액, 거래량 등)
    TYPE_COIN = "coin"  # 개별 코인 지수
    TYPE_USD = "usd"  # USD/KRW 환율

    # TTL (초 단위)
    DEFAULT_TTL = 300  # 5분

    def __init__(
        self,
        id: Optional[int] = None,
        index_type: str = TYPE_UPBIT,
        code: str = "",
        name: str = "",
        value: Decimal = Decimal("0"),
        change: Decimal = Decimal("0"),
        change_rate: Decimal = Decimal("0"),
        extra_data: Optional[dict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        ttl_seconds: int = DEFAULT_TTL,
    ):
        self.id = id
        self.index_type = index_type
        self.code = code
        self.name = name
        self.value = value
        self.change = change
        self.change_rate = change_rate
        self.extra_data = extra_data or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """
        데이터 만료 여부 확인

        Returns:
            bool: 만료되었으면 True
        """
        if not self.updated_at:
            return True

        expiry_time = self.updated_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time

    def get_remaining_ttl(self) -> int:
        """
        남은 TTL 시간 (초)

        Returns:
            int: 남은 시간 (초), 만료되었으면 0
        """
        if self.is_expired():
            return 0

        expiry_time = self.updated_at + timedelta(seconds=self.ttl_seconds)
        remaining = (expiry_time - datetime.now()).total_seconds()
        return max(0, int(remaining))

    def update_value(
        self,
        new_value: Decimal,
        calculate_change: bool = True
    ) -> None:
        """
        값 업데이트 및 변동 계산

        Args:
            new_value: 새로운 값
            calculate_change: 변동 계산 여부
        """
        if calculate_change and self.value > 0:
            old_value = self.value
            self.change = new_value - old_value
            self.change_rate = (self.change / old_value) * 100

        self.value = new_value
        self.updated_at = datetime.now()

        logger.debug(
            f"지수 업데이트 | {self.code} | "
            f"값: {new_value:,.2f} | "
            f"변동: {self.change_rate:+.2f}%"
        )

    def update_from_dict(self, data: dict) -> None:
        """
        딕셔너리로부터 데이터 업데이트

        Args:
            data: 업데이트할 데이터 {'value': ..., 'change': ..., 'change_rate': ...}
        """
        if 'value' in data:
            self.value = Decimal(str(data['value']))

        if 'change' in data:
            self.change = Decimal(str(data['change']))

        if 'change_rate' in data:
            self.change_rate = Decimal(str(data['change_rate']))

        if 'extra_data' in data:
            self.extra_data.update(data['extra_data'])

        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """
        딕셔너리로 변환

        Returns:
            dict: 지수 데이터
        """
        return {
            'id': self.id,
            'index_type': self.index_type,
            'code': self.code,
            'name': self.name,
            'value': float(self.value),
            'change': float(self.change),
            'change_rate': float(self.change_rate),
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'ttl_seconds': self.ttl_seconds,
            'is_expired': self.is_expired(),
            'remaining_ttl': self.get_remaining_ttl(),
        }

    @classmethod
    def create_upbit_index(
        cls,
        code: str,
        name: str,
        value: Decimal,
        change: Decimal = Decimal("0"),
        change_rate: Decimal = Decimal("0")
    ) -> "MarketIndex":
        """
        업비트 지수 생성

        Args:
            code: 지수 코드 (ubci, ubmi, ub10, ub30)
            name: 지수 이름
            value: 현재 값
            change: 변동값
            change_rate: 변동률

        Returns:
            MarketIndex: 업비트 지수 엔티티
        """
        return cls(
            index_type=cls.TYPE_UPBIT,
            code=code,
            name=name,
            value=value,
            change=change,
            change_rate=change_rate,
            ttl_seconds=300  # 5분
        )

    @classmethod
    def create_global_index(
        cls,
        code: str,
        name: str,
        value: Decimal,
        extra_data: Optional[dict] = None
    ) -> "MarketIndex":
        """
        글로벌 지수 생성

        Args:
            code: 지수 코드 (market_cap, volume, btc_dominance 등)
            name: 지수 이름
            value: 현재 값
            extra_data: 추가 데이터

        Returns:
            MarketIndex: 글로벌 지수 엔티티
        """
        return cls(
            index_type=cls.TYPE_GLOBAL,
            code=code,
            name=name,
            value=value,
            extra_data=extra_data,
            ttl_seconds=300  # 5분
        )

    @classmethod
    def create_coin_index(
        cls,
        symbol: str,
        price: Decimal,
        change_rate: Decimal,
        extra_data: Optional[dict] = None
    ) -> "MarketIndex":
        """
        개별 코인 지수 생성

        Args:
            symbol: 코인 심볼
            price: 현재가
            change_rate: 변동률
            extra_data: 추가 데이터 (시가총액 등)

        Returns:
            MarketIndex: 코인 지수 엔티티
        """
        return cls(
            index_type=cls.TYPE_COIN,
            code=symbol,
            name=symbol,
            value=price,
            change_rate=change_rate,
            extra_data=extra_data,
            ttl_seconds=60  # 1분 (코인은 더 자주 업데이트)
        )

    @classmethod
    def create_usd_rate(
        cls,
        rate: Decimal,
        change_rate: Decimal = Decimal("0")
    ) -> "MarketIndex":
        """
        USD/KRW 환율 생성

        Args:
            rate: 환율
            change_rate: 변동률

        Returns:
            MarketIndex: 환율 엔티티
        """
        return cls(
            index_type=cls.TYPE_USD,
            code="usd_krw",
            name="USD/KRW",
            value=rate,
            change_rate=change_rate,
            ttl_seconds=300  # 5분
        )

    def __repr__(self) -> str:
        status = "만료" if self.is_expired() else f"유효({self.get_remaining_ttl()}초)"
        return (
            f"<MarketIndex(type={self.index_type}, code={self.code}, "
            f"value={self.value:,.2f}, change_rate={self.change_rate:+.2f}%, "
            f"status={status})>"
        )


if __name__ == "__main__":
    # 엔티티 테스트
    print("=== 마켓 인덱스 엔티티 테스트 ===\n")

    # 1. 업비트 지수 생성
    ubci = MarketIndex.create_upbit_index(
        code="ubci",
        name="업비트 종합 지수",
        value=Decimal("18000.50"),
        change=Decimal("150.30"),
        change_rate=Decimal("0.84")
    )
    print(f"1. 업비트 지수 생성: {ubci}")
    print(f"   만료 여부: {ubci.is_expired()}")
    print(f"   남은 시간: {ubci.get_remaining_ttl()}초\n")

    # 2. 값 업데이트
    ubci.update_value(Decimal("18100.00"))
    print(f"2. 값 업데이트: {ubci}")
    print(f"   변동: {ubci.change:,.2f} ({ubci.change_rate:+.2f}%)\n")

    # 3. 글로벌 지수 생성
    market_cap = MarketIndex.create_global_index(
        code="total_market_cap",
        name="총 시가총액",
        value=Decimal("3500000000000"),  # 3.5조 달러
        extra_data={"currency": "USD"}
    )
    print(f"3. 글로벌 지수: {market_cap}\n")

    # 4. 코인 지수 생성
    btc = MarketIndex.create_coin_index(
        symbol="BTC",
        price=Decimal("85000000"),
        change_rate=Decimal("2.5"),
        extra_data={"market_cap": Decimal("1700000000000")}
    )
    print(f"4. 코인 지수: {btc}")
    print(f"   TTL: {btc.ttl_seconds}초\n")

    # 5. USD/KRW 환율
    usd = MarketIndex.create_usd_rate(
        rate=Decimal("1320.50"),
        change_rate=Decimal("0.15")
    )
    print(f"5. USD/KRW: {usd}\n")

    # 6. 딕셔너리 변환
    print("6. 딕셔너리 변환:")
    print(f"   {ubci.to_dict()}\n")

    # 7. 만료 테스트 (TTL 0으로 설정)
    expired_index = MarketIndex(
        index_type=MarketIndex.TYPE_UPBIT,
        code="test",
        name="만료 테스트",
        value=Decimal("1000"),
        ttl_seconds=0
    )
    import time
    time.sleep(1)
    print(f"7. 만료 테스트: {expired_index}")
    print(f"   만료 여부: {expired_index.is_expired()}")
