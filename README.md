# BTS - Bitcoin Auto Trading System

클린 아키텍처 기반 비트코인 자동매매 시스템

## 🎯 주요 기능

- 📊 **모의투자 전용 가상지갑** - 안전한 테스트 환경
- 🎯 **다양한 전략** - RSI, MA Cross, Bollinger 등
- 📈 **백테스팅** - 과거 데이터 기반 전략 검증
- 🔄 **실시간 트레이딩** - Upbit 거래소 연동
- 📉 **성과 분석** - 실시간 수익률 및 리스크 분석
- 🌐 **웹 UI** - Streamlit 기반 직관적 인터페이스

## 🏗️ 아키텍처

클린 아키텍처 원칙을 따라 계층 분리:

```
BTS/
├── core/                   # 핵심 모델 및 예외
├── domain/                 # 도메인 엔티티 및 전략
├── infrastructure/         # DB, 거래소 API 등 인프라
├── application/            # 비즈니스 로직 (서비스)
├── presentation/           # UI 계층 (Streamlit)
└── utils/                  # 유틸리티
```

### 계층별 역할

1. **Core** - 공통 모델, 열거형, 예외 처리
2. **Domain** - 비즈니스 도메인 로직 (Wallet, Order, Strategy 등)
3. **Infrastructure** - 외부 시스템 연동 (DB, Upbit API)
4. **Application** - 서비스 레이어 (FastAPI 재사용 가능)
5. **Presentation** - UI (Streamlit → FastAPI 전환 용이)

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# Python 3.11+ 필요
python3 --version

# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate    # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
# UPBIT_ACCESS_KEY=your_access_key
# UPBIT_SECRET_KEY=your_secret_key
```

### 3. 데이터베이스 초기화

```bash
# Alembic 마이그레이션 실행
alembic upgrade head
```

### 4. Streamlit 실행

```bash
# Streamlit 앱 실행
streamlit run presentation/streamlit_app.py
```

브라우저에서 http://localhost:8501 접속

## 📱 UI 페이지

### 1. 홈 (streamlit_app.py)
- 지갑 선택 및 전환
- 빠른 주문 생성
- 활성 전략 모니터링
- 최근 거래 내역

### 2. 대시보드 (1_Dashboard.py)
- 지갑 현황 및 수익률
- 트레이딩 통계
- 활성 전략 및 시그널
- 가격 차트 및 수익 차트

### 3. 전략 설정 (2_Strategy_Settings.py)
- 전략 생성/수정/삭제
- 전략 활성화/비활성화
- 전략 시그널 테스트

### 4. 가상지갑 (3_Virtual_Wallet.py)
- 가상지갑 생성 및 관리
- 입출금 처리
- 주문 생성 및 실행
- 보유 자산 조회

### 5. 백테스팅 (4_Backtest.py)
- 전략 백테스팅 (구현 예정)
- 성과 지표 분석
- 벤치마크 비교

## 🎯 전략 시스템

### 지원 전략

1. **RSI 전략** (domain/strategies/rsi_strategy.py)
   - 과매도/과매수 구간 감지
   - 확신도 기반 시그널 생성

2. **이동평균 교차** (구현 예정)
   - 골든크로스/데드크로스

3. **볼린저 밴드** (구현 예정)
   - 밴드 이탈 감지

### 전략 추가 방법

```python
from domain.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def calculate_indicators(self, ohlcv_data):
        # 지표 계산
        pass

    def generate_signal(self, symbol, ohlcv_data, indicators):
        # 시그널 생성
        pass
```

## 🔧 서비스 사용법

### 지갑 서비스

```python
from application.services.wallet_service import WalletService

wallet_service = WalletService(db)

# 가상지갑 생성
wallet = wallet_service.create_wallet(wallet_data)

# 입금
wallet = wallet_service.deposit(wallet_id, amount)

# 자산 조회
holdings = wallet_service.get_asset_holdings(wallet_id)
```

### 트레이딩 서비스

```python
from application.services.trading_service import TradingService

trading_service = TradingService(db, exchange)

# 주문 생성
order = trading_service.create_order(order_data)

# 주문 실행 (모의투자는 즉시 체결)
order = trading_service.execute_order(order.id)
```

### 전략 서비스

```python
from application.services.strategy_service import StrategyService

strategy_service = StrategyService(db, exchange)

# 전략 생성
strategy = strategy_service.create_strategy(strategy_data)

# 전략 활성화
strategy = strategy_service.activate_strategy(strategy_id)

# 시그널 생성
signal = strategy_service.generate_signal(strategy_id, symbol)
```

## 📊 데이터베이스

SQLite (로컬) → PostgreSQL (프로덕션) 전환 가능

### 테이블 구조

- **wallets** - 지갑 (가상/실거래)
- **orders** - 주문
- **trades** - 거래 내역
- **strategies** - 전략
- **positions** - 포지션
- **asset_holdings** - 자산 보유
- **transactions** - 거래 기록

### 마이그레이션

```bash
# 새 마이그레이션 생성
alembic revision --autogenerate -m "description"

# 마이그레이션 실행
alembic upgrade head

# 롤백
alembic downgrade -1
```

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 확인
pytest --cov=. --cov-report=html
```

## 📝 로깅

Loguru 기반 구조화된 로깅:

```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("메시지")
logger.error("오류", exc_info=True)
```

로그 위치: `logs/bts_{날짜}.log`

## 🔐 보안

1. **.env 파일** - API 키 등 민감정보 저장 (Git 제외)
2. **가상지갑 우선** - 실거래 전 충분한 테스트
3. **API 키 권한** - 최소 권한 원칙

## 🚧 구현 예정

- [ ] 백테스팅 엔진 고도화
- [ ] 추가 전략 (MA Cross, Bollinger, MACD)
- [ ] 하이브리드 전략
- [ ] 슬리피지 모델링
- [ ] 포트폴리오 최적화
- [ ] FastAPI 마이그레이션
- [ ] WebSocket 실시간 데이터

## 📚 기술 스택

- **Python 3.13**
- **Streamlit** - UI 프레임워크
- **FastAPI** - REST API (예정)
- **SQLAlchemy** - ORM
- **Alembic** - DB 마이그레이션
- **Pydantic** - 데이터 검증
- **pyupbit** - Upbit API
- **pandas** - 데이터 분석
- **plotly** - 차트 시각화
- **ta** - 기술적 지표

## 📄 라이선스

MIT License

## 🤝 기여

Pull Request 환영합니다!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 문의

프로젝트 관련 문의: [이슈 등록](https://github.com/yourusername/BTS/issues)

---

⚠️ **면책 조항**: 이 시스템은 교육 및 연구 목적으로 제작되었습니다. 실제 투자에 사용 시 발생하는 손실에 대해 책임지지 않습니다.
