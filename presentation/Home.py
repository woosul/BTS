"""
BTS - Bitcoin Auto Trading System
Streamlit 메인 애플리케이션

모의투자 전용 자동매매 시스템의 웹 인터페이스
"""
import streamlit as st
from decimal import Decimal
from typing import Optional
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.database.connection import get_db_session
from application.services.wallet_service import WalletService
from application.services.trading_service import TradingService
from application.services.strategy_service import StrategyService
from infrastructure.exchanges.upbit_client import UpbitClient
from config.settings import settings
from utils.logger import get_logger
from presentation.components.cards import render_wallet_card

logger = get_logger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="BTS | Bitcoin Trading System",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 로고 설정
logo_path = str(project_root / "resource" / "image" / "peaknine_logo_01.svg")
icon_path = str(project_root / "resource" / "image" / "peaknine_02.png")
st.logo(
    image=logo_path,
    icon_image=icon_path
)

# 로고 크기 조정 및 메뉴 스타일
st.markdown("""
<style>
    /* Noto Sans KR 폰트 로드 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
    /* Bootstrap Icons 로드 */
    @import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');
    /* Material Icons 로드 */
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    /* 전체 폰트 적용 (아이콘 제외) */
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif !important;
    }

    /* Streamlit 내부 요소 폰트 적용 */
    p, h1, h2, h3, h4, h5, h6, label, input, textarea, select, button,
    [data-testid] div, [data-testid] span, [data-testid] p,
    .stMarkdown, .stText, .stCaption {
        font-family: 'Noto Sans KR', sans-serif !important;
    }

    /* Material Icons 요소는 원래 폰트 유지 */
    .material-symbols-outlined,
    [class*="material-icons"],
    span[data-testid*="stIcon"],
    button span,
    [role="button"] span {
        font-family: 'Material Symbols Outlined', 'Material Icons' !important;
    }

    /* 로고 영역 스타일 */
    [data-testid="stSidebarNav"] {
        padding-top: 0 !important;
        overflow: visible !important;
    }

    /* 사이드바 전체 overflow 허용 */
    section[data-testid="stSidebar"] {
        overflow: visible !important;
    }
    section[data-testid="stSidebar"] > div {
        overflow: visible !important;
    }

    /* 로고 컨테이너 */
    [data-testid="stSidebarNav"] > div:first-child {
        padding: 2.4rem 0.6rem !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        overflow: visible !important;
    }

    /* 로고 링크 영역 */
    [data-testid="stSidebarNav"] a {
        display: block !important;
        width: 100% !important;
        overflow: visible !important;
    }

    /* 로고 이미지 크기 - 1.6배 확대 (transform 사용) */
    [data-testid="stSidebarNav"] img {
        width: 100% !important;
        max-width: 100% !important;
        height: auto !important;
        transform: scale(1.6) !important;
        transform-origin: center center !important;
        margin: 0 !important;
    }

    /* 네비게이션 메뉴와 로고 사이 간격 */
    [data-testid="stSidebarNav"] ul {
        margin-top: 1rem !important;
    }

    /* 메뉴명 좌측 정렬 */
    [data-testid="stSidebarNav"] ul li a {
        text-align: left !important;
        justify-content: flex-start !important;
    }

    /* 선택된 메뉴 스타일 */
    [data-testid="stSidebarNav"] ul li a[aria-current="page"] {
        background-color: #54A0FD !important;
        font-weight: 600 !important;
        border-radius: 4px !important;
    }

    /* 페이지 폰트 및 여백 통일 */
    h1 {
        font-size: 1.8rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    h2 {
        font-size: 1.3rem !important;
        margin-top: 0.8rem !important;
        margin-bottom: 0.5rem !important;
    }
    h3 {
        font-size: 1.1rem !important;
        margin-top: 0.6rem !important;
        margin-bottom: 0.4rem !important;
    }
    hr {
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }

    /* 셀렉트박스 폰트 크기 조정 */
    [data-testid="stSelectbox"] label {
        font-size: 0.875rem !important;
    }
    [data-testid="stSelectbox"] div[data-baseweb="select"] {
        font-size: 0.875rem !important;
    }
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        font-size: 0.875rem !important;
    }

    /* 드롭다운 메뉴 폰트 크기 조정 */
    ul[role="listbox"] li {
        font-size: 0.875rem !important;
    }
    div[role="listbox"] div {
        font-size: 0.875rem !important;
    }

    /* 상단 더보기 메뉴 폰트 크기 */
    [data-testid="stAppViewBlockContainer"] button[kind="header"] {
        font-size: 0.875rem !important;
    }
    div[data-baseweb="popover"] ul li {
        font-size: 0.875rem !important;
    }
    div[data-baseweb="popover"] button {
        font-size: 0.875rem !important;
    }


</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
def init_session_state():
    """세션 상태 초기화"""
    if 'selected_wallet' not in st.session_state:
        st.session_state.selected_wallet = None

    if 'db_session' not in st.session_state:
        st.session_state.db_session = None

    if 'services_initialized' not in st.session_state:
        st.session_state.services_initialized = False

def get_services():
    """서비스 인스턴스 가져오기 (캐싱)"""
    if not st.session_state.services_initialized:
        try:
            # DB 세션 생성
            from infrastructure.database.connection import SessionLocal
            db = SessionLocal()
            st.session_state.db = db

            # 거래소 클라이언트
            exchange = UpbitClient(
                settings.upbit_access_key,
                settings.upbit_secret_key
            )

            # 서비스 초기화
            st.session_state.wallet_service = WalletService(db)
            st.session_state.trading_service = TradingService(db, exchange)
            st.session_state.strategy_service = StrategyService(db, exchange)

            st.session_state.services_initialized = True
            logger.info("서비스 초기화 완료")

        except Exception as e:
            logger.error(f"서비스 초기화 실패: {e}")
            st.error(f"서비스 초기화 실패: {e}")
            return None, None, None

    return (
        st.session_state.wallet_service,
        st.session_state.trading_service,
        st.session_state.strategy_service
    )

def main():
    """메인 페이지"""
    init_session_state()

    # 헤더
    st.title("BTS - Bitcoin Auto Trading System")
    st.markdown("---")

    # 서비스 초기화
    wallet_service, trading_service, strategy_service = get_services()

    if not wallet_service:
        st.error("서비스를 초기화할 수 없습니다. 설정을 확인하세요.")
        return

    # 사이드바: 지갑 선택
    with st.sidebar:
        st.subheader("설정")

        # 지갑 목록 조회
        try:
            wallets = wallet_service.get_all_wallets()

            if wallets:
                wallet_options = {
                    f"{w.name} ({w.wallet_type.value})": w.id
                    for w in wallets
                }

                selected_wallet_name = st.selectbox(
                    "지갑 선택",
                    options=list(wallet_options.keys()),
                    key="wallet_selector"
                )

                if selected_wallet_name:
                    st.session_state.selected_wallet = wallet_options[selected_wallet_name]

            else:
                st.warning("등록된 지갑이 없습니다.")
                if st.button("가상지갑 생성"):
                    from core.models import WalletCreate
                    from core.enums import WalletType

                    wallet_data = WalletCreate(
                        name="기본 가상지갑",
                        wallet_type=WalletType.VIRTUAL,
                        initial_balance=Decimal("10000000")
                    )
                    wallet = wallet_service.create_wallet(wallet_data)
                    st.success(f"지갑 생성: {wallet.name}")
                    st.rerun()

        except Exception as e:
            logger.error(f"지갑 목록 조회 실패: {e}")
            st.error(f"지갑 목록 조회 실패: {e}")

        st.markdown("---")

        # AI 설정
        st.subheader("AI 설정")

        # AI 제공자 선택
        current_provider = settings.ai_provider
        ai_provider = st.selectbox(
            "AI 제공자",
            options=["claude", "openai"],
            index=0 if current_provider == "claude" else 1,
            format_func=lambda x: "Claude (Anthropic)" if x == "claude" else "OpenAI (GPT)",
            key="ai_provider_selector",
            help="AI 평가에 사용할 제공자를 선택하세요"
        )

        # 세션 상태에 저장
        if 'ai_provider' not in st.session_state or st.session_state.ai_provider != ai_provider:
            st.session_state.ai_provider = ai_provider

        # 선택된 제공자의 모델 정보 표시
        if ai_provider == "claude":
            st.caption(f"모델: {settings.claude_model}")
            st.caption(f"Fallback: {settings.claude_fallback_model}")
            api_key_status = "✓" if settings.claude_api_key else "✗"
            st.caption(f"API 키: {api_key_status}")
        else:
            st.caption(f"모델: {settings.openai_model}")
            st.caption(f"Fallback: {settings.openai_fallback_model}")
            api_key_status = "✓" if settings.openai_api_key else "✗"
            st.caption(f"API 키: {api_key_status}")

        st.caption(f"캐시: {'ON' if settings.ai_cache_enabled else 'OFF'} ({settings.ai_cache_ttl_minutes}분)")

        st.markdown("---")

        # 시스템 정보
        st.subheader("시스템 정보")
        st.caption(f"거래 모드: {settings.trading_mode}")
        st.caption(f"로그 레벨: {settings.log_level}")

        # 거래소 연결 상태
        try:
            from infrastructure.exchanges.upbit_client import UpbitClient
            upbit = UpbitClient()
            if upbit.check_connection():
                st.success("Upbit 연결")
            else:
                st.error("Upbit 연결 실패")
        except:
            st.warning("Upbit 연결 확인 불가")

    # 메인 컨텐츠
    if not st.session_state.selected_wallet:
        st.info("사이드바에서 지갑을 선택하거나 생성하세요.")

        # 빠른 시작 가이드
        st.subheader("빠른 시작 가이드")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            ### 1. 지갑 생성
            - 가상지갑 또는 실거래 지갑 생성
            - 초기 자본금 설정
            - 거래소 API 연동 (실거래용)
            """)

        with col2:
            st.markdown("""
            ### 2. 전략 설정
            - RSI, MA Cross, Bollinger 등
            - 파라미터 조정
            - 백테스팅으로 검증
            """)

        with col3:
            st.markdown("""
            ### 3. 자동매매 시작
            - 전략 활성화
            - 실시간 시그널 모니터링
            - 거래 내역 확인
            """)

        st.markdown("---")

        # 시스템 기능 소개
        st.subheader("주요 기능")

        features = [
            ("대시보드", "지갑 현황, 수익률, 최근 거래 한눈에 보기"),
            ("전략 설정", "다양한 트레이딩 전략 생성 및 관리"),
            ("가상지갑", "안전한 모의투자로 전략 테스트"),
            ("백테스팅", "과거 데이터로 전략 성과 검증"),
            ("실시간 분석", "시장 데이터 및 시그널 모니터링")
        ]

        for feature, description in features:
            st.markdown(f"**{feature}**: {description}")

    else:
        # 선택된 지갑 정보 표시
        try:
            wallet = wallet_service.get_wallet(st.session_state.selected_wallet)

            # 지갑 카드 표시
            wallet_type_text = "가상" if wallet.wallet_type.value == "virtual" else "실거래"
            render_wallet_card(
                title=wallet.name,
                balance=wallet.balance_krw,
                total_value=wallet.total_value_krw,
                wallet_type=wallet_type_text
            )

            st.markdown("---")

            # 탭: 주문/전략/거래내역
            tab1, tab2, tab3 = st.tabs(["주문하기", "활성 전략", "거래 내역"])

            with tab1:
                st.subheader("주문 생성")

                col1, col2 = st.columns(2)

                with col1:
                    from core.enums import OrderSide, OrderType

                    order_side = st.selectbox(
                        "주문 유형",
                        options=[OrderSide.BUY.value, OrderSide.SELL.value],
                        format_func=lambda x: "매수" if x == "buy" else "매도"
                    )

                    symbol = st.text_input("심볼", value="KRW-BTC")
                    quantity = st.number_input("수량", min_value=0.0, value=0.001, step=0.001)

                with col2:
                    order_type = st.selectbox(
                        "주문 타입",
                        options=[OrderType.MARKET.value, OrderType.LIMIT.value],
                        format_func=lambda x: "시장가" if x == "market" else "지정가"
                    )

                    price = None
                    if order_type == OrderType.LIMIT.value:
                        price = st.number_input("가격", min_value=0.0, value=50000000.0, step=100000.0)

                if st.button("주문 실행", type="primary"):
                    try:
                        from core.models import OrderCreate

                        order_data = OrderCreate(
                            wallet_id=wallet.id,
                            symbol=symbol,
                            order_type=OrderType(order_type),
                            order_side=OrderSide(order_side),
                            quantity=Decimal(str(quantity)),
                            price=Decimal(str(price)) if price else None
                        )

                        # 주문 생성 및 실행
                        order = trading_service.create_order(order_data)
                        order = trading_service.execute_order(order.id)

                        st.success(f"주문 실행 완료: {order.symbol} {order.order_side.value.upper()} {order.quantity}")
                        st.rerun()

                    except Exception as e:
                        logger.error(f"주문 실행 실패: {e}")
                        st.error(f"주문 실행 실패: {e}")

            with tab2:
                st.subheader("활성 전략")

                try:
                    strategies = strategy_service.get_all_strategies()
                    active_strategies = [s for s in strategies if s.status.value == "active"]

                    if active_strategies:
                        for strategy in active_strategies:
                            with st.expander(f"{strategy.name}"):
                                st.write(f"**설명**: {strategy.description}")
                                st.write(f"**시간프레임**: {strategy.timeframe.value}")
                                st.write(f"**파라미터**: {strategy.parameters}")

                                if st.button(f"비활성화", key=f"deactivate_{strategy.id}"):
                                    strategy_service.deactivate_strategy(strategy.id)
                                    st.success("전략 비활성화")
                                    st.rerun()
                    else:
                        st.info("활성화된 전략이 없습니다. '전략 설정' 페이지에서 전략을 생성하세요.")

                except Exception as e:
                    logger.error(f"전략 조회 실패: {e}")
                    st.error(f"전략 조회 실패: {e}")

            with tab3:
                st.subheader("최근 거래 내역")

                try:
                    trades = trading_service.get_wallet_trades(wallet.id, limit=10)

                    if trades:
                        import pandas as pd

                        df = pd.DataFrame([
                            {
                                "시간": t.created_at.strftime("%Y-%m-%d %H:%M"),
                                "심볼": t.symbol,
                                "구분": "매수" if t.side.value == "buy" else "매도",
                                "수량": float(t.quantity),
                                "가격": f"₩{float(t.price):,.0f}",
                                "금액": f"₩{float(t.total_amount):,.0f}",
                                "수수료": f"₩{float(t.fee):,.0f}"
                            }
                            for t in trades
                        ])

                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("거래 내역이 없습니다.")

                except Exception as e:
                    logger.error(f"거래 내역 조회 실패: {e}")
                    st.error(f"거래 내역 조회 실패: {e}")

        except Exception as e:
            logger.error(f"지갑 정보 조회 실패: {e}")
            st.error(f"지갑 정보 조회 실패: {e}")

    # 푸터
    st.markdown("---")
    st.caption("BTS - Bitcoin Auto Trading System v1.0 | Clean Architecture Design")

if __name__ == "__main__":
    main()
