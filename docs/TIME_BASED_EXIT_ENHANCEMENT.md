# TimeBasedExitStrategy 날짜/시간 제약 기능 개선

## 개요

TimeBasedExitStrategy에 날짜/시간 제약 기능을 추가하여 더 정교한 시간 기반 매도 전략을 구현할 수 있도록 개선했습니다.

## 주요 기능

### 1. 날짜/시간 제약 ON/OFF
- `use_datetime_constraint` 파라미터로 날짜/시간 제약 기능을 활성화/비활성화
- 기본값: `False` (기존 동작 유지)

### 2. 두 가지 모드 지원

#### A. 절대 날짜/시간 모드 (Absolute Mode)
특정 날짜/시간에 도달하면 매도

**사용 사례:**
- 연말 세금 정산 전 매도
- 특정 이벤트 전/후 매도
- 정기 리밸런싱 시점

**파라미터:**
```python
{
    "use_datetime_constraint": True,
    "datetime_mode": "absolute",
    "absolute_exit_datetime": datetime(2025, 12, 31, 23, 59, 59)
}
```

#### B. 상대 날짜/시간 모드 (Relative Mode)
매수 시점부터 N일/시간 경과 후 매도

**사용 사례:**
- 단타: 매수 후 4시간
- 스윙: 매수 후 3~7일
- 장기: 매수 후 30일

**파라미터:**
```python
{
    "use_datetime_constraint": True,
    "datetime_mode": "relative",
    "relative_exit_days": 3,     # 3일
    "relative_exit_hours": 12    # + 12시간 = 총 3.5일
}
```

### 3. 기존 모드와의 호환성
날짜/시간 제약을 비활성화하면 기존 방식대로 동작:
- `holding_periods`: 캔들 개수 기준
- `holding_hours`: 시간 기준 (선택적)

## 새로운 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `use_datetime_constraint` | bool | False | 날짜/시간 제약 사용 여부 |
| `datetime_mode` | str | "relative" | "absolute" 또는 "relative" |
| `absolute_exit_datetime` | datetime | None | 절대 날짜/시간 (absolute 모드) |
| `relative_exit_days` | int | 0 | 매수 후 N일 (relative 모드) |
| `relative_exit_hours` | int | 0 | 매수 후 N시간 (relative 모드) |

## 사용 예제

### 예제 1: 단타 전략 (4시간)
```python
from domain.strategies.exit import TimeBasedExitStrategy
from datetime import datetime

strategy = TimeBasedExitStrategy(
    id=1,
    parameters={
        "use_datetime_constraint": True,
        "datetime_mode": "relative",
        "relative_exit_days": 0,
        "relative_exit_hours": 4,
        "min_profit_pct": 1  # 최소 1% 이익
    }
)
```

### 예제 2: 스윙 트레이딩 (3일)
```python
strategy = TimeBasedExitStrategy(
    id=2,
    parameters={
        "use_datetime_constraint": True,
        "datetime_mode": "relative",
        "relative_exit_days": 3,
        "relative_exit_hours": 0,
        "min_profit_pct": 3  # 최소 3% 이익
    }
)
```

### 예제 3: 연말 정산 (절대 시각)
```python
strategy = TimeBasedExitStrategy(
    id=3,
    parameters={
        "use_datetime_constraint": True,
        "datetime_mode": "absolute",
        "absolute_exit_datetime": datetime(2025, 12, 31, 23, 59, 59),
        "force_exit": True  # 손실이어도 강제 매도
    }
)
```

## check_exit_condition 메서드 변경

### 새로운 시그니처
```python
def check_exit_condition(
    self,
    entry_price: Decimal,
    current_price: Decimal,
    ohlcv_data: List[OHLCV],
    indicators: Dict,
    holding_period: int = 0,
    entry_time: Optional[datetime] = None  # 새로 추가
) -> tuple[bool, Decimal, str]:
```

**주의:** 날짜/시간 제약을 사용할 때는 반드시 `entry_time`을 제공해야 합니다.

## 내부 동작 원리

### 절대 모드
1. 현재 시간 추출 (`current_time`)
2. 목표 시각과 비교
3. `current_time >= absolute_exit_datetime` → 매도 신호

### 상대 모드
1. 매수 시점 (`entry_time`) 필요
2. 목표 시간 계산: `target_exit_time = entry_time + timedelta(days=N, hours=M)`
3. `current_time >= target_exit_time` → 매도 신호

### 확신도 계산
- 날짜/시간 제약 모드: 기본 확신도 85%
- 수익 시: +10%
- 큰 손실 시: +20% (빨리 손절)
- 소폭 손실 시: -10%

## 파라미터 검증

### 필수 조건
- `datetime_mode`는 "absolute" 또는 "relative"만 가능
- Absolute 모드: `absolute_exit_datetime` 필수 (datetime 객체)
- Relative 모드: `relative_exit_days` 또는 `relative_exit_hours` 중 최소 하나는 0보다 커야 함

### 잘못된 설정 예시
```python
# ❌ 잘못된 예 1: datetime_mode 오타
{
    "datetime_mode": "relatve"  # ValueError
}

# ❌ 잘못된 예 2: absolute 모드인데 datetime 없음
{
    "datetime_mode": "absolute",
    "absolute_exit_datetime": None  # ValueError
}

# ❌ 잘못된 예 3: relative 모드인데 일/시간 모두 0
{
    "datetime_mode": "relative",
    "relative_exit_days": 0,
    "relative_exit_hours": 0  # ValueError
}
```

## 테스트 결과

### Test 1: Relative mode (2일 경과)
- **입력:** 매수 후 2일 2시간 경과, +3% 수익
- **결과:** 매도=True, 확신도=93.50%
- **이유:** 보유 시간 경과 (매수 후 2일 0시간), 손익률 3.00%

### Test 2: Relative mode (시간 미달)
- **입력:** 매수 후 1일 경과 (목표: 2일)
- **결과:** 매도=False
- **이유:** 보유 시간 미달 (남은 시간: 24.0시간)

### Test 3: Absolute mode (목표 시각 도달)
- **입력:** 2025-12-31 23:59:59 도달, +5% 수익
- **결과:** 매도=True, 확신도=93.50%
- **이유:** 목표 시각 도달 (2025-12-31 23:59:59), 손익률 5.00%

### Test 4: 기존 모드 (holding_periods)
- **입력:** 30개 캔들 보유 (목표: 24개), +2% 수익
- **결과:** 매도=True, 확신도=79.75%
- **이유:** 보유 기간 초과 (30개 캔들, 30.0시간), 손익률 2.00%

## 기존 코드와의 호환성

기존 코드는 수정 없이 그대로 동작합니다:

```python
# 기존 방식 (변경 없음)
strategy = TimeBasedExitStrategy(
    id=1,
    parameters={
        "holding_periods": 24
    }
)

# check_exit_condition 호출 시 entry_time 생략 가능
result = strategy.check_exit_condition(
    entry_price=Decimal("100000"),
    current_price=Decimal("102000"),
    ohlcv_data=ohlcv,
    indicators=indicators,
    holding_period=30
    # entry_time 생략 → 기존 모드로 동작
)
```

## 실전 활용 시나리오

### 1. 단타 전략 (Scalping)
```python
# 매수 후 4시간, 최소 1% 이익
TimeBasedExitStrategy(
    parameters={
        "use_datetime_constraint": True,
        "datetime_mode": "relative",
        "relative_exit_hours": 4,
        "min_profit_pct": 1
    }
)
```

### 2. 스윙 트레이딩 (Swing Trading)
```python
# 매수 후 3~7일, 최소 3% 이익
TimeBasedExitStrategy(
    parameters={
        "use_datetime_constraint": True,
        "datetime_mode": "relative",
        "relative_exit_days": 3,
        "min_profit_pct": 3
    }
)
```

### 3. 연말 세금 정산
```python
# 2025년 12월 31일 자정 전 전량 매도
TimeBasedExitStrategy(
    parameters={
        "use_datetime_constraint": True,
        "datetime_mode": "absolute",
        "absolute_exit_datetime": datetime(2025, 12, 31, 23, 59, 59),
        "force_exit": True  # 손실이어도 매도
    }
)
```

### 4. 주간 리밸런싱
```python
# 매주 월요일 오전 9시 매도
TimeBasedExitStrategy(
    parameters={
        "use_datetime_constraint": True,
        "datetime_mode": "absolute",
        "absolute_exit_datetime": next_monday_9am,
        "min_profit_pct": 0
    }
)
```

## 주의사항

1. **entry_time 필수**: 날짜/시간 제약 사용 시 `entry_time` 파라미터를 반드시 제공해야 합니다.

2. **타임존 일관성**: `entry_time`, `current_time`, `absolute_exit_datetime`은 동일한 타임존을 사용해야 합니다.

3. **손익 조건 우선**: `min_profit_pct`, `max_loss_pct` 조건은 시간 조건과 별개로 체크됩니다.

4. **force_exit**: 손실 중에도 시간 조건 충족 시 매도하려면 `force_exit=True` 설정.

## 파일 위치

- **전략 구현**: `domain/strategies/exit/time_based_exit.py`
- **사용 예제**: `examples/time_based_exit_example.py`
- **문서**: `docs/TIME_BASED_EXIT_ENHANCEMENT.md`

## 버전 정보

- **개선 날짜**: 2025-10-07
- **관련 이슈**: 사용자 요청 - "날자/시간으로 걸 수 있도록"
- **하위 호환성**: 완전 호환 (기존 코드 수정 불필요)
