"""
TimeBasedExitStrategy 사용 예제

날짜/시간 제약 기능을 활용한 다양한 매도 전략 예제
"""
from datetime import datetime, timedelta
from decimal import Decimal

from domain.strategies.exit import TimeBasedExitStrategy
from core.models import OHLCV


def example_1_legacy_mode():
    """예제 1: 기존 모드 (캔들 개수 기반)"""
    print("=" * 50)
    print("예제 1: 기존 모드 - 24개 캔들 보유 후 매도")
    print("=" * 50)

    strategy = TimeBasedExitStrategy(
        id=1,
        parameters={
            "use_datetime_constraint": False,  # 기존 모드
            "holding_periods": 24,  # 24개 캔들
            "min_profit_pct": 0,
        }
    )

    print(f"전략: {strategy}")
    print(f"설명: 24개 캔들(1시간봉 기준 24시간) 보유 후 매도")
    print()


def example_2_relative_days():
    """예제 2: 상대 날짜/시간 모드 - 매수 후 N일 경과"""
    print("=" * 50)
    print("예제 2: 상대 시간 모드 - 매수 후 3일 경과 시 매도")
    print("=" * 50)

    strategy = TimeBasedExitStrategy(
        id=2,
        parameters={
            "use_datetime_constraint": True,
            "datetime_mode": "relative",
            "relative_exit_days": 3,  # 3일 후
            "relative_exit_hours": 0,
            "min_profit_pct": 0,
        }
    )

    print(f"전략: {strategy}")
    print(f"설명: 매수 시점부터 정확히 3일 경과 후 매도")

    # 시뮬레이션
    entry_time = datetime(2025, 1, 1, 10, 0, 0)
    current_time = datetime(2025, 1, 4, 10, 0, 0)  # 정확히 3일 후

    ohlcv = [OHLCV(
        symbol="KRW-BTC",
        timestamp=current_time,
        open=Decimal("100000"),
        high=Decimal("105000"),
        low=Decimal("99000"),
        close=Decimal("103000"),
        volume=Decimal("100")
    )]

    indicators = {"current_time": current_time}
    result = strategy.check_exit_condition(
        entry_price=Decimal("100000"),
        current_price=Decimal("103000"),
        ohlcv_data=ohlcv,
        indicators=indicators,
        holding_period=0,
        entry_time=entry_time
    )

    print(f"결과: 매도={result[0]}, 확신도={result[1]:.2%}, 이유={result[2]}")
    print()


def example_3_relative_hours():
    """예제 3: 상대 시간 모드 - 매수 후 N시간 경과"""
    print("=" * 50)
    print("예제 3: 상대 시간 모드 - 매수 후 4시간 경과 시 매도 (단타)")
    print("=" * 50)

    strategy = TimeBasedExitStrategy(
        id=3,
        parameters={
            "use_datetime_constraint": True,
            "datetime_mode": "relative",
            "relative_exit_days": 0,
            "relative_exit_hours": 4,  # 4시간 후
            "min_profit_pct": 1,  # 최소 1% 이익 필요
        }
    )

    print(f"전략: {strategy}")
    print(f"설명: 매수 후 4시간 경과 + 최소 1% 이익 시 매도")

    # 시뮬레이션 1: 4시간 경과, 2% 이익
    entry_time = datetime(2025, 1, 1, 10, 0, 0)
    current_time = datetime(2025, 1, 1, 14, 0, 0)  # 4시간 후

    ohlcv = [OHLCV(
        symbol="KRW-BTC",
        timestamp=current_time,
        open=Decimal("100000"),
        high=Decimal("105000"),
        low=Decimal("99000"),
        close=Decimal("102000"),  # 2% 이익
        volume=Decimal("100")
    )]

    indicators = {"current_time": current_time}
    result = strategy.check_exit_condition(
        entry_price=Decimal("100000"),
        current_price=Decimal("102000"),
        ohlcv_data=ohlcv,
        indicators=indicators,
        holding_period=0,
        entry_time=entry_time
    )

    print(f"시뮬레이션 1 (4시간, +2%): 매도={result[0]}, 확신도={result[1]:.2%}")

    # 시뮬레이션 2: 4시간 경과, 0.5% 이익 (최소 익절률 미달)
    result2 = strategy.check_exit_condition(
        entry_price=Decimal("100000"),
        current_price=Decimal("100500"),  # 0.5% 이익
        ohlcv_data=ohlcv,
        indicators=indicators,
        holding_period=0,
        entry_time=entry_time
    )

    print(f"시뮬레이션 2 (4시간, +0.5%): 매도={result2[0]}, 이유={result2[2]}")
    print()


def example_4_absolute_datetime():
    """예제 4: 절대 날짜/시간 모드 - 특정 시각에 매도"""
    print("=" * 50)
    print("예제 4: 절대 시간 모드 - 2025년 12월 31일 자정에 매도")
    print("=" * 50)

    target_datetime = datetime(2025, 12, 31, 23, 59, 59)

    strategy = TimeBasedExitStrategy(
        id=4,
        parameters={
            "use_datetime_constraint": True,
            "datetime_mode": "absolute",
            "absolute_exit_datetime": target_datetime,
            "min_profit_pct": 0,
            "force_exit": True,  # 손실이어도 강제 매도
        }
    )

    print(f"전략: {strategy}")
    print(f"설명: 2025-12-31 23:59:59 도달 시 무조건 매도")

    # 시뮬레이션: 목표 시각 도달
    entry_time = datetime(2025, 11, 1, 0, 0, 0)
    current_time = datetime(2026, 1, 1, 0, 0, 0)  # 목표 시각 지남

    ohlcv = [OHLCV(
        symbol="KRW-BTC",
        timestamp=current_time,
        open=Decimal("100000"),
        high=Decimal("105000"),
        low=Decimal("99000"),
        close=Decimal("95000"),  # -5% 손실
        volume=Decimal("100")
    )]

    indicators = {"current_time": current_time}
    result = strategy.check_exit_condition(
        entry_price=Decimal("100000"),
        current_price=Decimal("95000"),
        ohlcv_data=ohlcv,
        indicators=indicators,
        holding_period=0,
        entry_time=entry_time
    )

    print(f"결과 (손실 -5%): 매도={result[0]}, 확신도={result[1]:.2%}, 이유={result[2]}")
    print()


def example_5_swing_trading():
    """예제 5: 스윙 트레이딩 - 1주일 보유"""
    print("=" * 50)
    print("예제 5: 스윙 트레이딩 - 7일간 보유 후 매도")
    print("=" * 50)

    strategy = TimeBasedExitStrategy(
        id=5,
        parameters={
            "use_datetime_constraint": True,
            "datetime_mode": "relative",
            "relative_exit_days": 7,
            "relative_exit_hours": 0,
            "min_profit_pct": 3,  # 최소 3% 이익
            "force_exit": False,
        }
    )

    print(f"전략: {strategy}")
    print(f"설명: 매수 후 7일 경과 + 최소 3% 이익 시 매도")
    print()


def example_6_combined_strategy():
    """예제 6: 복합 전략 - 2일 후 또는 10% 이익"""
    print("=" * 50)
    print("예제 6: 복합 활용 - 2일 보유 또는 큰 이익 시 매도")
    print("=" * 50)

    # 시간 기반 전략
    time_strategy = TimeBasedExitStrategy(
        id=6,
        parameters={
            "use_datetime_constraint": True,
            "datetime_mode": "relative",
            "relative_exit_days": 2,
            "relative_exit_hours": 0,
            "min_profit_pct": 0,
        }
    )

    # 고정 목표가 전략 (별도로 사용)
    # from domain.strategies.exit import FixedTargetExitStrategy
    # target_strategy = FixedTargetExitStrategy(...)

    print(f"시간 전략: {time_strategy}")
    print(f"설명: 2일 보유 OR 목표 수익률 달성 시 매도 (복합 활용)")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" TimeBasedExitStrategy 날짜/시간 제약 기능 예제")
    print("=" * 70 + "\n")

    example_1_legacy_mode()
    example_2_relative_days()
    example_3_relative_hours()
    example_4_absolute_datetime()
    example_5_swing_trading()
    example_6_combined_strategy()

    print("=" * 70)
    print("✅ 모든 예제 완료!")
    print("=" * 70)
