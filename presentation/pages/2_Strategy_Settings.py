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
    page_icon="🎯",
    layout="wide"
)

def get_services():
    """서비스 인스턴스 가져오기"""
    if 'db' not in st.session_state:
        db_gen = get_db_session()
        st.session_state.db = next(db_gen)

    if 'strategy_service' not in st.session_state:
        exchange = UpbitClient()
        st.session_state.strategy_service = StrategyService(st.session_state.db, exchange)

    return st.session_state.strategy_service

def main():
    st.title("🎯 전략 설정")
    st.markdown("---")

    # 서비스 초기화
    strategy_service = get_services()

    # 탭: 전략 목록 / 전략 생성 / 전략 테스트
    tab1, tab2, tab3 = st.tabs(["📋 전략 목록", "➕ 전략 생성", "🧪 전략 테스트"])

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
                        f"{'🟢' if strategy.status.value == 'active' else '⚫'} "
                        f"{strategy.name}",
                        expanded=False
                    ):
                        col1, col2 = st.columns([3, 1])

                        with col1:
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
                            # 활성화/비활성화 버튼
                            if strategy.status.value == "active":
                                if st.button(
                                    "비활성화",
                                    key=f"deactivate_{strategy.id}",
                                    type="secondary"
                                ):
                                    try:
                                        strategy_service.deactivate_strategy(strategy.id)
                                        st.success(f"'{strategy.name}' 비활성화")
                                        st.rerun()
                                    except Exception as e:
                                        logger.error(f"전략 비활성화 실패: {e}")
                                        st.error(f"비활성화 실패: {e}")
                            else:
                                if st.button(
                                    "활성화",
                                    key=f"activate_{strategy.id}",
                                    type="primary"
                                ):
                                    try:
                                        strategy_service.activate_strategy(strategy.id)
                                        st.success(f"'{strategy.name}' 활성화")
                                        st.rerun()
                                    except Exception as e:
                                        logger.error(f"전략 활성화 실패: {e}")
                                        st.error(f"활성화 실패: {e}")

                            # 삭제 버튼
                            if st.button(
                                "🗑️ 삭제",
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
                                "✏️ 수정",
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

    # ===== 탭 2: 전략 생성 =====
    with tab2:
        strategy_data = render_strategy_creation_form()

        if strategy_data:
            try:
                strategy = strategy_service.create_strategy(strategy_data)
                st.success(f"전략 '{strategy.name}' 생성 완료 (ID: {strategy.id})")
                logger.info(f"전략 생성: {strategy.name}")
                st.rerun()

            except Exception as e:
                logger.error(f"전략 생성 실패: {e}")
                st.error(f"전략 생성 실패: {e}")

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
                        st.subheader("📡 생성된 시그널")

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            signal_colors = {
                                "buy": "🟢",
                                "sell": "🔴",
                                "hold": "🟡"
                            }

                            signal_text = {
                                "buy": "매수",
                                "sell": "매도",
                                "hold": "관망"
                            }

                            icon = signal_colors.get(signal.signal.value, "⚪")
                            text = signal_text.get(signal.signal.value, signal.signal.value)

                            st.metric("시그널", f"{icon} {text}")

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

                        # 메타데이터
                        if signal.metadata:
                            st.markdown("#### 📊 메타데이터")

                            metadata_cols = st.columns(len(signal.metadata))
                            for idx, (key, value) in enumerate(signal.metadata.items()):
                                with metadata_cols[idx]:
                                    if isinstance(value, float):
                                        st.metric(key, f"{value:.2f}")
                                    else:
                                        st.metric(key, value)

                        # 지표 차트
                        if signal.metadata:
                            st.markdown("#### 📈 지표 차트")

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
                                    signal.metadata,
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
