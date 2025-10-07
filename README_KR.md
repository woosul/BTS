# BTS - 비트코인 자동매매 시스템

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 클린 아키텍처 기반 프로페셔널급 비트코인 자동매매 시스템

[English](README.md) | [전략 가이드](docs/strategy_guide.md) | [API 레퍼런스](docs/api_reference.md)

## 개요

BTS는 클린 아키텍처 원칙으로 설계된 프로페셔널 비트코인 자동매매 시스템으로, 다음 기능을 제공합니다:

- **가상지갑 시스템** : 안전한 모의투자 환경
- **4단계 전략 프레임워크** : 종목선정 → 매수 → 포트폴리오 → 매도
- **AI 기반 평가** : Claude & OpenAI 통합 시그널 검증
- **종합 백테스팅** : 슬리피지 & 샤프 비율 포함 과거 성과 분석
- **다중 거래소 지원** : Upbit 우선 (확장 가능한 아키텍처)

## 주요 기능

### 트레이딩 전략

#### 1. 종목선정 전략 (Screening)
KRW/BTC 시장에서 투자 가치 높은 종목 자동 선별:
- **모멘텀 기반** : 가격 변동률, 거래량 증가율, RSI 모멘텀
- **거래량 기반** : 거래량 급증 감지
- **기술지표 복합** : RSI + MACD + 이동평균 조합
- **하이브리드** : 여러 전략의 가중 조합

#### 2. 매수 전략 (Entry)
최적 진입 타이밍 포착 :
- **RSI** : 과매도 반등 감지
- **이동평균 교차** : 골든 크로스 신호
- **볼린저 밴드** : 하단 밴드 터치/돌파
- **MACD** : 골든 크로스 & 히스토그램 반전
- **스토캐스틱** : 과매도 %K/%D 교차
- **멀티 지표** : AND/OR 조합 모드

#### 3. 포트폴리오 전략
효율적 자금 배분:
- **균등 배분** : 모든 자산에 동일 금액
- **비율 배분** : 순위 기반 또는 사용자 지정 가중치
- **켈리 기준** : 수학적 최적 포지션 크기
- **리스크 패리티** : 역변동성 가중치
- **동적 배분** : 시장 상황 기반 조정

#### 4. 매도 전략 (Exit)
이익 실현 & 손실 최소화 :
- **고정 목표가** : 목표 수익 & 손절
- **단계별 익절** : 분할 매도
- **트레일링 스탑** : 최고가 추종 동적 손절
- **ATR 기반 손절** : 변동성 조정 손절
- **멀티 조건** : OR 조합 매도 신호

### AI 평가 시스템

**멀티 제공자 지원** : Claude (Anthropic) & OpenAI (GPT)

- **토큰 최적화** : 최근 20개 캔들 + 요약된 지표만 전송
- **Fallback 시스템** : 실패 시 자동 모델 전환
  - Claude: `claude-3-5-sonnet-20241022` → `claude-3-5-haiku-20241022`
  - OpenAI: `gpt-4o` → `gpt-4o-mini`
- **결과 캐싱** : 비용 절감을 위한 15분 TTL
- **시그널 결합** : 가중 평균 (전략 60% + AI 40%)

### 백테스팅 엔진

종합 성과 분석:
- **현실적 시뮬레이션** : 슬리피지 (0.1%) & 수수료 (0.05%)
- **성과 지표** : 샤프 비율, MDD, 승률, 손익비
- **시각적 분석** : 자산 곡선, 손실 차트, 거래 분포
- **전략 비교** : 여러 전략 나란히 비교

## 빠른 시작

### 사전 요구사항

- Python 3.11+
- Upbit API 키 (실거래용)
- Claude API 키 또는 OpenAI API 키 (AI 평가용)

### 설치

```bash
# 저장소 복제
git clone https://github.com/yourusername/BTS.git
cd BTS

# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 초기화
python -m infrastructure.database.init_db
```

### 설정

템플릿에서 `.env` 파일 생성:

```bash
cp .env.example .env
```

API 키로 `.env` 편집:

```bash
# Upbit API (모의투자는 선택사항)
UPBIT_ACCESS_KEY=your_access_key
UPBIT_SECRET_KEY=your_secret_key

# AI 제공자 선택
AI_PROVIDER=claude  # 또는 openai

# Claude API
CLAUDE_API_KEY=your_claude_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_FALLBACK_MODEL=claude-3-5-haiku-20241022

# OpenAI API
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
OPENAI_FALLBACK_MODEL=gpt-4o-mini

# 거래 모드
TRADING_MODE=paper  # paper 또는 live
INITIAL_BALANCE=10000000
```

### 애플리케이션 실행

```bash
# Streamlit 웹 인터페이스 시작
streamlit run presentation/streamlit_app.py

# 또는 특정 서비스 실행
python application/services/strategy_service.py
python application/services/screening_service.py
```

웹 인터페이스 접속: `http://localhost:8501`

## 사용 가이드

### 1. 가상지갑 생성

1. **가상지갑** 페이지로 이동
2. "지갑 생성" 클릭
3. 초기 잔액 설정 (기본값: 10,000,000 KRW)

### 2. 유망 종목 스크리닝

1. **종목선정** 페이지로 이동
2. 시장 선택 (KRW 또는 BTC)
3. 스크리닝 전략 선택
4. 파라미터 조정
5. "스크리닝 실행" 클릭
6. 상위 순위 종목 확인

### 3. 트레이딩 전략 설정

1. **전략 설정** 페이지 열기
2. 매수 전략 선택 (RSI, MACD 등)
3. 파라미터 설정
4. 전략 활성화
5. 대시보드에서 시그널 모니터링

### 4. 포트폴리오 배분

1. **포트폴리오** 페이지 방문
2. 지갑 선택
3. 배분 전략 선택
4. 종목 입력 (또는 스크리닝 결과 사용)
5. "배분 실행" 클릭
6. 분포 차트 확인

### 5. 성과 백테스팅

1. **백테스트** 페이지로 이동
2. 전략 선택
3. 날짜 범위 설정
4. 백테스트 실행
5. 지표 & 차트 분석

## 아키텍처

### 클린 아키텍처 계층

```
┌─────────────────────────────────────┐
│   Presentation Layer (Streamlit)    │  ← 사용자 인터페이스
├─────────────────────────────────────┤
│   Application Layer (Services)      │  ← 유스케이스
├─────────────────────────────────────┤
│   Domain Layer (Models/Strategies)  │  ← 비즈니스 로직
├─────────────────────────────────────┤
│   Infrastructure Layer              │  ← 외부 서비스
│   (Database, Exchange, AI APIs)     │
└─────────────────────────────────────┘
```

### 디렉토리 구조

```
BTS/
├── core/                   # 도메인 모델 & 열거형
│   ├── models.py
│   └── enums.py
├── domain/                 # 비즈니스 로직
│   ├── entities/
│   └── strategies/
│       ├── screening/      # 종목선정 전략
│       ├── entry/          # 매수 전략
│       ├── exit/           # 매도 전략
│       └── portfolio/      # 포트폴리오 전략
├── application/            # 유스케이스
│   └── services/
├── infrastructure/         # 외부 인터페이스
│   ├── database/
│   ├── exchanges/
│   └── ai/                 # AI 클라이언트
│       ├── claude_client.py
│       ├── openai_client.py
│       └── data_summarizer.py
├── presentation/           # UI 계층
│   ├── streamlit_app.py
│   ├── pages/
│   └── components/
└── utils/                  # 유틸리티
```

## 고급 설정

### 커스텀 전략 개발

베이스 전략 클래스를 상속하여 자신만의 전략 작성 :

```python
from domain.strategies.entry.base_entry import BaseEntryStrategy

class MyCustomEntry(BaseEntryStrategy):
    def check_entry_condition(self, ohlcv_data, indicators):
        # 사용자 로직
        return should_enter, confidence
```

### AI 제공자 전환

UI 또는 프로그래밍 방식으로 런타임 전환 :

```python
from application.services.ai_evaluation_service import AIEvaluationService

# Claude 사용
service = AIEvaluationService(provider="claude")

# 또는 OpenAI
service = AIEvaluationService(provider="openai")
```

## 성과 지표

백테스팅 엔진 계산 항목 :

- **총 수익률** : 전체 손익 백분율
- **샤프 비율** : 위험 조정 수익률
- **최대 손실폭 (MDD)** : 최고점-최저점 하락폭
- **승률** : 수익 거래 비율
- **손익비** : 평균 수익 vs 평균 손실
- **총 거래 수** : 실행된 거래 횟수

## 기여

기여를 환영합니다! 다음 단계를 따라주세요:

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 열기

## 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다 - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 면책 조항

**이 소프트웨어는 교육 및 연구 목적으로만 제공됩니다.**

- 암호화폐 거래는 상당한 위험을 수반합니다
- 과거 성과가 미래 결과를 보장하지 않습니다
- 실거래 전 충분한 테스트를 수행하세요
- 저자는 금전적 손실에 대해 책임지지 않습니다

## 감사의 말

- [Upbit](https://upbit.com/) - 한국 암호화폐 거래소
- [Anthropic Claude](https://www.anthropic.com/) - AI 평가
- [OpenAI](https://openai.com/) - AI 평가
- [Streamlit](https://streamlit.io/) - 웹 프레임워크

## 문의

질문이나 지원이 필요하시면 GitHub에 이슈를 등록해주세요.

---

**클린 아키텍처 원칙으로 실제 거래를 통한 최대의 수익을 목표로 하는 마음을 담아 제작**
