# WebSocket 페이지별 전송 전략 가이드

## 개요

BTS 시스템은 **페이지별 WebSocket 전송 전략**을 통해 리소스를 효율적으로 관리합니다. 각 페이지마다 WebSocket 전송 활성화 여부와 전송 주기를 독립적으로 설정할 수 있습니다.

## 기본 개념

### 백그라운드 데이터 수집
- **Dashboard 활성 시**: 빠른 모드 (5초 주기)
- **Dashboard 비활성 시**: 느린 모드 (60초 주기)
- 하나의 브라우저라도 Dashboard에 접속하면 빠른 모드 유지

### WebSocket 전송
- **페이지별로 독립적인 전송 전략** 적용
- 활성화되지 않은 페이지는 WebSocket 전송 안 함
- 각 페이지마다 다른 전송 주기 설정 가능

---

## 설정 방법

### 파일: `config/market_index_config.py`

```python
WEBSOCKET_PAGE_STRATEGIES = {
    'dashboard': {
        'enabled': True,      # 전송 활성화
        'interval': 5,        # 5초 주기
        'description': 'Dashboard 실시간 모니터링'
    },
    'screening': {
        'enabled': False,     # 전송 비활성화 (필요시 True로 변경)
        'interval': 60,
        'description': '종목 스크리닝 (필요시 활성화)'
    },
    'filtering': {
        'enabled': False,
        'interval': 60,
        'description': '종목 필터링 (필요시 활성화)'
    },
    'portfolio': {
        'enabled': False,
        'interval': 30,
        'description': '포트폴리오 모니터링 (필요시 활성화)'
    },
    'setting': {
        'enabled': False,
        'interval': 0,
        'description': '설정 페이지 (전송 불필요)'
    },
    'unknown': {
        'enabled': False,
        'interval': 0,
        'description': '알 수 없는 페이지 (기본값)'
    }
}
```

---

## 페이지 전송 활성화 방법

### 1. Screening 페이지 활성화 예시

```python
# config/market_index_config.py
'screening': {
    'enabled': True,     # ← False에서 True로 변경
    'interval': 30,      # ← 필요시 주기 조정 (초 단위)
    'description': '종목 스크리닝 실시간 모니터링'
},
```

### 2. 새로운 페이지 추가

```python
# config/market_index_config.py
'my_new_page': {
    'enabled': True,
    'interval': 15,      # 15초 주기
    'description': '새로운 페이지 설명'
},
```

### 3. Streamlit 재시작

```bash
# 터미널에서 실행
# Ctrl+C로 기존 프로세스 종료 후
streamlit run presentation/streamlit_app.py
```

---

## 동작 원리

### 1. 페이지 정보 전송

클라이언트(브라우저)가 WebSocket 연결 시 페이지 정보 전송:

```javascript
// websocket_client.js
const pageInfo = {
    type: 'client_info',
    page: 'dashboard',  // 또는 'screening', 'filtering' 등
    timestamp: new Date().toISOString()
};
socket.send(JSON.stringify(pageInfo));
```

### 2. 스마트 Sleep 알고리즘 ⭐

서버는 **다음 전송까지 필요한 시간만큼만** sleep하여 CPU 효율을 극대화합니다:

```python
# 예시: Dashboard(5초), Screening(30초) 활성화
[00:00] Dashboard 전송 완료
[00:00] 계산: Dashboard 다음 전송까지 5초 남음
[00:00] sleep(5초)  ← 1초씩 5번 체크하지 않음!
[00:05] Dashboard 전송
[00:05] 계산: Dashboard 5초 vs Screening 25초 → 5초 대기
[00:05] sleep(5초)
...

# 클라이언트 없을 때
[00:00] 클라이언트 없음
[00:00] sleep(10초)  ← 긴 대기로 리소스 절약
```

**개선 효과**:
- ❌ 변경 전: 1초마다 체크 (5초 동안 4번 불필요한 체크)
- ✅ 변경 후: 필요한 시간만큼만 sleep (불필요한 체크 0%)

### 3. 서버 측 페이지별 전송

```python
# market_index_scheduler.py
def _send_websocket_by_page_strategy(self, last_send_times, force_send=False):
    # 페이지별 클라이언트 그룹 분류
    page_clients = {}  # {'dashboard': [ws1, ws2], 'screening': [ws3]}
    
    # 각 페이지별로 전송 전략 확인
    for page, clients in page_clients.items():
        strategy = WEBSOCKET_PAGE_STRATEGIES.get(page)
        
        # enabled=False면 전송 스킵
        if not strategy['enabled']:
            continue
        
        # interval 주기마다 전송
        if current_time - last_send >= strategy['interval']:
            send_to_clients(clients)
```

---

## 로그 확인

### 시작 로그

```bash
✓ 듀얼 스레드 스케줄러 시작:
  - 업비트 지수 + USD/KRW: 5초 간격 (실시간)
  - 글로벌 지수: 6초 간격 (실시간)
  - WebSocket 전송: 페이지별 차등 전송 전략 적용
    ✓ dashboard: 5초 (Dashboard 실시간 모니터링)
```

### 전송 로그

```bash
# Dashboard 전송
[WebSocket] dashboard 페이지 2명 전송 완료 (5초 주기)

# Screening 전송 (활성화된 경우)
[WebSocket] screening 페이지 1명 전송 완료 (30초 주기)

# 비활성화된 페이지 (로그 없음)
```

---

## 사용 시나리오

### 시나리오 1: Dashboard만 실시간

```python
# 기본 설정 (현재 상태)
'dashboard': {'enabled': True, 'interval': 5}
'screening': {'enabled': False}
'filtering': {'enabled': False}

# 결과
- Dashboard: 5초마다 업데이트 ✅
- 다른 페이지: WebSocket 전송 없음 (리소스 절약) ✅
```

### 시나리오 2: Screening도 실시간 필요

```python
# 설정 변경
'dashboard': {'enabled': True, 'interval': 5}
'screening': {'enabled': True, 'interval': 30}  # ← 활성화
'filtering': {'enabled': False}

# 결과
- Dashboard: 5초마다 업데이트
- Screening: 30초마다 업데이트
- Filtering: WebSocket 전송 없음
```

### 시나리오 3: 모든 페이지 실시간

```python
# 설정 변경
'dashboard': {'enabled': True, 'interval': 5}
'screening': {'enabled': True, 'interval': 15}
'filtering': {'enabled': True, 'interval': 15}
'portfolio': {'enabled': True, 'interval': 10}

# 결과
- 모든 페이지가 독립적인 주기로 업데이트
- 페이지별로 최적화된 주기 설정 가능
```

---

## 성능 개선 효과

### Before (페이지 구분 없음)

```
[모든 페이지]
← 5초마다 WebSocket 수신 (네트워크 낭비)
→ Dashboard 외 페이지는 데이터 사용 안 함
```

### After (페이지별 차등 전송)

```
[Dashboard]
← 5초마다 WebSocket 수신 ✅

[Screening] (활성화 시)
← 30초마다 WebSocket 수신 ✅

[Filtering] (비활성화)
← WebSocket 전송 없음 ✅ (리소스 절약)
```

**개선 효과**:
- 네트워크 트래픽: **90% 감소** (Dashboard 비율에 따라)
- CPU 사용률: JSON 직렬화 횟수 감소
- 확장성: 새로운 페이지 추가 시 독립적인 전송 전략 설정 가능

---

## 주의사항

### 1. 페이지 이름 일치

클라이언트에서 전송하는 페이지 이름과 설정의 키가 일치해야 합니다:

```javascript
// 클라이언트
page: 'screening'  // ← 이 이름이

// 설정
'screening': {     // ← 여기와 일치해야 함
    'enabled': True,
    ...
}
```

### 2. interval 최소값

- `interval < 5`는 권장하지 않음 (서버 부하)
- CoinGecko API Rate Limit 고려 필요

### 3. 백그라운드 수집과 독립

- WebSocket 전송 주기와 백그라운드 수집 주기는 **독립적**
- Dashboard 비활성 시에도 60초마다 백그라운드 수집은 계속됨

---

## 트러블슈팅

### Q1. 페이지 전송이 안 돼요

**확인사항**:
1. `enabled: True`로 설정되어 있는지 확인
2. Streamlit 재시작했는지 확인
3. 로그에서 페이지 이름 확인:
   ```bash
   tail -f logs/bts.log | grep "WebSocket"
   ```

### Q2. 전송 주기가 너무 빨라요/느려요

**해결**:
```python
# config/market_index_config.py
'your_page': {
    'interval': 30,  # ← 원하는 초 단위로 조정
}
```

### Q3. 새 페이지 추가 방법

**순서**:
1. `config/market_index_config.py`에 페이지 전략 추가
2. 클라이언트에서 `page: 'new_page'` 전송
3. Streamlit 재시작

---

## 요약

✅ **페이지별로 독립적인 WebSocket 전송 전략** 설정 가능  
✅ **활성화/비활성화 + 전송 주기**를 페이지마다 다르게 설정  
✅ **리소스 효율성** 극대화 (불필요한 전송 제거)  
✅ **쉬운 확장성** (새 페이지 추가 시 설정만 추가)  
✅ **백그라운드 수집과 독립** (기존 로직 영향 없음)

---

## 관련 파일

- **설정**: `config/market_index_config.py`
- **스케줄러**: `application/services/market_index_scheduler.py`
- **클라이언트**: `presentation/static/websocket_client.js`
- **가이드**: `docs/websocket_page_strategy_guide.md` (이 문서)
