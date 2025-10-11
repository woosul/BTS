"""
홈 페이지 컨텐츠
"""
import streamlit as st
from decimal import Decimal
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from application.services.wallet_service import WalletService
from application.services.trading_service import TradingService
from application.services.strategy_service import StrategyService
from infrastructure.exchanges.upbit_client import UpbitClient
from config.settings import settings
from utils.logger import get_logger
from presentation.components.cards import render_wallet_card

logger = get_logger(__name__)

def get_services():
    """서비스 인스턴스 가져오기 (캐싱)"""
    if not st.session_state.get('services_initialized', False):
        try:
            from infrastructure.database.connection import SessionLocal
            db = SessionLocal()
            st.session_state.db = db

            exchange = UpbitClient(
                settings.upbit_access_key,
                settings.upbit_secret_key
            )

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

# 전역 스타일 적용
from presentation.styles.global_styles import apply_global_styles
apply_global_styles()

# 헤더
st.title("BTS | Bitcoin Trading System")
st.caption("KRW/BTC 시장에서의 종목선정에서부터 매수/매도 시스템 자동매매 시스템을 위한 트레이딩 전략 평가 플랫폼  |  UPBIT  |  BITTHUMB")
st.markdown("---")

# 서비스 초기화
wallet_service, trading_service, strategy_service = get_services()

if not wallet_service:
    st.error("서비스를 초기화할 수 없습니다. 설정을 확인하세요.")
    st.stop()

# 세션 상태 초기화
if 'selected_wallet' not in st.session_state:
    st.session_state.selected_wallet = None

# 메인 컨텐츠
if not st.session_state.selected_wallet:
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
                        price=Decimal(str(price)) if price else None,
                        strategy_id=None
                    )

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

                            if st.button("비활성화", key=f"deactivate_{strategy.id}"):
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
st.caption("BTS - Bitcoin Trading System v1.0  |  Clean Architecture Designed  |  Copyright 2025 Peaknine")
