"""
BTS 전략 설정 페이지

전략 생성, 수정, 활성화/비활성화
"""
import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.database.connection import get_db_session
from application.services.strategy_service import StrategyService
from infrastructure.exchanges.upbit_client import UpbitClient
from presentation.components.forms import (
    render_strategy_creation_form,
    render_strategy_update_form
)
from presentation.components.charts import render_indicator_chart
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="전략 설정 - BTS",
    page_icon="",
    layout="wide"
)

# 사이드바 로고 설정
# 사이드바 로고 설정
logo_path = str(project_root / "resource" / "image" / "peaknine_logo_01.svg")
icon_path = str(project_root / "resource" / "image" / "peaknine_02.png")
st.logo(
    image=logo_path,
    icon_image=logo_path
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

    [data-testid="stSidebarNav"] {
        padding-top: 0 !important;
    }
    [data-testid="stSidebarNav"] > div:first-child {
        padding: 1.5rem 1rem !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }
    [data-testid="stSidebarNav"] a {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }
    [data-testid="stSidebarNav"] img {
        width: 90% !important;
        max-width: 280px !important;
        height: auto !important;
    }
    [data-testid="stSidebarNav"] ul {
        margin-top: 1rem !important;
    }
    [data-testid="stSidebarNav"] ul li a {
        text-align: left !important;
        justify-content: flex-start !important;
    }
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
</style>
""", unsafe_allow_html=True)

def get_services():
    """서비스 인스턴스 가져오기"""
    if 'db' not in st.session_state:
        from infrastructure.database.connection import SessionLocal
        st.session_state.db = SessionLocal()

    if 'strategy_service' not in st.session_state:
        exchange = UpbitClient()
        st.session_state.strategy_service = StrategyService(st.session_state.db, exchange)

    return st.session_state.strategy_service

def main():
    st.title("전략 설정")
    st.markdown("---")

    # 서비스 초기화
    strategy_service = get_services()

    # 탭: 전략 목록 / 전략 생성 / 매수 전략 / 전략 테스트
    tab1, tab2, tab_entry, tab3 = st.tabs(["전략 목록", "전략 생성", "매수 전략", "전략 테스트"])

    # ===== 탭 1: 전략 목록 =====
    with tab1:
        st.subheader("등록된 전략")

        try:
            strategies = strategy_service.get_all_strategies()

            if not strategies:
                st.info("등록된 전략이 없습니다. '전략 생성' 탭에서 새 전략을 만드세요.")
            else:
                for strategy in strategies:
                    with st.expander(
                        f"{strategy.name}",
                        expanded=False
                    ):
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            # Toggle switch for active/inactive status
                            is_active = st.toggle(
                                "활성화",
                                value=strategy.status.value == "active",
                                key=f"toggle_{strategy.id}"
                            )

                            # Handle toggle state change
                            if is_active and strategy.status.value != "active":
                                try:
                                    strategy_service.activate_strategy(strategy.id)
                                    st.success(f"'{strategy.name}' 활성화")
                                    st.rerun()
                                except Exception as e:
                                    logger.error(f"전략 활성화 실패: {e}")
                                    st.error(f"활성화 실패: {e}")
                            elif not is_active and strategy.status.value == "active":
                                try:
                                    strategy_service.deactivate_strategy(strategy.id)
                                    st.success(f"'{strategy.name}' 비활성화")
                                    st.rerun()
                                except Exception as e:
                                    logger.error(f"전략 비활성화 실패: {e}")
                                    st.error(f"비활성화 실패: {e}")

                            st.markdown("---")

                            st.write(f"**ID**: {strategy.id}")
                            st.write(f"**설명**: {strategy.description}")
                            st.write(f"**시간프레임**: {strategy.timeframe.value}")
                            st.write(f"**상태**: {strategy.status.value}")

                            st.markdown("**파라미터**:")
                            for key, value in strategy.parameters.items():
                                st.write(f"  - {key}: {value}")

                            st.caption(f"생성: {strategy.created_at.strftime('%Y-%m-%d %H:%M')}")
                            st.caption(f"수정: {strategy.updated_at.strftime('%Y-%m-%d %H:%M')}")

                        with col2:
                            # 삭제 버튼
                            if st.button(
                                "삭제",
                                key=f"delete_{strategy.id}",
                                type="secondary"
                            ):
                                try:
                                    strategy_service.delete_strategy(strategy.id)
                                    st.success(f"'{strategy.name}' 삭제")
                                    st.rerun()
                                except Exception as e:
                                    logger.error(f"전략 삭제 실패: {e}")
                                    st.error(f"삭제 실패: {e}")

                            # 수정 버튼
                            if st.button(
                                "수정",
                                key=f"edit_{strategy.id}",
                                type="secondary"
                            ):
                                st.session_state.editing_strategy_id = strategy.id

        except Exception as e:
            logger.error(f"전략 목록 조회 실패: {e}")
            st.error(f"전략 목록 조회 실패: {e}")

        # 전략 수정 폼 (선택 시)
        if 'editing_strategy_id' in st.session_state:
            strategy_id = st.session_state.editing_strategy_id
            try:
                strategy = strategy_service.get_strategy(strategy_id)

                st.markdown("---")
                update_data = render_strategy_update_form(
                    strategy_id,
                    strategy.parameters
                )

                if update_data:
                    try:
                        updated_strategy = strategy_service.update_strategy(
                            strategy_id,
                            update_data
                        )
                        st.success(f"'{updated_strategy.name}' 수정 완료")
                        del st.session_state.editing_strategy_id
                        st.rerun()

                    except Exception as e:
                        logger.error(f"전략 수정 실패: {e}")
                        st.error(f"전략 수정 실패: {e}")

            except Exception as e:
                logger.error(f"전략 조회 실패: {e}")
                st.error(f"전략 조회 실패: {e}")
                del st.session_state.editing_strategy_id

    # ===== 탭 2: 전략 생성 (기본 RSI) =====
    with tab2:
        strategy_data = render_strategy_creation_form(strategy_type="rsi")

        if strategy_data:
            try:
                strategy = strategy_service.create_strategy(strategy_data)
                st.success(f"전략 '{strategy.name}' 생성 완료 (ID: {strategy.id})")
                logger.info(f"전략 생성: {strategy.name}")
                st.rerun()

            except Exception as e:
                logger.error(f"전략 생성 실패: {e}")
                st.error(f"전략 생성 실패: {e}")

    # ===== 탭 Entry: 매수 전략 =====
    with tab_entry:
        st.subheader("매수 전략 생성")

        # 전략 타입 선택
        strategy_type = st.selectbox(
            "매수 전략 타입",
            options=["macd_entry", "stochastic_entry", "multi_indicator_entry", "hybrid_entry"],
            format_func=lambda x: {
                "macd_entry": "MACD Entry (골든 크로스)",
                "stochastic_entry": "Stochastic Entry (과매도 반등)",
                "multi_indicator_entry": "Multi-Indicator Entry (복합 지표)",
                "hybrid_entry": "Hybrid Entry (가중 평균)"
            }.get(x, x)
        )

        # 전략 설명 표시
        strategy_descriptions = {
            "macd_entry": "MACD 선이 시그널 선을 상향 돌파하거나 히스토그램이 양수로 전환될 때 매수",
            "stochastic_entry": "%K와 %D가 골든 크로스하거나 과매도 구간에서 반등할 때 매수",
            "multi_indicator_entry": "RSI, MACD, 볼린저 밴드, 거래량 등 여러 지표를 조합하여 매수 (AND/OR 모드)",
            "hybrid_entry": "여러 전략의 시그널을 가중 평균하여 종합적으로 판단"
        }
        st.info(strategy_descriptions.get(strategy_type, ""))

        st.markdown("---")

        # 전략 생성 폼
        strategy_data = render_strategy_creation_form(strategy_type=strategy_type)

        if strategy_data:
            try:
                # Entry Service 사용
                from application.services.entry_service import EntryService
                entry_service = EntryService(st.session_state.db, UpbitClient())

                strategy = entry_service.create_entry_strategy(
                    strategy_type=strategy_type,
                    name=strategy_data.name,
                    description=strategy_data.description,
                    timeframe=strategy_data.timeframe,
                    parameters=strategy_data.parameters
                )

                st.success(f"매수 전략 '{strategy.name}' 생성 완료 (ID: {strategy.id})")
                logger.info(f"매수 전략 생성: {strategy.name}")
                st.rerun()

            except Exception as e:
                logger.error(f"매수 전략 생성 실패: {e}")
                st.error(f"매수 전략 생성 실패: {e}")

    # ===== 탭 3: 전략 테스트 =====
    with tab3:
        st.subheader("전략 시그널 테스트")

        try:
            strategies = strategy_service.get_all_strategies()

            if not strategies:
                st.info("등록된 전략이 없습니다.")
            else:
                col1, col2 = st.columns(2)

                with col1:
                    strategy_id = st.selectbox(
                        "전략 선택",
                        options=[s.id for s in strategies],
                        format_func=lambda x: next(
                            (f"{s.name} (ID: {s.id})" for s in strategies if s.id == x),
                            str(x)
                        )
                    )

                with col2:
                    symbol = st.text_input(
                        "거래 심볼",
                        value="KRW-BTC",
                        help="테스트할 거래 쌍"
                    )

                if st.button("시그널 생성", type="primary"):
                    try:
                        # 시그널 생성
                        signal = strategy_service.generate_signal(strategy_id, symbol)

                        # 결과 표시
                        st.markdown("---")
                        st.subheader("생성된 시그널")

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            signal_text = {
                                "buy": "매수",
                                "sell": "매도",
                                "hold": "관망"
                            }

                            text = signal_text.get(signal.signal.value, signal.signal.value)

                            st.metric("시그널", text)

                        with col2:
                            st.metric(
                                "확신도",
                                f"{signal.confidence * 100:.1f}%"
                            )

                        with col3:
                            st.metric(
                                "생성 시간",
                                signal.timestamp.strftime("%H:%M:%S")
                            )

                        # 지표 데이터
                        if signal.indicators:
                            st.markdown("#### 지표 데이터")

                            metadata_cols = st.columns(len(signal.indicators))
                            for idx, (key, value) in enumerate(signal.indicators.items()):
                                with metadata_cols[idx]:
                                    if isinstance(value, float):
                                        st.metric(key, f"{value:.2f}")
                                    else:
                                        st.metric(key, value)

                        # 지표 차트
                        if signal.indicators:
                            st.markdown("#### 지표 차트")

                            # OHLCV 데이터 조회
                            exchange = UpbitClient()
                            strategy = strategy_service.get_strategy(strategy_id)

                            interval_map = {
                                "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
                                "1h": "60", "4h": "240", "1d": "day", "1w": "week"
                            }
                            interval = interval_map.get(strategy.timeframe.value, "60")

                            ohlcv_data = exchange.get_ohlcv(symbol, interval, 100)

                            if ohlcv_data:
                                fig = render_indicator_chart(
                                    ohlcv_data,
                                    signal.indicators,
                                    title=f"{symbol} 지표",
                                    height=500
                                )
                                st.plotly_chart(fig, use_container_width=True)

                    except Exception as e:
                        logger.error(f"시그널 생성 실패: {e}")
                        st.error(f"시그널 생성 실패: {e}")

        except Exception as e:
            logger.error(f"전략 테스트 오류: {e}")
            st.error(f"전략 테스트 오류: {e}")

if __name__ == "__main__":
    main()
