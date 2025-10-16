"""
BTS 거래분석 페이지

매수/매도 신호 분석 및 모니터링
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import json

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from application.services.entry_service import EntryService
from application.services.exit_service import ExitService
from application.services.screening_service import ScreeningService
from infrastructure.exchanges.upbit_client import UpbitClient
from infrastructure.repositories.pinned_symbol_repository import PinnedSymbolRepository
from utils.logger import get_logger
from core.enums import StrategySignal

logger = get_logger(__name__)

# st.navigation을 사용할 때는 각 페이지에서 st.set_page_config와 st.logo를 호출하면 안 됨
# 메인 streamlit_app.py에서만 설정해야 함
# st.set_page_config(
#     page_title="거래분석 - BTS",
#     page_icon="",
#     layout="wide"
# )

# # 사이드바 로고 설정
# logo_path = str(project_root / "resource" / "image" / "peaknine_logo_01.svg")
# st.logo(
#     image=logo_path,
#     icon_image=logo_path
# )

def get_services():
    """서비스 인스턴스 가져오기"""
    from infrastructure.database.connection import SessionLocal

    db = SessionLocal()
    exchange = UpbitClient()
    entry_service = EntryService(db, exchange)
    exit_service = ExitService(db, exchange)
    screening_service = ScreeningService(db, exchange)
    pinned_repo = PinnedSymbolRepository(db)

    return entry_service, exit_service, screening_service, pinned_repo, db

def format_confidence(confidence):
    """신뢰도 포맷팅"""
    if confidence >= 0.8:
        return f"높음 {confidence:.1%}"
    elif confidence >= 0.6:
        return f"중간 {confidence:.1%}"
    else:
        return f"낮음 {confidence:.1%}"

def format_signal(signal):
    """신호 포맷팅"""
    signal_icons = {
        StrategySignal.BUY: "매수",
        StrategySignal.SELL: "매도",
        StrategySignal.HOLD: "보유"
    }
    return signal_icons.get(signal, "없음")

def create_signal_chart(signals_data):
    """신호 시계열 차트 생성"""
    if not signals_data:
        return None

    # 시간대별 신호 집계
    df = pd.DataFrame(signals_data)
    df['time'] = pd.to_datetime(df['timestamp'])
    df_hourly = df.groupby([df['time'].dt.floor('H'), 'signal']).size().reset_index(name='count')

    fig = px.bar(
        df_hourly,
        x='time',
        y='count',
        color='signal',
        color_discrete_map={
            'BUY': '#2E86AB',
            'SELL': '#F24236',
            'HOLD': '#A23B72'
        },
        title="시간대별 매수/매도 신호 분포"
    )

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#FAFAFA'),
        height=300
    )

    return fig

def analyze_single_symbol(symbol, entry_service, exit_service, strategy_configs):
    """단일 종목 매수/매도 분석"""
    results = {
        'symbol': symbol,
        'timestamp': datetime.now(),
        'entry_signals': {},
        'exit_signals': {},
        'current_price': 0,
        'recommendations': []
    }

    try:
        # 현재 가격 조회
        ticker = entry_service.exchange.get_ticker(symbol)
        results['current_price'] = ticker.get('trade_price', 0)

        # 매수 신호 생성
        for strategy_type, config in strategy_configs.get('entry', {}).items():
            if config.get('enabled', False):
                try:
                    signal_data = entry_service.generate_entry_signal(
                        strategy_id=config.get('strategy_id', 1),
                        strategy_type=strategy_type,
                        symbol=symbol
                    )
                    results['entry_signals'][strategy_type] = {
                        'signal': signal_data.signal.value,
                        'confidence': float(signal_data.confidence),
                        'indicators': dict(signal_data.indicators),
                        'metadata': dict(signal_data.metadata)
                    }
                except Exception as e:
                    logger.error(f"{symbol} {strategy_type} 매수 신호 생성 실패: {e}")
                    results['entry_signals'][strategy_type] = {
                        'signal': 'HOLD',
                        'confidence': 0.0,
                        'error': str(e)
                    }

        # 매도 신호 생성
        for strategy_type, config in strategy_configs.get('exit', {}).items():
            if config.get('enabled', False):
                try:
                    signal_data = exit_service.generate_exit_signal(
                        strategy_id=config.get('strategy_id', 1),
                        strategy_type=strategy_type,
                        symbol=symbol,
                        entry_price=results['current_price']  # 현재가를 매수가로 가정
                    )
                    results['exit_signals'][strategy_type] = {
                        'signal': signal_data.signal.value,
                        'confidence': float(signal_data.confidence),
                        'indicators': dict(signal_data.indicators),
                        'metadata': dict(signal_data.metadata)
                    }
                except Exception as e:
                    logger.error(f"{symbol} {strategy_type} 매도 신호 생성 실패: {e}")
                    results['exit_signals'][strategy_type] = {
                        'signal': 'HOLD',
                        'confidence': 0.0,
                        'error': str(e)
                    }

        # 종합 추천 생성
        buy_signals = [s for s in results['entry_signals'].values() if s['signal'] == 'BUY']
        sell_signals = [s for s in results['exit_signals'].values() if s['signal'] == 'SELL']

        if buy_signals:
            avg_confidence = sum(s['confidence'] for s in buy_signals) / len(buy_signals)
            results['recommendations'].append({
                'type': '매수',
                'confidence': avg_confidence,
                'count': len(buy_signals)
            })

        if sell_signals:
            avg_confidence = sum(s['confidence'] for s in sell_signals) / len(sell_signals)
            results['recommendations'].append({
                'type': '매도',
                'confidence': avg_confidence,
                'count': len(sell_signals)
            })

    except Exception as e:
        logger.error(f"{symbol} 분석 실패: {e}")
        results['error'] = str(e)

    return results

@st.dialog("연속분석 설정")
def show_continuous_analysis_modal():
    """연속분석 설정 모달"""
    st.markdown("### 연속분석 모드 설정")

    analysis_type = st.radio(
        "분석 타입",
        options=["연속 (무한 반복)", "횟수 지정"],
        help="연속 분석 모드를 선택하세요"
    )

    if analysis_type == "횟수 지정":
        repeat_count = st.number_input(
            "반복 횟수",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            help="분석을 반복할 횟수를 지정하세요"
        )
    else:
        repeat_count = -1  # -1은 무한 반복을 의미

    interval = st.slider(
        "분석 간격 (초)",
        min_value=10,
        max_value=300,
        value=60,
        step=10,
        help="각 분석 사이의 대기 시간"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("시작", type="primary", use_container_width=True):
            st.session_state.continuous_config = {
                'enabled': True,
                'repeat_count': repeat_count,
                'interval': interval,
                'current_iteration': 0
            }
            st.rerun()
    with col2:
        if st.button("취소", use_container_width=True):
            st.rerun()

def main():
    # 서비스 초기화
    entry_service, exit_service, screening_service, pinned_repo, db = get_services()

    st.title("거래분석")
    st.markdown("---")

    # 사이드바 설정
    with st.sidebar:
        st.markdown("<h3>분석 설정</h3>", unsafe_allow_html=True)

        # 매수 전략 설정
        st.markdown("<h4>매수 전략</h4>", unsafe_allow_html=True)

        entry_strategies = {}
        available_entry = entry_service.get_available_strategies()

        for strategy in available_entry[:3]:  # 상위 3개만 표시
            enabled = st.checkbox(
                strategy['name'],
                value=False,
                key=f"entry_{strategy['type']}"
            )
            entry_strategies[strategy['type']] = {
                'enabled': enabled,
                'strategy_id': 1,
                'name': strategy['name']
            }

        st.markdown("<h4>매도 전략</h4>", unsafe_allow_html=True)

        exit_strategies = {}
        available_exit = exit_service.get_available_strategies()

        for strategy in available_exit[:3]:  # 상위 3개만 표시
            enabled = st.checkbox(
                strategy['name'],
                value=False,
                key=f"exit_{strategy['type']}"
            )
            exit_strategies[strategy['type']] = {
                'enabled': enabled,
                'strategy_id': 1,
                'name': strategy['name']
            }

        # 전략 설정 딕셔너리
        strategy_configs = {
            'entry': entry_strategies,
            'exit': exit_strategies
        }

        st.markdown("---")

        # 기타 설정
        st.markdown("<h4>기타 설정</h4>", unsafe_allow_html=True)

        show_indicators = st.checkbox("기술 지표 표시", value=True)

    # 연속분석 상태 확인
    continuous_config = st.session_state.get('continuous_config', {'enabled': False})
    is_continuous_running = continuous_config.get('enabled', False)

    # 상단 버튼 영역
    col_title, col_spacer, col_btn1, col_btn2, col_btn3 = st.columns([0.4, 0.15, 0.15, 0.15, 0.15])

    with col_title:
        st.markdown("<h3 style='margin: 0; padding-top: 0.3rem;'>분석 제어</h3>", unsafe_allow_html=True)

    with col_btn1:
        single_symbol_btn = st.button("단일종목분석", use_container_width=True, type="secondary")

    with col_btn2:
        batch_analysis_btn = st.button("단일분석", use_container_width=True, type="secondary")

    with col_btn3:
        if is_continuous_running:
            stop_continuous_btn = st.button("연속분석정지", use_container_width=True, type="primary")
            if stop_continuous_btn:
                st.session_state.continuous_config = {'enabled': False}
                st.success("연속 분석이 정지되었습니다.")
                st.rerun()
        else:
            continuous_analysis_btn = st.button("연속분석", use_container_width=True, type="secondary")
            if continuous_analysis_btn:
                show_continuous_analysis_modal()

    # Screening 페이지에서 선정된 종목 가져오기
    screening_results = st.session_state.get('screening_results', [])
    market = st.session_state.get('screening_market', 'KRW')

    pinned_symbols_db = pinned_repo.get_all_active(market=market)
    pinned_symbols = [p.symbol for p in pinned_symbols_db]

    # 분석 대상 종목 목록 구성 (지정종목 + 스크리닝 결과)
    analysis_symbols = []
    if pinned_symbols:
        analysis_symbols.extend(pinned_symbols)
    if screening_results:
        analysis_symbols.extend([r.symbol for r in screening_results])

    # 중복 제거
    analysis_symbols = list(dict.fromkeys(analysis_symbols))

    # 종목 목록 표시
    st.markdown("---")
    st.markdown(f"<h3>분석 대상 종목 | {len(analysis_symbols)}개 (지정: {len(pinned_symbols)} + 스크리닝: {len([r.symbol for r in screening_results])})</h3>", unsafe_allow_html=True)

    if analysis_symbols:
        # 종목 목록을 DataFrame으로 표시
        symbols_df = pd.DataFrame({
            '종목': analysis_symbols,
            '구분': ['지정' if s in pinned_symbols else '스크리닝' for s in analysis_symbols]
        })

        # 상세보기 선택을 위한 selectbox
        selected_detail_symbol = st.selectbox(
            "상세 분석할 종목 선택",
            options=[""] + analysis_symbols,
            help="단일종목분석을 위해 종목을 선택하세요"
        )

        st.dataframe(symbols_df, use_container_width=True, hide_index=True)
    else:
        st.info("분석 대상 종목이 없습니다. Screening 페이지에서 종목을 선정하거나 지정 종목을 추가하세요.")

    st.markdown("---")

    # 단일종목분석 모드
    if single_symbol_btn:
        if selected_detail_symbol:
            with st.spinner(f"{selected_detail_symbol} 분석 중..."):
                result = analyze_single_symbol(
                    selected_detail_symbol,
                    entry_service,
                    exit_service,
                    strategy_configs
                )
                st.session_state.single_analysis_result = result
                st.session_state.analysis_mode = 'single'
        else:
            st.warning("상세 분석할 종목을 선택해주세요.")

    # 단일분석 모드 (1회 배치 분석)
    if batch_analysis_btn and analysis_symbols:
        with st.spinner("단일분석 실행 중..."):
            progress_bar = st.progress(0)
            results_container = st.empty()

            batch_results = []

            for i, symbol in enumerate(analysis_symbols):
                progress_bar.progress((i + 1) / len(analysis_symbols))

                result = analyze_single_symbol(
                    symbol,
                    entry_service,
                    exit_service,
                    strategy_configs
                )
                batch_results.append(result)

                # 중간 결과 표시
                summary_data = []
                for r in batch_results:
                    buy_count = sum(1 for s in r.get('entry_signals', {}).values()
                                  if s.get('signal') == 'BUY' and not s.get('error'))
                    sell_count = sum(1 for s in r.get('exit_signals', {}).values()
                                   if s.get('signal') == 'SELL' and not s.get('error'))

                    summary_data.append({
                        '종목': r['symbol'],
                        '현재가': f"{r.get('current_price', 0):,}",
                        '매수신호': buy_count,
                        '매도신호': sell_count,
                        '시각': r['timestamp'].strftime('%H:%M:%S')
                    })

                results_container.dataframe(
                    pd.DataFrame(summary_data),
                    use_container_width=True,
                    hide_index=True
                )

            progress_bar.progress(1.0)
            st.session_state.batch_results = batch_results
            st.session_state.analysis_mode = 'batch'
            st.success(f"단일분석 완료! {len(batch_results)} 개 종목")

    # 연속분석 모드
    if is_continuous_running and analysis_symbols:
        repeat_count = continuous_config.get('repeat_count', -1)
        interval = continuous_config.get('interval', 60)
        current_iteration = continuous_config.get('current_iteration', 0)

        # 반복 횟수 체크
        should_continue = (repeat_count == -1) or (current_iteration < repeat_count)

        if should_continue:
            st.info(f"연속분석 실행 중... ({current_iteration + 1}회차 / {'무한' if repeat_count == -1 else repeat_count}회)")

            progress_bar = st.progress(0)
            results_container = st.empty()

            batch_results = []

            for i, symbol in enumerate(analysis_symbols):
                progress_bar.progress((i + 1) / len(analysis_symbols))

                result = analyze_single_symbol(
                    symbol,
                    entry_service,
                    exit_service,
                    strategy_configs
                )
                batch_results.append(result)

                # 중간 결과 표시
                summary_data = []
                for r in batch_results:
                    buy_count = sum(1 for s in r.get('entry_signals', {}).values()
                                  if s.get('signal') == 'BUY' and not s.get('error'))
                    sell_count = sum(1 for s in r.get('exit_signals', {}).values()
                                   if s.get('signal') == 'SELL' and not s.get('error'))

                    summary_data.append({
                        '종목': r['symbol'],
                        '현재가': f"{r.get('current_price', 0):,}",
                        '매수신호': buy_count,
                        '매도신호': sell_count,
                        '시각': r['timestamp'].strftime('%H:%M:%S')
                    })

                results_container.dataframe(
                    pd.DataFrame(summary_data),
                    use_container_width=True,
                    hide_index=True
                )

            progress_bar.progress(1.0)
            st.session_state.batch_results = batch_results
            st.session_state.analysis_mode = 'continuous'

            # 다음 반복을 위한 카운터 증가 및 대기
            continuous_config['current_iteration'] = current_iteration + 1
            st.session_state.continuous_config = continuous_config

            # 대기 시간 표시
            st.info(f"다음 분석까지 {interval}초 대기 중... [연속분석정지] 버튼을 눌러 중단할 수 있습니다.")
            time.sleep(interval)
            st.rerun()
        else:
            # 지정된 횟수 완료
            st.success(f"연속분석 완료! 총 {repeat_count}회 실행")
            st.session_state.continuous_config = {'enabled': False}

    # 분석 결과 표시 영역
    st.markdown("---")
    st.markdown("<h3>분석 결과</h3>", unsafe_allow_html=True)

    analysis_mode = st.session_state.get('analysis_mode', None)

    # 단일종목분석 결과 표시
    if analysis_mode == 'single' and 'single_analysis_result' in st.session_state:
        result = st.session_state.single_analysis_result

        # 기본 정보
        col_price, col_time = st.columns(2)
        with col_price:
            price = result.get('current_price', 0)
            st.metric("현재가", f"{price:,}원")
        with col_time:
            timestamp = result.get('timestamp', datetime.now())
            st.metric("분석시각", timestamp.strftime('%H:%M:%S'))

        # 매수 신호
        st.markdown("<h4>매수 신호</h4>", unsafe_allow_html=True)
        entry_data = []
        for strategy, signal_info in result.get('entry_signals', {}).items():
            if not signal_info.get('error'):
                entry_data.append({
                    '전략': strategy_configs['entry'][strategy]['name'],
                    '신호': format_signal(StrategySignal(signal_info['signal'])),
                    '신뢰도': format_confidence(signal_info['confidence']),
                    '상태': "정상" if 'error' not in signal_info else f"오류"
                })

        if entry_data:
            st.dataframe(pd.DataFrame(entry_data), use_container_width=True, hide_index=True)
        else:
            st.info("활성화된 매수 전략이 없습니다.")

        # 매도 신호
        st.markdown("<h4>매도 신호</h4>", unsafe_allow_html=True)
        exit_data = []
        for strategy, signal_info in result.get('exit_signals', {}).items():
            if not signal_info.get('error'):
                exit_data.append({
                    '전략': strategy_configs['exit'][strategy]['name'],
                    '신호': format_signal(StrategySignal(signal_info['signal'])),
                    '신뢰도': format_confidence(signal_info['confidence']),
                    '상태': "정상" if 'error' not in signal_info else f"오류"
                })

        if exit_data:
            st.dataframe(pd.DataFrame(exit_data), use_container_width=True, hide_index=True)
        else:
            st.info("활성화된 매도 전략이 없습니다.")

        # 종합 추천
        if result.get('recommendations'):
            st.markdown("<h4>종합 추천</h4>", unsafe_allow_html=True)
            for rec in result['recommendations']:
                if rec['type'] == '매수':
                    st.success(f"{rec['type']} 추천 | 신뢰도: {rec['confidence']:.1%} | {rec['count']} 개 전략")
                elif rec['type'] == '매도':
                    st.error(f"{rec['type']} 추천 | 신뢰도: {rec['confidence']:.1%} | {rec['count']} 개 전략")

        # 기술 지표 상세
        if show_indicators and result.get('entry_signals'):
            with st.expander("기술 지표 상세", expanded=False):
                for strategy, signal_info in result.get('entry_signals', {}).items():
                    if signal_info.get('indicators') and not signal_info.get('error'):
                        st.write(f"**{strategy}**")
                        indicators_df = pd.DataFrame([signal_info['indicators']])
                        st.dataframe(indicators_df, use_container_width=True)

    # 배치 분석 결과 표시 (단일분석 & 연속분석)
    elif analysis_mode in ['batch', 'continuous'] and 'batch_results' in st.session_state:
        batch_results = st.session_state.batch_results

        # 요약 테이블
        summary_data = []
        for r in batch_results:
            buy_count = sum(1 for s in r.get('entry_signals', {}).values()
                          if s.get('signal') == 'BUY' and not s.get('error'))
            sell_count = sum(1 for s in r.get('exit_signals', {}).values()
                           if s.get('signal') == 'SELL' and not s.get('error'))

            summary_data.append({
                '종목': r['symbol'],
                '현재가': f"{r.get('current_price', 0):,}",
                '매수신호': buy_count,
                '매도신호': sell_count,
                '시각': r['timestamp'].strftime('%H:%M:%S')
            })

        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    else:
        st.info("분석을 실행하려면 위의 버튼을 클릭하세요.")

    # 신호 히스토리 영역
    st.markdown("---")
    st.markdown("<h3>신호 히스토리</h3>", unsafe_allow_html=True)

    if 'signal_history' not in st.session_state:
        st.session_state.signal_history = []

    if st.session_state.signal_history:
        history_df = pd.DataFrame(st.session_state.signal_history)
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("아직 기록된 신호 히스토리가 없습니다.")

if __name__ == "__main__":
    main()
