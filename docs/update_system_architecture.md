# BTS 데이터 업데이트 시스템 구조

## 📊 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BTS 데이터 업데이트 시스템                           │
└─────────────────────────────────────────────────────────────────────┘

┌────────────────────┐         ┌────────────────────┐
│ 백그라운드 데이터   │         │   화면 업데이트     │
│   수집 스레드       │   →     │   (클라이언트)     │
└────────────────────┘         └────────────────────┘
         ↓                              ↑
    [Database]                    [WebSocket]
```

---

## 1️⃣ 백그라운드 데이터 수집 (독립 스레드)

### 설정 파일
`/Users/denny/Gaia/30_Share/33_DEVELOPMENT/BTS/config/market_index_config.py`

### 수집 주기 (동적 간격 시스템)

#### Dashboard 활성 시 (빠른 모드)
```python
UPDATE_INTERVAL_UPBIT_SCRAPING = 5    # 업비트 지수 + USD/KRW: 5초
UPDATE_INTERVAL_COINGECKO = 6         # 글로벌 지수: 6초 (429 에러 방지)
UPDATE_INTERVAL_FXRATES = 3600        # FxRates API: 1시간 (fallback)
UPDATE_INTERVAL_CURRENCY_API = 86400  # Currency API: 1일 (fallback)
```

#### Dashboard 비활성 시 (백그라운드 모드)
```python
DEFAULT_BACKGROUND_UPDATE_INTERVAL = 300  # 기본값: 5분

# Setting 페이지에서 설정 가능한 옵션 (초 단위)
# 10초, 30초, 1분, 5분, 10분, 20분, 30분
```

### 동적 간격 전환 시스템

```
┌─────────────────────────────────────────┐
│       Dashboard 페이지 활성?            │
└─────────────────────────────────────────┘
         │                  │
    Yes  │                  │  No
         ↓                  ↓
   ┌──────────┐      ┌──────────────┐
   │ 빠른 모드 │      │ 백그라운드 모드│
   │ 5초/6초  │      │ 사용자 설정값 │
   └──────────┘      └──────────────┘
         │                  │
         └────────┬─────────┘
                  ↓
         ┌─────────────────┐
         │ 데이터 수집 실행 │
         └─────────────────┘
```

**동작 원리**:
- `_is_dashboard_active()`: WebSocket 연결 중 Dashboard 클라이언트 존재 확인
- `_get_background_interval()`: UserSettings DB에서 사용자 설정 간격 읽기
- 각 업데이트 루프마다 동적으로 간격 재계산

### 동작 구조

```
[업비트 스레드]          [글로벌 스레드]
  Dashboard ON: 5초      Dashboard ON: 6초
  Dashboard OFF: 설정값   Dashboard OFF: 설정값
     ↓                        ↓
  웹스크래핑              CoinGecko API
     ↓                        ↓
┌──────────────────────────────────┐
│          Database                │
│    (단일 진실 공급원, SSOT)       │
└──────────────────────────────────┘
```

**핵심 특징**:
- ✅ **독립 실행**: 각 스레드는 서로 영향 없이 독립적으로 실행
- ✅ **동적 간격 조정**: Dashboard 활성 여부에 따라 자동 전환
- ✅ **API 충돌 방지**: 종목선정/매수 분석 시 백그라운드를 느리게 설정
- ✅ **자동 재시도**: API 실패 시 5초 후 자동 재시도
- ✅ **데이터 보호**: API 실패 시 빈 데이터(0)로 DB 덮어쓰기 방지
- ✅ **DB 중심**: 모든 데이터는 DB에 저장되며, 다른 컴포넌트는 DB에서만 읽음

### 설정 변경 방법

#### UI에서 변경 (권장)
```
1. Setting 페이지 접속
2. "백그라운드 업데이트 설정" 섹션
3. 간격 선택 (10초, 30초, 1분, 5분, 10분, 20분, 30분)
4. "저장" 버튼 클릭
→ 즉시 적용, 재시작 불필요
```

#### 코드에서 변경 (고급 사용자)
```bash
# 1. 설정 파일 편집
nano config/market_index_config.py

# 2. 빠른 모드 간격 수정
UPDATE_INTERVAL_COINGECKO = 10  # 예: 6초 → 10초

# 3. Streamlit 재시작
./restart_streamlit.sh

# 4. 로그 모니터링
./monitor_logs.sh
```

---

## 2️⃣ WebSocket 전송 주기

### 설정
```python
WEBSOCKET_UPDATE_INTERVAL = 5  # 5초마다 클라이언트에 전송
```

### 동작 구조

```
┌─────────────────────────┐
│   WebSocket 스레드      │
│   (5초 주기 브로드캐스트)│
└─────────────────────────┘
         ↓ (DB 조회)
┌─────────────────────────┐
│      Database           │
└─────────────────────────┘
         ↓ (전송)
┌─────────────────────────┐
│  연결된 모든 클라이언트   │
│  (브라우저 Dashboard)    │
└─────────────────────────┘
```

**핵심 특징**:
- ✅ **DB 기반**: 백그라운드 수집과 무관하게 DB에서 최신 데이터 읽기
- ✅ **브로드캐스트**: 연결된 모든 클라이언트에 동일한 데이터 전송
- ✅ **논블로킹**: 전송 실패 시에도 다음 주기는 정상 실행
- ✅ **자동 재연결**: 클라이언트 연결 끊김 시 자동 재연결 시도

### 전송 데이터 형식

```json
{
  "type": "indices_updated",
  "timestamp": "2025-10-17T10:30:00",
  "data": {
    "upbit": {
      "ubci": {"value": 17560.36, "change_rate": -0.11},
      "ubmi": {"value": 5739.69, "change_rate": 0.33},
      "ub10": {"value": 4715.89, "change_rate": 0.03},
      "ub30": {"value": 4224.45, "change_rate": 0.01}
    },
    "usd_krw": {"value": 1417.4, "change_rate": 0.36},
    "global": {
      "total_market_cap_usd": 3888590205326,
      "btc_dominance": 57.08
    },
    "coingecko_top_coins": [...]
  }
}
```

---

## 3️⃣ 화면 업데이트 (Dashboard 새로고침)

### 설정 위치
**Setting 페이지** → "화면 업데이트 설정" 섹션

### 설정 키
`UserSettings.DASHBOARD_REFRESH_INTERVAL` (DB 저장)

### 동작 방식

```
┌──────────────────────────┐
│   Dashboard 페이지        │
│  (Streamlit st.rerun())  │
└──────────────────────────┘
         ↑
    (설정된 간격마다 새로고침)
         ↑
┌──────────────────────────┐
│  DASHBOARD_REFRESH_      │
│  INTERVAL (초 단위)       │
└──────────────────────────┘
```

**선택 옵션**:
- `OFF (WebSocket만 사용)` - **권장** ⭐
- `10초` - 페이지 전체 새로고침
- `30초` - 페이지 전체 새로고침
- `1분` / `3분` / `5분` / `10분`

**핵심 특징**:
- ✅ **WebSocket과 독립**: WebSocket 실시간 업데이트와 별개로 동작
- ✅ **일반적으로 OFF**: WebSocket이 5초마다 자동 업데이트하므로 불필요
- ⚠️ **현재 미구현**: selectbox는 있지만 실제 자동 새로고침 로직은 아직 구현되지 않음

---

## 4️⃣ 백그라운드 ↔ 화면 업데이트 관계

### 전체 플로우

```
[단계 1] 데이터 수집 (백그라운드)
┌────────────────────┐      ┌────────────────────┐
│ 업비트 스레드 (5초) │  →  │     Database       │
└────────────────────┘      │  (SSOT, 단일원천)  │
┌────────────────────┐      │                    │
│ 글로벌 스레드 (6초) │  →  │                    │
└────────────────────┘      └────────────────────┘
                                    ↓
[단계 2] WebSocket 전송 (5초)
                            ┌────────────────────┐
                            │ WebSocket 스레드   │
                            │  (DB에서 읽기)     │
                            └────────────────────┘
                                    ↓
[단계 3] 클라이언트 수신 (실시간)
                            ┌────────────────────┐
                            │  Dashboard 브라우저│
                            │  (JavaScript 업데이트)│
                            └────────────────────┘
                                    ↓
[단계 4] 페이지 새로고침 (선택적, 현재 미사용)
                            ┌────────────────────┐
                            │  Streamlit rerun   │
                            │  (전체 페이지 재로드)│
                            └────────────────────┘
```

### 업데이트 타이밍 다이어그램

#### Dashboard 활성 시 (빠른 모드)
```
시간축 →  0초    5초    10초   15초   20초   25초   30초
          │      │      │      │      │      │      │
업비트    ●------●------●------●------●------●------●
글로벌    ●-----------●-----------●-----------●--------
WebSocket ●------●------●------●------●------●------●
화면      ●-----(자동 업데이트, OFF 권장)-------------

범례:
● = 데이터 수집/전송 시점
─ = 대기 기간
```

#### Dashboard 비활성 시 (백그라운드 모드, 예: 30초 설정)
```
시간축 →  0초         30초        60초        90초
          │           │           │           │
업비트    ●-----------●-----------●-----------●
글로벌    ●-----------●-----------●-----------●
WebSocket ●------●------●------●------●------●
화면      (Screening/Transaction 페이지 활성)

범례:
● = 데이터 수집/전송 시점
─ = 대기 기간 (백그라운드 모드)
```

### 데이터 흐름 요약

| 단계 | 컴포넌트 | 주기 (Dashboard ON) | 주기 (Dashboard OFF) | 역할 | 설정 위치 |
|------|----------|---------------------|----------------------|------|-----------|
| 1 | 업비트 스레드 | 5초 | 사용자 설정 (10초~30분) | 웹스크래핑 → DB 저장 | Config (빠른) + UserSettings (느린) |
| 2 | 글로벌 스레드 | 6초 | 사용자 설정 (10초~30분) | CoinGecko API → DB 저장 | Config (빠른) + UserSettings (느린) |
| 3 | WebSocket 스레드 | 5초 | 5초 | DB 읽기 → 클라이언트 전송 | `market_index_config.py` (고정) |
| 4 | Dashboard 새로고침 | OFF (권장) | OFF (권장) | 페이지 전체 새로고침 | Setting 페이지 (DB 저장) |

---

## 5️⃣ 설정 관리 위치

### 설정 체계 (3-Layer Architecture)

```
┌─────────────────────────────────────────────┐
│  Layer 1: Config (시스템 규칙)               │
│  market_index_config.py                     │
│  - 빠른 모드 간격 (5초/6초)                  │
│  - 백그라운드 기본값 (5분)                   │
│  - 사용 가능한 옵션 목록                     │
│  - 검증 로직                                 │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  Layer 2: UserSettings (사용자 선택)         │
│  user_settings 테이블                        │
│  - GENERAL_UPDATE_INTERVAL (사용자 설정)     │
│  - DASHBOARD_REFRESH_INTERVAL (사용자 설정)  │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  Layer 3: Runtime (실행 시 적용)             │
│  market_index_scheduler.py                  │
│  - Dashboard 활성: Config 빠른 모드          │
│  - Dashboard 비활성: UserSettings 값         │
└─────────────────────────────────────────────┘
```

### 하드코딩 설정 (코드 수정 필요)
**파일**: `config/market_index_config.py`

```python
# Dashboard 활성 시 (빠른 모드)
UPDATE_INTERVAL_UPBIT_SCRAPING = 5
UPDATE_INTERVAL_COINGECKO = 6

# WebSocket 전송 주기 (항상 고정)
WEBSOCKET_UPDATE_INTERVAL = 5

# 백그라운드 기본값
DEFAULT_BACKGROUND_UPDATE_INTERVAL = 300  # 5분

# 사용 가능한 백그라운드 옵션
def get_available_background_intervals() -> list:
    return [10, 30, 60, 300, 600, 1200, 1800]
```

**변경 방법**: 파일 편집 → Streamlit 재시작

### DB 저장 설정 (UI에서 변경 가능)
**설정 페이지**: Setting.py

| 설정 키 | 설명 | 기본값 | 사용 여부 | 적용 범위 |
|---------|------|--------|-----------|-----------|
| `DASHBOARD_REFRESH_INTERVAL` | Dashboard 페이지 새로고침 간격 | 0 (OFF) | ⚠️ 미구현 | Dashboard 페이지만 |
| `GENERAL_UPDATE_INTERVAL` | 백그라운드 업데이트 간격 | 300초 (5분) | ✅ **사용 중** | Dashboard 비활성 시 |

**중요**: `GENERAL_UPDATE_INTERVAL`은 Dashboard가 **비활성**일 때만 적용됩니다. Dashboard 활성 시에는 항상 5초/6초(빠른 모드)를 사용합니다.

---

## 6️⃣ 핵심 개념 정리

### Q1. 백그라운드 수집과 화면 업데이트는 어떤 관계?
**A**: **독립적**입니다.
- 백그라운드 스레드가 DB에 데이터를 저장
- WebSocket이 DB에서 읽어서 클라이언트에 전송
- 화면은 WebSocket으로 자동 업데이트
- 페이지 새로고침은 선택적 (일반적으로 OFF)

### Q2. Dashboard 활성 여부를 어떻게 판단하나요?
**A**: WebSocket 연결 정보로 판단합니다.
- `_is_dashboard_active()`: WebSocket `client_info`에서 `page == 'dashboard'` 확인
- Dashboard 페이지 접속 시 WebSocket이 자동 연결되면서 페이지 정보 전송
- 다른 페이지로 이동하면 Dashboard 클라이언트 없음 → 백그라운드 모드 전환

### Q3. 백그라운드 간격을 30초로 설정했는데 왜 Dashboard에서는 5초/6초로 나오나요?
**A**: **정상 동작**입니다.
- Dashboard **활성 시**: 빠른 모드 (5초/6초) - 실시간 모니터링 우선
- Dashboard **비활성 시**: 백그라운드 모드 (30초) - API 충돌 방지
- Screening/Transaction 페이지로 이동하면 자동으로 30초로 전환됩니다.

### Q4. CoinGecko 간격을 10초로 줄이면 화면도 10초마다 업데이트?
**A**: **아니오**. WebSocket이 5초마다 전송합니다.
- CoinGecko 10초 → 10초마다 DB 업데이트
- WebSocket 5초 → 5초마다 DB 읽고 전송
- 결과: 5초마다 화면 업데이트 (단, CoinGecko 데이터는 10초마다 새로워짐)

### Q5. WebSocket 간격을 10초로 늘리면?
**A**: 화면 업데이트가 **10초**로 느려집니다.
- 백그라운드 수집은 그대로 (빠른 모드: 5초/6초, 느린 모드: 설정값)
- DB에 데이터는 빠르게 쌓임
- 클라이언트는 10초마다 받음

### Q6. Dashboard 새로고침 설정(현재 OFF)을 10초로 바꾸면?
**A**: **전체 페이지**가 10초마다 새로고침됩니다.
- WebSocket 실시간 업데이트 + 페이지 새로고침 중복
- 일반적으로 불필요 (WebSocket만으로 충분)
- 특수한 경우(차트 재렌더링 필요)에만 사용

### Q7. 종목선정/매수 분석 시 API 충돌을 어떻게 방지하나요?
**A**: 백그라운드 간격을 **느리게** 설정합니다.
- Setting 페이지에서 백그라운드 간격을 5분 이상으로 설정
- Screening/Transaction 페이지로 이동 → 자동으로 느린 모드 전환
- 분석 중에는 업비트/글로벌 수집이 5분마다만 실행
- 분석 완료 후 Dashboard로 돌아가면 다시 5초/6초로 자동 전환

---

## 7️⃣ 권장 설정

### 실시간 트레이딩 (기본 설정) ⭐
```
[빠른 모드 - Dashboard 활성]
업비트: 5초
글로벌: 6초 (429 에러 방지)
WebSocket: 5초
Dashboard 새로고침: OFF

[백그라운드 모드 - Dashboard 비활성]
업비트/글로벌: 5분 (Setting 페이지에서 설정)
WebSocket: 5초 (그대로 유지)
```

### 활발한 분석 작업 (API 충돌 방지)
```
[빠른 모드 - Dashboard 활성]
업비트: 5초
글로벌: 6초
WebSocket: 5초
Dashboard 새로고침: OFF

[백그라운드 모드 - Dashboard 비활성]
업비트/글로벌: 10분 (Screening/Transaction 페이지 사용 시)
WebSocket: 5초
```

### 장기 운영 (안정성 우선)
```
[빠른 모드 - Dashboard 활성]
업비트: 5초
글로벌: 10초 (429 에러 방지 강화)
WebSocket: 5초
Dashboard 새로고침: OFF

[백그라운드 모드 - Dashboard 비활성]
업비트/글로벌: 30분 (서버 부하 최소화)
WebSocket: 5초
```

### 설정 팁
1. **Dashboard 모니터링 중**: 설정 불필요 (자동으로 5초/6초)
2. **종목선정/매수 분석 중**: 백그라운드 간격을 5분 이상으로 설정
3. **429 에러 발생 시**: 빠른 모드 글로벌 간격을 10초로 증가 (코드 수정 필요)
4. **장기 서버 운영**: 백그라운드 간격을 20분 이상으로 설정

---

## 8️⃣ 트러블슈팅

### 문제: CoinGecko 429 에러 발생
**해결**:
```bash
# config/market_index_config.py 수정
UPDATE_INTERVAL_COINGECKO = 10  # 6초 → 10초

# 재시작
./restart_streamlit.sh

# 로그 확인
./monitor_logs.sh
```

### 문제: 화면 업데이트가 느림
**확인 사항**:
1. WebSocket 연결 확인 (브라우저 콘솔)
2. WebSocket 전송 로그 확인 (`monitor_logs.sh`)
3. `WEBSOCKET_UPDATE_INTERVAL` 설정 확인

### 문제: 백그라운드 간격을 변경했는데 적용되지 않음
**원인**: Dashboard 페이지에 있으면 항상 빠른 모드(5초/6초)를 사용합니다.
**확인 방법**:
```bash
# 로그에서 간격 확인
tail -f logs/bts.log | grep "간격:"

# [업비트 업데이터] 업비트 지수 + USD/KRW 수집 시작 (간격: 5초)  ← Dashboard 활성
# [업비트 업데이터] 업비트 지수 + USD/KRW 수집 시작 (간격: 30초) ← Dashboard 비활성
```
**해결**: Screening/Transaction 페이지로 이동하면 설정된 간격으로 전환됩니다.

### 문제: 종목선정/매수 분석 시 API 충돌
**해결**:
1. Setting 페이지에서 백그라운드 간격을 **5분 이상**으로 설정
2. Screening/Transaction 페이지로 이동
3. 로그에서 간격 전환 확인 (5초 → 5분)
4. 분석 작업 진행

### 문제: BTC 도미넌스가 0.00%로 표시
**해결**: 이미 수정됨 (빈 데이터 저장 방지 로직 추가)

---

## 9️⃣ 모니터링 명령어

```bash
# 실시간 로그 모니터링 (색상 구분)
./monitor_logs.sh

# 전체 로그 확인
tail -f logs/bts.log

# 업데이트 간격 모니터링 (동적 간격 전환 확인)
tail -f logs/bts.log | grep "간격:"

# 429 에러만 확인
tail -f logs/bts.log | grep "429"

# WebSocket 전송 확인
tail -f logs/bts.log | grep "WebSocket 데이터 전송"

# BTC 도미넌스 값 확인
tail -f logs/bts.log | grep "BTC도미넌스"

# Dashboard 활성 상태 확인
tail -f logs/bts.log | grep -E "(Dashboard 활성|Dashboard 비활성)"

# 백그라운드 간격 설정 확인 (DB)
sqlite3 data/bts.db "SELECT setting_key, setting_value FROM user_settings WHERE setting_key = 'general_update_interval';"
```

---

## 📝 참고 문서

- 설정 파일: `config/market_index_config.py`
- 스케줄러: `application/services/market_index_scheduler.py`
- 서비스: `application/services/market_index_service.py`
- 캐시 서비스: `application/services/cached_market_index_service.py`
- 대시보드: `presentation/pages/Dashboard.py`
- 설정 페이지: `presentation/pages/Setting.py`
- 로그 모니터: `monitor_logs.sh`

---

## 🔄 변경 이력

### v2.0 (2025-10-17)
- ✅ **동적 간격 시스템 추가**
  - Dashboard 활성/비활성에 따른 자동 간격 전환
  - UserSettings 기반 백그라운드 간격 설정
  - API 충돌 방지를 위한 느린 모드 지원
- ✅ **3-Layer Architecture 구현**
  - Config (시스템 규칙) → UserSettings (사용자 선택) → Runtime (실행 시 적용)
- ✅ **Setting 페이지 UI 개선**
  - 백그라운드 업데이트 간격 설정 추가
  - Screening 페이지와 동일한 스타일 적용

### v1.0 (2025-10-17)
- 초기 문서 작성
- 백그라운드 데이터 수집 구조 설명
- WebSocket 전송 주기 설명
- 하드코딩 설정 방식

---

**최종 업데이트**: 2025-10-17
**버전**: 2.0
