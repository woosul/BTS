# 프로젝트 : BTS - Bitcoin Auto Trading System

## 개요
이 파일은 이 저장소에서 작업할 때 Claude Code (claude.ai/code)에 대한 가이드를 제공합니다.


## 미션
FastAPI로 쉽게 전환 가능한 클린 아키텍처 기반 비트코인 자동매매 시스템을 구축하세요.

## 주요 기능
- 모의투자 전용 가상지갑 시스템
- 다양한 전략 플러그인 구조
- 모의투자를 통한 다양한 전략 테스트 및 성과 관리
- 단일전략, 복합전략 및 하이브리드 전략 시험 지원
- 전략에 대한 성과기반 실거래 전환 적용 지원
- 거래소와 실거래용 지갑 동기화
- Upbit 거래소 우선 지원 (추후 확장 가능) - pyupbit 사용 우선하며, BTC 시장기반 거래를 위한 REST API 래퍼 작성

## 핵심 원칙
1. 비즈니스 로직과 UI 완전 분리
2. Service Layer는 FastAPI에서 재사용
3. Repository 패턴으로 데이터 계층 추상화
4. Pydantic으로 타입 안정성
5. 의존성 주입으로 테스트 용이성
6. SQLite로 시작해 PostgreSQL로 확장 용이 (Service → Repository → DB (계층 분리))
7. Streamlit 기반 웹 UI

## 아키텍처 계층 설명
### 1. Core Layer (핵심 계층)
- **models.py**: Pydantic DTO (Data Transfer Object) - API 요청/응답 모델
- **enums.py**: 열거형 상수 (OrderType, OrderStatus, TradingMode 등)
- **exceptions.py**: 커스텀 예외 클래스

### 2. Domain Layer (도메인 계층)
- **entities/**: 비즈니스 엔티티 (Wallet, Order, Trade)
- **strategies/**: 트레이딩 전략 (RSI, MA Cross, Bollinger 등)

### 3. Infrastructure Layer (인프라 계층)
- **database/models.py**: SQLAlchemy ORM 모델 (DB 테이블 매핑)
- **repositories/**: 데이터 저장소 패턴 구현
- **exchanges/**: 외부 거래소 API 클라이언트

### 4. Application Layer (애플리케이션 계층)
- **services/**: 비즈니스 로직 조합 (Streamlit/FastAPI 공통 사용)

### 5. Presentation Layer (표현 계층)
- **streamlit_app.py**: UI 진입점 (FastAPI로 교체 예정)

## 모델 구분 명확화
```python
# core/models.py - Pydantic DTO (API 계층)
class OrderCreate(BaseModel):
    symbol: str
    order_type: OrderType
    quantity: Decimal

# infrastructure/database/models.py - SQLAlchemy ORM (DB 계층)
class OrderORM(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
```

## 디렉토리 구조
BTS/
├── README.md
├── requirements.txt
├── .env
├── config/
│   ├── __init__.py
│   └── settings.py                    # 환경설정 (재사용)
├── core/
│   ├── __init__.py
│   ├── models.py                      # 데이터 모델 (재사용)
│   ├── enums.py                       # 열거형 (재사용)
│   └── exceptions.py                  # 예외 처리 (재사용)
├── data/
│   ├── data.db                       # SQLite DB 파일 
│   └── sample_data.csv               # 샘플 데이터
├── domain/
│   ├── __init__.py
│   ├── entities/                      # 도메인 엔티티 (재사용)
│   │   ├── __init__.py
│   │   ├── order.py
│   │   ├── trade.py
│   │   └── wallet.py
│   └── strategies/                    # 전략 (재사용)
│       ├── __init__.py
│       ├── base_strategy.py
│       ├── rsi_strategy.py
│       ├── ma_cross_strategy.py
│       └── bollinger_strategy.py
├── infrastructure/
│   ├── __init__.py
│   ├── database/                      # DB (재사용)
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   ├── repositories/                  # 저장소 (재사용)
│   │   ├── __init__.py
│   │   ├── trade_repository.py
│   │   ├── order_repository.py
│   │   └── wallet_repository.py
│   └── exchanges/                     # 거래소 API (재사용)
│       ├── __init__.py
│       ├── base_exchange.py
│       ├── bithumb_client.py
│       └── upbit_client.py
├── application/
│   ├── __init__.py
│   └── services/                      # 서비스 (FastAPI에서 재사용)
│       ├── __init__.py
│       ├── trading_service.py
│       ├── strategy_service.py
│       ├── backtest_service.py
│       └── wallet_service.py
├── presentation/
│   ├── __init__.py
│   ├── streamlit_app.py              # Streamlit 진입점 (교체 예정)
│   ├── pages/                         # Streamlit 페이지 (교체 예정)
│   │   ├── 1_Dashboard.py
│   │   ├── 2_Strategy_Settings.py
│   │   ├── 3_Virtual_Wallet.py
│   │   ├── 4_Backtest.py
│   │   └── 5_Analytics.py
│   └── components/                    # UI 컴포넌트 (교체 예정)
│       ├── __init__.py
│       ├── charts.py
│       ├── metrics.py
│       └── forms.py
├── utils/
│   ├── __init__.py
│   ├── logger.py                      # 로깅 (재사용)
│   ├── validators.py                  # 검증 (재사용)
│   └── helpers.py                     # 유틸리티 (재사용)
└── tests/
    ├── __init__.py
    ├── unit/
    ├── integration/
    └── fixtures/

## 구현 순서

### Phase 0: 프로젝트 기반 구축 (필수)
1. 디렉토리 구조 생성
2. config/settings.py - 환경설정 및 Pydantic Settings
3. utils/logger.py - Loguru 기반 로깅 설정
4. core/enums.py - 열거형 정의 (OrderType, OrderStatus, TradingMode 등)
5. core/exceptions.py - 커스텀 예외 클래스

### Phase 1: 데이터 계층 (수정)
6. core/models.py - Pydantic DTO (Request/Response 모델)
7. infrastructure/database/connection.py - SQLAlchemy 엔진 및 세션
8. infrastructure/database/models.py - SQLAlchemy ORM 모델
9. infrastructure/repositories/base.py - Repository 베이스 클래스
10. Alembic 초기화 및 첫 마이그레이션

### Phase 2: 도메인 계층
11. domain/entities/wallet.py - 지갑 엔티티
12. domain/entities/order.py - 주문 엔티티
13. domain/entities/trade.py - 거래 엔티티
14. domain/strategies/base_strategy.py - 전략 베이스 클래스
15. domain/strategies/rsi_strategy.py - RSI 전략 구현

### Phase 3: 애플리케이션 계층
16. application/services/wallet_service.py - 지갑 서비스
17. application/services/trading_service.py - 트레이딩 서비스
18. application/services/strategy_service.py - 전략 서비스
19. infrastructure/exchanges/base_exchange.py - 거래소 베이스
20. infrastructure/exchanges/upbit_client.py - Upbit API 클라이언트

### Phase 4: UI 계층
21. presentation/streamlit_app.py - Streamlit 진입점
22. presentation/pages/1_Dashboard.py - 대시보드
23. presentation/pages/2_Strategy_Settings.py - 전략 설정
24. presentation/pages/3_Virtual_Wallet.py - 가상지갑
25. presentation/pages/4_Backtest.py - 백테스팅
26. presentation/components/ - 재사용 UI 컴포넌트

### Phase 5: 고급 기능
27. application/services/backtest_service.py - 백테스팅 서비스
28. domain/strategies/ma_cross_strategy.py - 이동평균 교차 전략
29. domain/strategies/bollinger_strategy.py - 볼린저 밴드 전략
30. utils/validators.py - 데이터 검증 유틸리티

## 코드 스타일 예시
```python
# TradingService 예시
from typing import Optional
from core.models import OrderCreate, OrderResponse

class TradingService:
    """
    FastAPI에서도 재사용 가능한 트레이딩 서비스
    
    Streamlit: service.execute_trade(order)
    FastAPI: @app.post("/trade") -> service.execute_trade(order)
    """
    
    def __init__(
        self,
        order_repo: Optional[OrderRepository] = None
    ):
        self.order_repo = order_repo or OrderRepository()
    
    def execute_trade(self, order: OrderCreate) -> OrderResponse:
        # 비즈니스 로직 (UI 독립적)
        ...
```
## 요구사항

1. Python 3.11+ (현재 가상환경 3.13.7 사용)
2. Pydantic, Streamlit, pandas, plotly
3. 클린 아키텍처 원칙 준수
4. 모든 함수에 타입 힌팅
5. 한글 주석 및 docstring

## 데이터베이스 요구사항
1. SQLite로 시작해 PostgreSQL로 확장 용이
2. bts.db 파일로 로컬 저장
3. DB Lock 문제 방지
4. SQLAlchemy ORM 사용
   
## 세부 기능 체크리스트
1. 모의투자 전용 가상지갑 시스템
   - 잔고 조회
   - 입출금 관리
   - 거래 내역 추적
   - 수익 계산
2. 주문 관리
   - 매수/매도 주문
   - 주문 상태 관리
   - 주문 내역 조회
3. 거래 쌍 관리
   - 거래 쌍 추가/제거
   - 포지션 오픈/클로즈
   - 수익 계산
   - 거래 내역 추적
4. 전략 시스템
   - 전략 플러그인 관리 (p1)
   - RSI 전략(p1)
   - 전략 베이스 클래스 (p1)
   - 신호 생성 (p1)
   - 확신도 계산 (p1)
   - 이동평균 교차 전략 (p2)
   - 볼린저 밴드 전략 (p2)
   - MACD 전략 (p2)
   - 하이브리드 전략 (p2)
5. 설정 관리
   - 환경변수 관리
   - 모의/실전 모드
   - 로깅 설정
6. 실제 거래소 연동
   - Upbit API 클라이언트
   - 실시간 시세 조회
   - 매도/매수 주문
   - 잔고 조회
7. 백테스팅 고도화
   - 슬리피지 시뮬레이션
   - 샤프 비율 계산
   - 벤치마크 비교
8. 보고서 및 분석
   - 거래 내역 리포트
   - 전략 성과 리포트
   - 시각화 대시보드
9. 추가 UI 페이지
   - 전략 설정 페이지
   - 가상지갑 페이지
   - 백테스트 페이지
   - 분석 페이지

## 시작
지금 구현을 시작해주세요!
우선 Phase 0부터 진행합니다.

---
