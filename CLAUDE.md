# 프로젝트 : BTS - Bitcoin Auto Trading System

## 개요
이 파일은 이 저장소에서 작업할 때 Claude Code (claude.ai/code)에 대한 가이드를 제공합니다.

## 미션
FastAPI로 쉽게 전환 가능한 클린 아키텍처 기반 **프로페셔널급 비트코인 자동매매 시스템**을 구축하세요.

## 주요 기능
- **모의투자 전용 가상지갑 시스템**
- **4단계 전략 체계**: 종목선정 → 매수 → 포트폴리오 → 매도
- **다양한 전략 플러그인 구조**: 단일/복합/하이브리드 전략 지원
- **AI 기반 전략 평가**: Claude API 통합
- **모의투자를 통한 전략 테스트 및 성과 관리**
- **전략 성과기반 실거래 전환 지원**
- **거래소와 실거래용 지갑 동기화**
- **Upbit 거래소 우선 지원** (추후 확장 가능) - pyupbit 사용, BTC 시장 거래를 위한 REST API 래퍼

## 핵심 원칙
1. 비즈니스 로직과 UI 완전 분리
2. Service Layer는 FastAPI에서 재사용
3. Repository 패턴으로 데이터 계층 추상화
4. Pydantic으로 타입 안정성
5. 의존성 주입으로 테스트 용이성
6. SQLite로 시작해 PostgreSQL로 확장 용이
7. Streamlit 기반 웹 UI (추후 FastAPI로 전환)

---

## 전략 체계 개요

BTS는 **4단계 전략 파이프라인**으로 구성됩니다:

```
1. 종목선정 → 2. 매수 → 3. 포트폴리오 → 4. 매도
           (Screening) (Entry)  (Portfolio)   (Exit)
                                    ↓
                            AI 평가 시스템 (선택)
```

### 1. 종목선정 전략 (Screening Strategy)
**목적**: KRW/BTC 시장에서 투자 가치가 높은 종목을 선별

#### 주요 기능
- KRW 또는 BTC 시장 선택
- 각 시장의 전체 심볼 목록 대상 스크리닝
- 단일 전략 또는 복합전략 (하이브리드) 설정
- 복합 지표 기반 순위 점수 산출
- 상위 N개 종목 자동 선정

#### 현존 최고의 스크리닝 전략 유형
1. **모멘텀 기반**
   - 가격 상승률 (1일/7일/30일)
   - 거래량 증가율, RSI 모멘텀

2. **변동성 기반**
   - ATR, 볼린저 밴드 폭, 표준편차

3. **거래량 기반**
   - 거래대금 순위, 거래량 급증, 유동성 점수

4. **기술지표 복합**
   - RSI + MACD + 이동평균 조합

5. **하이브리드 (가중치 조합)**
   - 각 전략별 점수에 가중치 부여
   ```python
   score = momentum * 0.3 + volume * 0.3 + volatility * 0.2 + technical * 0.2
   ```

#### 구현 클래스
- `domain/strategies/screening/base_screening.py`
- `domain/strategies/screening/momentum_screening.py`
- `domain/strategies/screening/volume_screening.py`
- `domain/strategies/screening/technical_screening.py`
- `domain/strategies/screening/hybrid_screening.py`

---

### 2. 매수전략 (Entry Strategy)
**목적**: 선정된 종목에 대해 최적의 진입 타이밍 포착

#### 주요 기능
- 종목선정 전략에 따라 선정된 종목을 대상으로 순차적 매수 적용
- 매수량은 포트폴리오 전략에 따라 결정 (수량/금액/기존 보유 기준)
- 단일전략 또는 복합전략 (전략별 가중치 적용)

#### 적용대상 기술지표 및 현존 최고의 매수전략 유형

##### A. 기술적 지표 기반
1. **RSI 전략**
   - 과매도 구간 매수, RSI 다이버전스
   - 파라미터: period(14), oversold(30), overbought(70)

2. **이동평균 교차 (MA Cross)**
   - 골든 크로스 매수
   - 파라미터: short_period(20), long_period(60), ma_type(SMA/EMA)

3. **볼린저 밴드**
   - 하단 밴드 터치/돌파 매수
   - 파라미터: period(20), std_dev(2.0), signal_mode(touch/breakout)

4. **MACD**
   - MACD 골든 크로스, 히스토그램 반전
   - 파라미터: fast(12), slow(26), signal(9)

5. **스토캐스틱**
   - %K와 %D 교차, 과매도 구간 반등
   - 파라미터: k_period(14), d_period(3), smooth(3)

6. **ADX (트렌드 강도)**
   - 강한 트렌드 감지 후 +DI/-DI 교차
   - 파라미터: period(14), adx_threshold(25)

##### B. 패턴 인식 기반
7. **캔들 패턴**
   - 망치형, 샛별형, 상승 삼각형
   - 파라미터: pattern_list

8. **지지/저항 돌파**
   - 저항선 돌파 + 거래량 동반 확인
   - 파라미터: lookback_period, volume_threshold

##### C. 복합 전략
9. **멀티 지표 (AND 조합)**
   - 예: RSI 과매도 AND 볼린저 하단 AND 거래량 증가
   - 파라미터: indicators, combination_mode(AND/OR)

10. **하이브리드 스코어링 (가중치)**
    - 각 전략별 점수 산출 후 가중 평균
    ```python
    confidence = rsi_signal * 0.3 + macd_signal * 0.3 + bb_signal * 0.2 + volume_signal * 0.2
    ```
    - 파라미터: strategy_weights

#### 구현 클래스
- `domain/strategies/entry/base_entry.py`
- `domain/strategies/entry/rsi_entry.py` (✅ Phase 2 완료 - domain/strategies/rsi_strategy.py)
- `domain/strategies/entry/ma_cross_entry.py` (✅ Phase 5 완료 - domain/strategies/ma_cross_strategy.py)
- `domain/strategies/entry/bollinger_entry.py` (✅ Phase 5 완료 - domain/strategies/bollinger_strategy.py)
- `domain/strategies/entry/macd_entry.py`
- `domain/strategies/entry/stochastic_entry.py`
- `domain/strategies/entry/multi_indicator_entry.py`
- `domain/strategies/entry/hybrid_entry.py`

---

### 3. 포트폴리오 전략 (Portfolio Strategy)
**목적**: 자금을 효율적으로 배분하고 리스크 관리

#### 주요 기능
- **포트폴리오 구성 전략**: 금액기준, 수량기준, 보유종목 기준, 보유잔액 기준
- **보유잔액 기준 포트폴리오**: 잔액에 따라 동적 비중 조정
- **매도에 따른 보유잔액 변경 대응**: 유동적 전략 적용
- **리밸런싱**: 주기적 또는 임계값 기반

#### 현존 최고의 포트폴리오 구성전략 유형

1. **균등 배분 (Equal Weight)**
   - 모든 종목에 동일 금액
   ```python
   amount_per_coin = total_balance / num_coins
   ```

2. **비율 배분 (Proportional Weight)**
   - 종목별 가중치 설정 (순위 기반)
   ```python
   amount = total_balance * weight[coin]
   ```

3. **켈리 기준 (Kelly Criterion)**
   - 승률과 손익비 기반 최적 포지션 크기
   ```python
   kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
   ```

4. **리스크 패리티 (Risk Parity)**
   - 각 자산의 리스크 기여도를 동일하게
   ```python
   weight = (1 / volatility) / sum(1 / volatilities)
   ```

5. **동적 배분 (Dynamic Allocation)**
   - 시장 상황에 따라 비중 조정
   - 변동성 증가 시 현금 비중 확대

6. **보유잔액 기준 배분**
   - 기존 보유 종목: 추가 매수량 계산
   - 신규 종목: 초기 진입 금액 설정
   - 잔액 변화에 따른 동적 조정

#### 리밸런싱 전략
1. **주기적**: 매주/매월 목표 비중으로 조정
2. **임계값**: 비중 ±5% 이상 벗어날 때
3. **수익 실현**: 목표 수익 달성 시 일부 매도 후 재배분

#### 구현 클래스
- `domain/entities/portfolio.py`
- `domain/strategies/portfolio/base_portfolio.py`
- `domain/strategies/portfolio/equal_weight.py`
- `domain/strategies/portfolio/proportional_weight.py`
- `domain/strategies/portfolio/kelly_criterion.py`
- `domain/strategies/portfolio/risk_parity.py`
- `domain/strategies/portfolio/dynamic_allocation.py`

---

### 4. 매도전략 (Exit Strategy)
**목적**: 이익 실현 및 손실 최소화

#### 주요 기능
- **보유 코인별 대상 종목 지정**
- **홀딩 타입 분류**: 장기보유, 스윙, 즉시거래
- **즉시거래종목에 대한 매도전략 적용**
- **단일전략 또는 복합전략 (가중치)**

#### 홀딩 타입 분류
1. **장기 보유 (Long-term)**
   - 보유 기간: 3개월 이상
   - 매도: 펀더멘털 변화, 목표가 달성

2. **스윙 트레이딩 (Swing)**
   - 보유 기간: 수일 ~ 수주
   - 매도: 기술적 반전, 목표 수익률

3. **즉시 거래 (Day/Scalping)**
   - 보유 기간: 수분 ~ 수시간
   - 매도: 빠른 익절/손절

#### 적용대상 기술지표 및 현존 최고의 매도전략 유형

##### A. 목표 기반
1. **고정 목표가**
   - 매수가 대비 +N% 상승 시
   - 파라미터: target_profit_pct(5%, 10%, 20%)

2. **단계별 익절**
   - 가격 상승에 따라 분할 매도
   - 예: +5% 시 1/3, +10% 시 1/3, +20% 시 나머지
   - 파라미터: profit_levels, sell_ratios

3. **손절가**
   - 매수가 대비 -N% 하락 시
   - 파라미터: stop_loss_pct(-3%, -5%)

##### B. 기술지표 기반
4. **RSI 과매수**
   - RSI > 70
   - 파라미터: overbought_level(70)

5. **이동평균 데드 크로스**
   - 단기 MA가 장기 MA 하향 돌파
   - 파라미터: short_period, long_period

6. **볼린저 밴드 상단**
   - 가격이 상단 밴드 터치/돌파
   - 파라미터: period, std_dev

7. **MACD 데드 크로스**
   - MACD 선이 시그널 선 하향 돌파
   - 파라미터: fast, slow, signal

##### C. 동적 전략
8. **트레일링 스탑**
   - 최고가 대비 -N% 하락 시
   - 파라미터: trailing_pct(-2%, -3%)

9. **ATR 기반 동적 손절**
   - 변동성 고려 손절가
   ```python
   stop_loss = entry_price - (ATR * multiplier)
   ```
   - 파라미터: atr_period(14), atr_multiplier(2.0)

10. **시간 기반**
    - 보유 기간 경과 시 자동 매도
    - 파라미터: holding_days

##### D. 복합 전략
11. **멀티 조건 (OR 조합)**
    - (목표 수익) OR (RSI 과매수) OR (손절)
    - 파라미터: conditions, combination_mode

12. **하이브리드 스코어링**
    - 각 지표별 매도 점수 산출 후 가중 평균
    - 파라미터: indicator_weights, sell_threshold

#### 구현 클래스
- `domain/strategies/exit/base_exit.py`
- `domain/strategies/exit/fixed_target_exit.py`
- `domain/strategies/exit/ladder_exit.py`
- `domain/strategies/exit/stop_loss_exit.py`
- `domain/strategies/exit/rsi_exit.py`
- `domain/strategies/exit/ma_cross_exit.py`
- `domain/strategies/exit/bollinger_exit.py`
- `domain/strategies/exit/trailing_stop_exit.py`
- `domain/strategies/exit/atr_stop_exit.py`
- `domain/strategies/exit/time_based_exit.py`
- `domain/strategies/exit/multi_condition_exit.py`
- `domain/strategies/exit/hybrid_exit.py`

---

### 5. 매도/매수 평가 프로세스

#### A. 내부 평가 방법 (기술지표 기반)
전략 내부에서 기술지표를 계산하여 평가
```python
# 예: RSI 전략 내부 평가
def evaluate(self, ohlcv_data):
    rsi = self.calculate_rsi(ohlcv_data)
    if rsi < self.oversold:
        return Signal.BUY, confidence=0.8
    elif rsi > self.overbought:
        return Signal.SELL, confidence=0.8
    else:
        return Signal.HOLD, confidence=0.5
```

#### B. AI 평가 방법 (Claude API 통합)
**토큰 최소화를 위한 차트 데이터 및 기술지표 전달**

##### 1. 데이터 요약 및 압축
```python
# 최소 정보만 전달 (토큰 절약)
summary = {
    "symbol": "KRW-BTC",
    "timeframe": "1h",
    "current_price": 85000000,
    "price_change_24h": 2.5,  # %
    "recent_candles": [  # 최근 20개만
        {"time": "2025-01-01 10:00", "open": 84500000, "close": 85000000, "volume": 1234},
        # ...
    ],
    "indicators": {
        "rsi": 65.5,
        "macd": {"value": 150000, "signal": 120000},
        "bb": {"upper": 86000000, "middle": 85000000, "lower": 84000000},
        "ma_20": 84800000,
        "volume_ratio": 1.8
    }
}
```

##### 2. Claude API 호출
```python
import anthropic

client = anthropic.Anthropic(api_key=settings.claude_api_key)

prompt = f"""
당신은 암호화폐 전문 트레이더입니다.
다음 데이터를 분석하여 매수/매도 신호를 평가해주세요.

{json.dumps(summary, indent=2, ensure_ascii=False)}

현재 전략 신호:
- RSI 전략: 매수 (확신도 70%)
- 볼린저 밴드: 중립 (확신도 50%)

JSON 형식으로 답변:
{{
  "recommendation": "buy|sell|hold",
  "confidence": 75,
  "reasoning": "...",
  "warnings": "..."
}}
"""

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}]
)

ai_eval = json.loads(response.content[0].text)
```

##### 3. 전략 신호 + AI 평가 통합
```python
# 가중 평균
final_confidence = (
    strategy_confidence * 0.6 +
    ai_eval["confidence"] / 100 * 0.4
)

# 불일치 시 경고
if ai_eval["recommendation"] != strategy_signal:
    logger.warning(f"AI와 전략 불일치: {strategy_signal} vs {ai_eval['recommendation']}")
```

#### 토큰 최적화 전략
1. **데이터 압축**: 최근 20-50개 캔들만, 요약 통계 활용
2. **배치 평가**: 여러 종목 한 번에
3. **캐싱**: 동일 시간대 결과 재사용
4. **조건부 호출**: 중요한 결정 시점에만 (큰 금액, 불일치 시)

#### 구현 클래스
- `infrastructure/ai/claude_client.py`
- `infrastructure/ai/data_summarizer.py`
- `infrastructure/ai/evaluation_cache.py`
- `application/services/ai_evaluation_service.py`

---

## 디렉토리 구조 (Phase 6 확장)

```
BTS/
├── domain/
│   └── strategies/
│       ├── screening/          # 종목선정 (Phase 6)
│       │   ├── base_screening.py
│       │   ├── momentum_screening.py
│       │   ├── volume_screening.py
│       │   ├── technical_screening.py
│       │   └── hybrid_screening.py
│       │
│       ├── entry/              # 매수 (Phase 6)
│       │   ├── base_entry.py
│       │   ├── rsi_entry.py
│       │   ├── ma_cross_entry.py
│       │   ├── bollinger_entry.py
│       │   ├── macd_entry.py
│       │   ├── stochastic_entry.py
│       │   ├── multi_indicator_entry.py
│       │   └── hybrid_entry.py
│       │
│       ├── exit/               # 매도 (Phase 6)
│       │   ├── base_exit.py
│       │   ├── fixed_target_exit.py
│       │   ├── ladder_exit.py
│       │   ├── stop_loss_exit.py
│       │   ├── rsi_exit.py
│       │   ├── ma_cross_exit.py
│       │   ├── bollinger_exit.py
│       │   ├── trailing_stop_exit.py
│       │   ├── atr_stop_exit.py
│       │   ├── time_based_exit.py
│       │   ├── multi_condition_exit.py
│       │   └── hybrid_exit.py
│       │
│       └── portfolio/          # 포트폴리오 (Phase 6)
│           ├── base_portfolio.py
│           ├── equal_weight.py
│           ├── proportional_weight.py
│           ├── kelly_criterion.py
│           ├── risk_parity.py
│           └── dynamic_allocation.py
│
├── infrastructure/
│   └── ai/                     # AI 통합 (Phase 6)
│       ├── claude_client.py
│       ├── data_summarizer.py
│       └── evaluation_cache.py
│
└── application/services/       # 서비스 (Phase 6)
    ├── screening_service.py
    ├── entry_service.py
    ├── exit_service.py
    ├── portfolio_service.py
    └── ai_evaluation_service.py
```

---

## 구현 순서

### Phase 0~5: 완료 ✅
- Phase 0: 프로젝트 기반 (완료)
- Phase 1: 데이터 계층 (완료)
- Phase 2: 도메인 계층 (완료)
- Phase 3: 애플리케이션 계층 (완료)
- Phase 4: UI 계층 (완료)
- Phase 5: 고급 기능 - 백테스팅, MA Cross, Bollinger (완료)

### Phase 6: 프로페셔널 전략 시스템 🚀

#### 6.1 종목선정 전략
1. `domain/strategies/screening/base_screening.py`
2. `domain/strategies/screening/momentum_screening.py`
3. `domain/strategies/screening/volume_screening.py`
4. `domain/strategies/screening/technical_screening.py`
5. `domain/strategies/screening/hybrid_screening.py`
6. `application/services/screening_service.py`

#### 6.2 매수/매도 전략 확장
7. `domain/strategies/entry/macd_entry.py`
8. `domain/strategies/entry/stochastic_entry.py`
9. `domain/strategies/entry/multi_indicator_entry.py`
10. `domain/strategies/entry/hybrid_entry.py`
11. `application/services/entry_service.py`

12. `domain/strategies/exit/fixed_target_exit.py`
13. `domain/strategies/exit/ladder_exit.py`
14. `domain/strategies/exit/trailing_stop_exit.py`
15. `domain/strategies/exit/atr_stop_exit.py`
16. `domain/strategies/exit/multi_condition_exit.py`
17. `domain/strategies/exit/hybrid_exit.py`
18. `application/services/exit_service.py`

#### 6.3 포트폴리오 전략
19. `domain/entities/portfolio.py`
20. `domain/strategies/portfolio/base_portfolio.py`
21. `domain/strategies/portfolio/equal_weight.py`
22. `domain/strategies/portfolio/proportional_weight.py`
23. `domain/strategies/portfolio/kelly_criterion.py`
24. `domain/strategies/portfolio/risk_parity.py`
25. `domain/strategies/portfolio/dynamic_allocation.py`
26. `infrastructure/repositories/portfolio_repository.py`
27. `application/services/portfolio_service.py`

#### 6.4 AI 평가 시스템
28. `infrastructure/ai/claude_client.py`
29. `infrastructure/ai/data_summarizer.py`
30. `infrastructure/ai/evaluation_cache.py`
31. `application/services/ai_evaluation_service.py`

#### 6.5 UI 확장
32. `presentation/pages/6_Screening.py`
33. `presentation/pages/7_Portfolio.py`

#### 6.6 문서화
34. `docs/strategy_guide.md`
35. `docs/api_reference.md`

---

## 전략 조합 패턴 예시

### 패턴 1: 보수적 장기 투자
```yaml
screening: momentum_screening (top 5)
entry: ma_cross (골든 크로스)
portfolio: equal_weight
exit: fixed_target (목표 +20%, 손절 -5%)
```

### 패턴 2: 공격적 스윙 트레이딩
```yaml
screening: hybrid_screening (모멘텀 + 거래량)
entry: hybrid_entry (RSI + 볼린저 + MACD)
portfolio: kelly_criterion
exit: trailing_stop (최고가 대비 -3%)
```

### 패턴 3: AI 보조 단타
```yaml
screening: volume_screening (거래량 급증 top 3)
entry: multi_indicator + AI 평가
portfolio: risk_parity
exit: multi_condition (목표 +5% OR 손절 -2% OR 시간 4시간)
```

---

## 요구사항

1. Python 3.11+ (현재 3.13.7)
2. Pydantic, Streamlit, pandas, plotly
3. 클린 아키텍처 원칙 준수
4. 타입 힌팅, 한글 주석/docstring
5. Claude AI API 키 (AI 평가용)

---

## 세부 기능 체크리스트

### Phase 0-5: 완료 ✅
- [x] 가상지갑 시스템
- [x] 주문 관리
- [x] RSI, MA Cross, Bollinger 전략
- [x] 백테스팅 (슬리피지, 샤프 비율, MDD)
- [x] 대시보드, 전략 설정, 가상지갑, 백테스트 페이지

### Phase 6: 프로페셔널 전략 시스템 🚀

#### 6.1 종목선정 (Screening)
- [ ] KRW/BTC 시장 유니버스 관리
- [ ] 모멘텀 기반 스크리닝
- [ ] 거래량 기반 스크리닝
- [ ] 기술지표 복합 스크리닝
- [ ] 하이브리드 스크리닝 (가중치)
- [ ] 상위 N개 종목 자동 선정

#### 6.2 매수 (Entry)
- [x] RSI, MA Cross, Bollinger (Phase 2, 5)
- [ ] MACD, 스토캐스틱, ADX
- [ ] 멀티 지표 복합
- [ ] 하이브리드 스코어링

#### 6.3 포트폴리오 (Portfolio)
- [ ] 균등 배분
- [ ] 비율 배분
- [ ] 켈리 기준
- [ ] 리스크 패리티
- [ ] 동적 배분
- [ ] 주기적/임계값 리밸런싱

#### 6.4 매도 (Exit)
- [ ] 고정 목표가, 단계별 익절, 손절
- [ ] RSI 과매수, MA 데드 크로스, 볼린저 상단
- [ ] 트레일링 스탑, ATR 손절
- [ ] 멀티 조건, 하이브리드

#### 6.5 AI 평가
- [ ] Claude API 통합
- [ ] 차트 데이터 요약
- [ ] 토큰 최적화
- [ ] 평가 결과 캐싱

#### 6.6 UI
- [ ] 종목선정 페이지
- [ ] 포트폴리오 관리 페이지

---

## 시작

현재 Phase 0~5 완료.
다음은 **Phase 6: 프로페셔널 전략 시스템** 구현.
첫단계로 6.1 종목선정 전략부터 단계적으로 시작

---
