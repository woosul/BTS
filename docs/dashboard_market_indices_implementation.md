# Dashboard 마켓 지수 구현 완료 보고서

## 📊 구현 내용

### 1. 글로벌 종합지수 (CoinGecko API)

#### 구현된 지표
- **총 시가총액**: USD/KRW 단위로 24시간 변화율 포함
- **24시간 거래량**: USD/KRW 단위
- **BTC 도미넌스**: 비트코인 시장 점유율
- **활성 코인 수**: 전체 활성화된 암호화폐 수

#### 위치
- `Dashboard.py` 상단 섹션
- 4열 메트릭 카드로 표시

### 2. 업비트 종합지수

#### 구현된 지수
- **UBCI** (업비트 종합지수): 업비트 전체 시장 대표 지수
- **UBMI** (업비트 알트코인 지수): 비트코인 제외 알트코인 지수
- **UB10** (업비트 10): 시가총액 상위 10개 코인 지수
- **UB30** (업비트 30): 시가총액 상위 30개 코인 지수

#### 특징
- 실시간 가격, 변화량, 변화율 표시
- 웹 스크래핑을 통한 업비트 공식 데이터 수집
- 4열 메트릭 카드로 표시

#### 위치
- 글로벌 지수 바로 아래
- 각 지수별 상세 설명 툴팁 포함

### 3. 7일 평균 지표 (상위 코인 분석)

#### 구현된 평균 지표
- **평균 변화율**: 상위 10개 코인의 7일 평균 가격 변화율
- **평균 시가총액**: 상위 10개 코인의 평균 시가총액
- **상승 코인 수**: 7일간 상승한 코인 개수
- **하락 코인 수**: 7일간 하락한 코인 개수

#### 특징
- CoinGecko API의 sparkline 데이터 활용
- 5분 캐싱으로 API 요청 최적화
- 시장 전반 트렌드 파악 용이

#### 위치
- "상위 코인 7일 추세" 섹션 내부
- 개별 코인 추세 차트 위에 배치

### 4. 개별 코인 7일 추세 차트

#### 구현 사항
- 상위 5개 코인의 sparkline 차트
- 가격, 변화율, 미니 라인 차트 표시
- 상승/하락에 따른 색상 구분 (초록/빨강)

---

## 🔧 기술 구현

### 서비스 레이어 (`market_index_service.py`)

#### 주요 메서드

1. **`get_global_crypto_data()`**
   ```python
   # 반환 데이터
   {
       'total_market_cap_usd': float,
       'total_market_cap_krw': float,
       'market_cap_change_24h': float,
       'total_volume_usd': float,
       'total_volume_krw': float,
       'btc_dominance': float,
       'eth_dominance': float,
       'volume_to_market_cap_ratio': float,
       'active_cryptocurrencies': int,
       'markets': int,
       'timestamp': datetime
   }
   ```

2. **`get_upbit_indices()`**
   ```python
   # 반환 데이터
   {
       'ubci': {'value': float, 'change': float, 'change_rate': float},
       'ubmi': {'value': float, 'change': float, 'change_rate': float},
       'ub10': {'value': float, 'change': float, 'change_rate': float},
       'ub30': {'value': float, 'change': float, 'change_rate': float},
       'timestamp': datetime
   }
   ```

3. **`get_top_coins_with_sparkline(limit=10)`**
   ```python
   # 반환 데이터 (리스트)
   [
       {
           'id': str,
           'symbol': str,
           'name': str,
           'current_price': float,
           'market_cap': float,
           'market_cap_rank': int,
           'price_change_percentage_24h': float,
           'price_change_percentage_7d': float,
           'sparkline_in_7d': [float]  # 7일 가격 데이터 168개 포인트
       }
   ]
   ```

4. **`calculate_7day_averages(sparkline_data)`** ⭐ 신규
   ```python
   # 반환 데이터
   {
       'avg_price_change_7d': float,
       'avg_market_cap': float,
       'positive_coins': int,
       'negative_coins': int
   }
   ```

### 프레젠테이션 레이어 (`Dashboard.py`)

#### 구조
```
Dashboard
├── 글로벌 암호화폐 시장
│   ├── 총 시가총액 (24h 변화)
│   ├── 24h 거래량
│   ├── BTC 도미넌스
│   └── 활성 코인 수
│
├── 상위 코인 7일 추세
│   ├── 7일 평균 지표 ⭐ 신규
│   │   ├── 평균 변화율
│   │   ├── 평균 시가총액
│   │   ├── 상승 코인 수
│   │   └── 하락 코인 수
│   └── 개별 코인 차트 (5개)
│
├── 업비트 종합지수 ⭐ 신규
│   ├── UBCI (업비트 종합지수)
│   ├── UBMI (알트코인 지수)
│   ├── UB10 (시총 상위 10)
│   └── UB30 (시총 상위 30)
│
└── [기존 Dashboard 컨텐츠]
    ├── 지갑 현황
    ├── 거래 통계
    ├── 차트
    └── 거래 내역
```

---

## 📈 데이터 소스

### CoinGecko API
- **엔드포인트**: 
  - `/api/v3/global` - 글로벌 시장 데이터
  - `/api/v3/coins/markets` - 개별 코인 데이터 + sparkline
- **Rate Limit**: 초당 50 요청
- **대응**: 20ms 간격 보장, 5분 캐싱

### 업비트
- **엔드포인트**: `https://www.upbit.com/trends`
- **방식**: Next.js `__NEXT_DATA__` 스크래핑
- **데이터**: UBCI, UBMI, UB10, UB30 실시간 지수

---

## 🎯 주요 기능

### 캐싱 최적화
```python
@st.cache_data(ttl=300)  # 5분 캐시
def get_cached_sparkline_data():
    return market_index_service.get_top_coins_with_sparkline(limit=10)
```
- API 호출 최소화
- 페이지 로딩 속도 향상
- Rate limit 대응

### 에러 핸들링
- 각 섹션별 독립적인 try-except 블록
- API 실패 시 빈 데이터 또는 정보 메시지 표시
- 로깅을 통한 디버깅 지원

### 시각화
- **Plotly** 기반 sparkline 차트
- 상승/하락 색상 구분
- Streamlit 메트릭 카드의 delta 기능 활용

---

## 🔍 테스트

### 테스트 파일
- `test_market_indices.py`: 마켓 지수 서비스 단위 테스트
- 글로벌 데이터 및 업비트 지수 출력 확인

### 실행 방법
```bash
python test_market_indices.py
```

---

## 📝 수정된 파일

### 1. `application/services/market_index_service.py`
- ✅ `get_global_crypto_data()` 반환 키 수정 (호환성)
- ✅ `calculate_7day_averages()` 메서드 추가
- ✅ KRW 시가총액/거래량 추가
- ✅ 마켓 수 정보 추가

### 2. `presentation/pages/Dashboard.py`
- ✅ 업비트 종합지수 섹션 추가
- ✅ 7일 평균 지표 표시 추가
- ✅ sparkline 데이터를 10개로 확대
- ✅ 평균 지표 4개 메트릭 추가

---

## 🚀 다음 단계 제안

### 단기 개선
1. **업비트 지수 히스토리 저장**
   - DB에 시계열 데이터 저장
   - 트렌드 차트 생성

2. **알림 기능**
   - 특정 지수 변화 시 알림
   - 급등/급락 감지

3. **비교 분석**
   - 업비트 vs 글로벌 시장 비교
   - 김치 프리미엄 계산

### 중장기 개선
1. **추가 지수 통합**
   - 빗썸, 코인원 등 다른 거래소 지수
   - Fear & Greed Index
   - 온체인 지표 (거래량, 활성 주소 등)

2. **AI 분석 연동**
   - 지수 기반 시장 전망
   - 매수/매도 시그널 생성

3. **대시보드 커스터마이징**
   - 사용자별 관심 지표 선택
   - 레이아웃 조정 기능

---

## ✅ 완료 체크리스트

- [x] 글로벌 종합지수 표시
- [x] 업비트 종합지수 (UBCI, UBMI, UB10, UB30) 표시
- [x] 7일 평균 지표 계산 및 표시
- [x] 개별 코인 sparkline 차트
- [x] API 캐싱 최적화
- [x] 에러 핸들링
- [x] 서비스 레이어 구현
- [x] 테스트 코드 작성
- [x] 문서화

---

## 💡 알려진 이슈

### 업비트 지수 스크래핑
- Next.js 구조 변경 시 파싱 실패 가능성
- 대응: `_extract_indices_from_nextjs()` 메서드에서 여러 경로 시도

### CoinGecko Rate Limit
- 무료 API는 초당 30 요청 제한
- 대응: 20ms 간격 보장 + 5분 캐싱

---

## 📞 문의 및 지원

구현 관련 문의사항이나 추가 개선사항이 있으시면 말씀해 주세요!

---

**작성일**: 2025-10-12
**버전**: 1.0.0
**상태**: ✅ 완료
