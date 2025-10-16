"""
BTS 전략 설정 페이지

전략 생성, 수정, 활성화/비활성화
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd

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

    # 탭: 전략 목록 / 전략 생성 / 매수 전략 / 매도 전략 / 전략 테스트
    tab1, tab2, tab_entry, tab_exit, tab3 = st.tabs(["전략 목록", "전략 생성", "매수 전략", "매도 전략", "전략 테스트"])

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
        # 사이드바: 매수 전략 설정
        with st.sidebar:
            st.markdown("<h3 style='margin-bottom: 0.8rem;'>매수 전략 설정</h3>", unsafe_allow_html=True)

            # 전략 선택
            entry_strategy_type = st.selectbox(
                "전략",
                options=["macd_entry", "stochastic_entry", "multi_indicator_entry", "hybrid_entry"],
                format_func=lambda x: {
                    "macd_entry": "MACD Entry",
                    "stochastic_entry": "Stochastic Entry",
                    "multi_indicator_entry": "Multi-Indicator Entry",
                    "hybrid_entry": "Hybrid Entry"
                }[x],
                help="**매수 전략 선택**\n\n매수 시점을 결정할 전략을 선택합니다.\n- MACD: 골든 크로스\n- Stochastic: 과매도 반등\n- Multi-Indicator: 복합 지표\n- Hybrid: 가중 평균",
                key="entry_strategy_select"
            )

            st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

            # 전략 설정 (카드 + 모달 방식)
            st.markdown("<h3 style='margin-bottom: 0.8rem;'>전략 설정</h3>", unsafe_allow_html=True)

            # Session state 초기화
            if f"entry_params_{entry_strategy_type}" not in st.session_state:
                st.session_state[f"entry_params_{entry_strategy_type}"] = None

            # 현재 설정된 파라미터
            entry_params = st.session_state.get(f"entry_params_{entry_strategy_type}")

            # 전략 이름 매핑
            entry_names = {
                "macd_entry": "MACD Entry",
                "stochastic_entry": "Stochastic Entry",
                "multi_indicator_entry": "Multi-Indicator Entry",
                "hybrid_entry": "Hybrid Entry"
            }

            from presentation.components.strategy_card import render_strategy_card
            from presentation.components.entry_modal import show_entry_config_modal

            # 전략 카드 렌더링
            button_clicked = render_strategy_card(
                strategy_name=entry_names.get(entry_strategy_type, entry_strategy_type),
                strategy_type=entry_strategy_type,
                strategy_params=entry_params,
                card_key=f"entry_{entry_strategy_type}"
            )

            # 설정 버튼 클릭 시 모달 열기
            if button_clicked:
                show_entry_config_modal(
                    strategy_name=entry_names.get(entry_strategy_type, entry_strategy_type),
                    strategy_type=entry_strategy_type,
                    current_params=entry_params
                )

        # 메인 영역
        st.subheader("매수 전략")

        # 전략 설명
        strategy_descriptions = {
            "macd_entry": "MACD 선이 시그널 선을 상향 돌파하거나 히스토그램이 양수로 전환될 때 매수",
            "stochastic_entry": "%K와 %D가 골든 크로스하거나 과매도 구간에서 반등할 때 매수",
            "multi_indicator_entry": "RSI, MACD, 볼린저 밴드, 거래량 등 여러 지표를 조합하여 매수 (AND/OR 모드)",
            "hybrid_entry": "여러 전략의 시그널을 가중 평균하여 종합적으로 판단"
        }

        st.info(strategy_descriptions.get(entry_strategy_type, ""))

        if entry_params:
            st.success("전략이 설정되었습니다. 백테스트를 실행하거나 저장할 수 있습니다.")

            # 전략 저장 버튼
            if st.button("전략 저장", type="primary"):
                try:
                    from application.services.entry_service import EntryService
                    entry_service = EntryService(st.session_state.db, UpbitClient())

                    strategy = entry_service.create_entry_strategy(
                        strategy_type=entry_strategy_type,
                        name=f"{entry_names[entry_strategy_type]}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}",
                        description=strategy_descriptions[entry_strategy_type],
                        timeframe="1h",
                        parameters=entry_params
                    )

                    st.success(f"매수 전략 저장 완료 (ID: {strategy.id})")
                    st.rerun()

                except Exception as e:
                    logger.error(f"전략 저장 실패: {e}")
                    st.error(f"전략 저장 실패: {e}")
        else:
            st.warning("왼쪽 사이드바에서 전략을 설정해주세요.")

    # ===== 탭 Exit: 매도 전략 =====
    with tab_exit:
        # 사이드바: 매도 전략 설정
        with st.sidebar:
            st.markdown("<h3 style='margin-bottom: 0.8rem;'>매도 전략 설정</h3>", unsafe_allow_html=True)

            # 전략 선택
            exit_strategy_type = st.selectbox(
                "전략",
                options=[
                    "macd_exit",
                    "stochastic_exit",
                    "time_based_exit",
                    "fixed_target_exit",
                    "trailing_stop_exit",
                    "hybrid_exit"
                ],
                format_func=lambda x: {
                    "macd_exit": "MACD Exit",
                    "stochastic_exit": "Stochastic Exit",
                    "time_based_exit": "Time-based Exit",
                    "fixed_target_exit": "Fixed Target Exit",
                    "trailing_stop_exit": "Trailing Stop Exit",
                    "hybrid_exit": "Hybrid Exit"
                }[x],
                help="**매도 전략 선택**\n\n매도 시점을 결정할 전략을 선택합니다.\n- MACD: 데드 크로스\n- Stochastic: 과매수\n- Time-based: 보유 기간\n- Fixed Target: 목표가/손절가\n- Trailing Stop: 트레일링 스탑\n- Hybrid: 가중 평균",
                key="exit_strategy_select"
            )

            st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

            # 전략 설정 (카드 + 모달 방식)
            st.markdown("<h3 style='margin-bottom: 0.8rem;'>전략 설정</h3>", unsafe_allow_html=True)

            # Session state 초기화
            if f"exit_params_{exit_strategy_type}" not in st.session_state:
                st.session_state[f"exit_params_{exit_strategy_type}"] = None

            # 현재 설정된 파라미터
            exit_params = st.session_state.get(f"exit_params_{exit_strategy_type}")

            # 전략 이름 매핑
            exit_names = {
                "macd_exit": "MACD Exit",
                "stochastic_exit": "Stochastic Exit",
                "time_based_exit": "Time-based Exit",
                "fixed_target_exit": "Fixed Target Exit",
                "trailing_stop_exit": "Trailing Stop Exit",
                "hybrid_exit": "Hybrid Exit"
            }

            from presentation.components.strategy_card import render_strategy_card
            from presentation.components.exit_modal import show_exit_config_modal

            # 전략 카드 렌더링
            button_clicked = render_strategy_card(
                strategy_name=exit_names.get(exit_strategy_type, exit_strategy_type),
                strategy_type=exit_strategy_type,
                strategy_params=exit_params,
                card_key=f"exit_{exit_strategy_type}"
            )

            # 설정 버튼 클릭 시 모달 열기
            if button_clicked:
                show_exit_config_modal(
                    strategy_name=exit_names.get(exit_strategy_type, exit_strategy_type),
                    strategy_type=exit_strategy_type,
                    current_params=exit_params
                )

        # 메인 영역
        st.subheader("매도 전략")

        # 전략 설명
        exit_strategy_descriptions = {
            "macd_exit": "MACD 선이 시그널 선을 하향 돌파하거나 0선 아래로 하락할 때 매도",
            "stochastic_exit": "%K가 과매수 구간(80 이상)에서 %D를 하향 돌파할 때 매도",
            "time_based_exit": "설정된 보유 기간 경과 시 자동 매도. 날짜/시간 제약 기능 지원",
            "fixed_target_exit": "목표 수익률 달성 또는 손절률 도달 시 매도",
            "trailing_stop_exit": "최고가 대비 일정 비율 하락 시 매도 (트레일링 스탑)",
            "hybrid_exit": "여러 매도 전략의 시그널을 가중 평균하여 종합적으로 판단"
        }

        st.info(exit_strategy_descriptions.get(exit_strategy_type, ""))

        if exit_params:
            st.success("전략이 설정되었습니다. 백테스트를 실행하거나 저장할 수 있습니다.")

            # 전략 저장 버튼
            if st.button("전략 저장", type="primary", key="exit_save_btn"):
                try:
                    from application.services.exit_service import ExitService
                    exit_service = ExitService(st.session_state.db, UpbitClient())

                    strategy = exit_service.create_exit_strategy(
                        strategy_type=exit_strategy_type,
                        name=f"{exit_names[exit_strategy_type]}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}",
                        description=exit_strategy_descriptions[exit_strategy_type],
                        timeframe="1h",
                        parameters=exit_params
                    )

                    st.success(f"매도 전략 저장 완료 (ID: {strategy.id})")
                    st.rerun()

                except Exception as e:
                    logger.error(f"전략 저장 실패: {e}")
                    st.error(f"전략 저장 실패: {e}")
        else:
            st.warning("왼쪽 사이드바에서 전략을 설정해주세요.")

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
