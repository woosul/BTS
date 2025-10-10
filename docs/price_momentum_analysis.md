# 가격 모멘텀 분석 문제점 및 개선 방안

모멘텀 전략의 7일/30일 데이터가 0.0으로 나오는 문제를 분석하겠습니다. 먼저 관련 코드를 확인하겠습니다.

코드를 확인한 결과, **7일과 30일 데이터 수집 기능이 구현되지 않았습니다**.

## 분석 결과

### 1) 실제 기능 구현 상태 ❌

**현재 상태:**
```python
# domain/strategies/screening/momentum_screening.py (Line 68-77)
market_data = {
    'current_price': current_price,
    'price_1d': ticker.get('signed_change_rate', 0) * 100,
    'volume_1d': ticker.get('acc_trade_price_24h', 0),
    'price_7d': 0.0,   # ← 미구현
    'volume_7d': 0.0,  # ← 미구현
    'price_30d': 0.0,  # ← 미구현
    'volume_30d': 0.0, # ← 미구현
    'rsi': 0.0
}
```

**문제점:**
- 7일/30일 데이터는 하드코딩된 `0.0` 값만 사용
- Upbit ticker API는 **24시간 데이터만 제공**
- 장기 데이터는 **candle API를 호출하여 계산**해야 함

---

### 2) 기능 구현 방법 및 성능 영향

#### **구현 방법:**

```python
# 7일/30일 가격 변동률 계산
def calculate_momentum(symbol: str, days: int) -> dict:
    """
    days일 전 대비 가격 변동률 및 거래량 증가율 계산
    """
    # 1. candle API로 일봉 데이터 조회 (days + 1일치)
    candles = upbit_client.get_candles_daily(symbol, count=days+1)
    
    # 2. 가격 변동률 계산
    price_current = candles[0]['trade_price']
    price_past = candles[days]['trade_price']
    price_change = ((price_current - price_past) / price_past) * 100
    
    # 3. 거래량 증가율 계산
    volume_recent = sum([c['candle_acc_trade_price'] for c in candles[:days]])
    volume_past = sum([c['candle_acc_trade_price'] for c in candles[days:]])
    volume_change = ((volume_recent - volume_past) / volume_past) * 100 if volume_past > 0 else 0
    
    return {
        'price_change': price_change,
        'volume_change': volume_change
    }
```

#### **성능 영향:**

| 항목 | 1일 (현재) | 7일 추가 | 30일 추가 | 7일+30일 |
|------|-----------|---------|----------|----------|
| **API 호출** | ticker 1회 | +candle 1회 | +candle 1회 | +candle 2회 |
| **데이터 양** | 즉시값 | 8일치 | 31일치 | 8일치 + 31일치 |
| **처리 시간** | ~0.1초 | +0.11초 | +0.11초 | +0.22초 |
| **Rate Limit** | 10회/초 | 10회/초 | 10회/초 | 10회/초 |

**예상 처리 시간 (50개 종목 기준):**
- **현재 (1일만)**: 50개 × 0.1초 = **5초**
- **7일 추가**: 50개 × 0.21초 = **10.5초**
- **30일 추가**: 50개 × 0.21초 = **10.5초**
- **7일+30일**: 50개 × 0.32초 = **16초**

**Rate Limit 대응:**
- Candle API: 초당 10회 제한
- 현재 코드에 이미 0.11초 대기 로직 있음 (`screening_service.py` Line 162)
- 추가 API 호출해도 안전

---

### 3) 관련 API 및 구현 방법

#### **Upbit API 종류:**

| API | 엔드포인트 | 제공 데이터 | Rate Limit |
|-----|-----------|------------|------------|
| **Ticker** | `/ticker` | 24시간 현재가/거래량 | 600회/분 |
| **Candle (일봉)** | `/candles/days` | 일별 OHLCV 데이터 | 10회/초 |
| **Candle (주봉)** | `/candles/weeks` | 주별 OHLCV 데이터 | 10회/초 |
| **Candle (월봉)** | `/candles/months` | 월별 OHLCV 데이터 | 10회/초 |

#### **구현 필요 사항:**

✅ **이미 구현됨:**
- `UpbitClient.get_candles_daily()` (Line 178-199)
- Rate limit 준수 로직 (`screening_service.py` Line 162)

❌ **추가 구현 필요:**
- `MomentumScreening._collect_market_data()`에서 candle API 호출
- 7일/30일 가격 변동률 및 거래량 계산 로직

---

### 4) 7일/30일 분석의 의미

#### **가격 변동성 분석 의미:**

| 기간 | 투자 관점 | 분석 의미 | 추천 대상 |
|------|----------|----------|----------|
| **1일** | 초단타 | - 당일 급등/급락 포착<br>- 뉴스/이벤트 반응<br>- 단기 모멘텀 | 데이 트레이더 |
| **7일** | 단기 스윙 | - 단기 추세 확인<br>- 주간 패턴 분석<br>- 급등 지속성 검증 | 스윙 트레이더 |
| **30일** | 중기 추세 | - 월간 추세 방향<br>- 장기 모멘텀 지속성<br>- 변동성 안정화 구간 | 포지션 트레이더 |

#### **복합 분석 전략:**

```
[예시: 강한 상승 모멘텀 포착]
- 1일: +15% (급등)
- 7일: +30% (지속 상승)
- 30일: +80% (강한 추세)
→ 강력한 상승 모멘텀, 매수 신호

[예시: 약한 모멘텀 (매수 주의)]
- 1일: +10% (급등)
- 7일: +5% (약화)
- 30일: -10% (하락 추세)
→ 일시적 반등, 매수 위험

[예시: 추세 전환 신호]
- 1일: -5% (하락)
- 7일: +20% (회복)
- 30일: +50% (상승 추세)
→ 조정 후 재상승, 매수 기회
```

#### **가중치 전략:**

현재 기본 설정:
```python
strategy_params = {
    "price_weight": 0.4,    # 가격 모멘텀 40%
    "volume_weight": 0.3,   # 거래량 30%
    "rsi_weight": 0.3,      # RSI 30%
    "period_1d": True,
    "period_7d": True,
    "period_30d": True
}
```

**기간별 가중치 적용 예시:**
- 1일: 빠른 반응성 (30%)
- 7일: 단기 추세 확인 (40%)
- 30일: 장기 추세 안정성 (30%)

---

## 결론 및 권장사항

### ✅ 구현 필요성: **매우 높음**

**이유:**
1. **현재는 1일 데이터만 사용** → 단기 변동성에만 의존
2. **7일/30일 추가 시 정확도 향상** → 추세 지속성 검증 가능
3. **API 및 인프라 이미 준비됨** → 구현 난이도 낮음

### 📊 성능 영향: **수용 가능**

- 종목당 +0.22초 (7일+30일)
- 50개 종목: 약 16초 (현재 5초 → +11초)
- Rate limit 준수 가능

### 🚀 구현 우선순위: **HIGH**

**다음 단계:**
1. `MomentumScreening._collect_market_data()` 수정
2. Candle API 호출 로직 추가
3. 7일/30일 계산 함수 구현
4. 테스트 및 검증

**구현하시겠습니까?** 바로 코드 수정을 도와드릴 수 있습니다! 🎯