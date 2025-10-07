"""
BTS 종목선정 페이지

KRW/BTC 시장에서 투자 가치가 높은 종목을 선정
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from application.services.screening_service import ScreeningService
from infrastructure.exchanges.upbit_client import UpbitClient
from infrastructure.repositories.pinned_symbol_repository import PinnedSymbolRepository
from utils.logger import get_logger
from presentation.components.strategy_card import render_strategy_card
from presentation.components.strategy_modal import show_strategy_config_modal

logger = get_logger(__name__)

st.set_page_config(
    page_title="종목선정 - BTS",
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
</style>
""", unsafe_allow_html=True)

def get_services():
    """서비스 인스턴스 가져오기 - 매번 새 세션 생성"""
    from infrastructure.database.connection import SessionLocal

    # 매번 새 세션 생성
    db = SessionLocal()

    exchange = UpbitClient()
    screening_service = ScreeningService(db, exchange)
    pinned_repo = PinnedSymbolRepository(db)

    return screening_service, pinned_repo, db

def main():
    # 전체 페이지 스타일 조정
    st.markdown("""
    <style>
    /* 타이틀 크기 조정 */
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
    /* 구분선 여백 조정 */
    hr {
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
    }
    /* 블록 요소 여백 조정 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }

    /* 셀렉트박스 폰트 크기 및 스타일 */
    [data-baseweb="select"] > div {
        font-size: 0.875em !important;
    }
    [data-baseweb="select"] input {
        font-size: 0.875em !important;
    }
    [data-baseweb="select"] div[role="button"] {
        border-radius: 4px !important;
    }

    /* 멀티셀렉트 태그 폰트 크기 및 스타일 */
    [data-baseweb="tag"] {
        font-size: 0.875rem !important;
        font-family: "Noto Sans KR", sans-serif !important;
    }
    [data-baseweb="tag"] span {
        font-size: 0.875rem !important;
        font-family: "Noto Sans KR", sans-serif !important;
    }

    /* 사이드바 메뉴 스타일 */
    [data-testid="stSidebarNav"] ul li a {
        background-color: var(--primary-color) !important;
        border-radius: 4px !important;
        margin-bottom: 4px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 서비스 초기화
    screening_service, pinned_repo, db = get_services()

    # 사이드바: 스크리닝 설정
    with st.sidebar:
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>스크리닝 설정</h3>", unsafe_allow_html=True)

        # 시장 및 전략 선택 (한 줄에 배치)
        col1, col2 = st.columns(2)

        with col1:
            market = st.selectbox(
                "시장",
                options=["KRW", "BTC"],
                help="**대상 시장**\n\n거래할 시장을 선택합니다.\n- KRW: 원화 시장\n- BTC: 비트코인 시장"
            )

        with col2:
            strategy_type = st.selectbox(
                "전략",
                options=["momentum", "volume", "technical", "hybrid"],
                format_func=lambda x: {
                    "momentum": "모멘텀 기반",
                    "volume": "거래량 기반",
                    "technical": "기술지표 복합",
                    "hybrid": "하이브리드"
                }[x],
                help="**스크리닝 전략**\n\n종목을 선정할 전략을 선택합니다.\n- 모멘텀: 가격/거래량 상승세\n- 거래량: 거래 활발도\n- 기술지표: RSI/MACD/MA 복합\n- 하이브리드: 여러 전략 조합"
            )

        # 시장의 전체 종목 수 미리 조회 (대략적인 수)
        try:
            from infrastructure.exchanges.upbit_client import UpbitClient
            temp_exchange = UpbitClient()
            market_symbols = temp_exchange.get_market_symbols(market)
            total_symbols = len(market_symbols)
            # 5의 배수로 올림
            max_symbols = ((total_symbols + 4) // 5) * 5
        except:
            total_symbols = 200
            max_symbols = 200

        # 상위 종목 수
        st.markdown("""
        <style>
        /* All 토글 우측 정렬 - padding 기반 정렬 */
        .st-key-show_all_toggle {
            margin-left: auto !important;
            display: block !important;
            padding-top: 0.3rem !important;
        }
        div[data-testid="column"]:nth-child(3) div[data-testid="stVerticalBlock"] {
            display: flex !important;
            justify-content: flex-end !important;
        }
        </style>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
        with col1:
            st.markdown("<h3 style='margin: 0; padding-top: 0.3rem;'>선정 종목 수</h3>", unsafe_allow_html=True)
        with col2:
            st.write("")  # 빈 공간
        with col3:
            show_all = st.toggle(
                "All",
                value=False,
                help="**전체 종목 표시**\n\n활성화 시 스크리닝 결과를 전체 종목으로 표시합니다.\n- ON: 모든 종목 표시\n- OFF: 상위 N개만 표시",
                key="show_all_toggle"
            )

        if show_all:
            st.info(f"전체 종목을 표시합니다 (총 {total_symbols}개)")
            top_n = total_symbols
        else:
            top_n = st.slider(
                "상위 종목",
                min_value=5,
                max_value=max_symbols,
                value=10,
                step=5,
                help=f"**상위 종목 수 설정**\n\n스크리닝 결과에서 상위 N개 종목만 선정합니다.\n- 최소: 5개\n- 최대: {max_symbols}개\n- 단위: 5개",
                label_visibility="collapsed"
            )
            st.caption(f"상위 {top_n}개 종목 (전체 {total_symbols}개 중)")

        # st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

        # 스크리닝 실행 버튼
        run_screening = st.button(
            "스크리닝 실행",
            type="primary",
            use_container_width=True,
            help="설정된 전략으로 종목 스크리닝을 실행합니다"
        )

        st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

        st.markdown("<h3 style='margin-bottom: 0.8rem;'>전략설정</h3>", unsafe_allow_html=True)

        # Session state 초기화
        if f"strategy_params_{strategy_type}" not in st.session_state:
            st.session_state[f"strategy_params_{strategy_type}"] = None

        # 현재 설정된 파라미터
        strategy_params = st.session_state.get(f"strategy_params_{strategy_type}")

        # 전략 이름 매핑
        strategy_names = {
            "momentum": "모멘텀 기반",
            "volume": "거래량 기반",
            "technical": "기술지표 복합",
            "hybrid": "하이브리드"
        }

        strategy_name = strategy_names.get(strategy_type, strategy_type)

        # 하이브리드 전략의 경우 개별 전략별 카드 표시
        if strategy_type == "hybrid" and strategy_params:
            weights = strategy_params.get("strategy_weights", {})

            # 모멘텀 카드
            if weights.get("momentum", 0) > 0:
                momentum_params = {
                    "price_weight": strategy_params.get("momentum_price_weight", 0.4),
                    "volume_weight": strategy_params.get("momentum_volume_weight", 0.3),
                    "rsi_weight": strategy_params.get("momentum_rsi_weight", 0.3),
                    "period_1d": strategy_params.get("momentum_period_1d", True),
                    "period_7d": strategy_params.get("momentum_period_7d", True),
                    "period_30d": strategy_params.get("momentum_period_30d", True)
                }
                render_strategy_card(
                    strategy_name=f"모멘텀 기반 | {weights.get('momentum', 0):.0%}",
                    strategy_type="momentum",
                    strategy_params=momentum_params,
                    card_key="hybrid_momentum",
                    show_button=False,
                    is_hybrid_sub=True
                )

            # 거래량 카드
            if weights.get("volume", 0) > 0:
                volume_params = {
                    "amount_weight": strategy_params.get("volume_amount_weight", 0.5),
                    "surge_weight": strategy_params.get("volume_surge_weight", 0.5),
                    "threshold": strategy_params.get("volume_threshold", 1.5),
                    "period": strategy_params.get("volume_period", 20)
                }
                render_strategy_card(
                    strategy_name=f"거래량 기반 | {weights.get('volume', 0):.0%}",
                    strategy_type="volume",
                    strategy_params=volume_params,
                    card_key="hybrid_volume",
                    show_button=False,
                    is_hybrid_sub=True
                )

            # 기술지표 카드
            if weights.get("technical", 0) > 0:
                technical_params = {
                    "rsi_weight": strategy_params.get("technical_rsi_weight", 0.3),
                    "macd_weight": strategy_params.get("technical_macd_weight", 0.4),
                    "ma_weight": strategy_params.get("technical_ma_weight", 0.3),
                    "use_rsi": strategy_params.get("technical_rsi", True),
                    "use_macd": strategy_params.get("technical_macd", True),
                    "use_ma": strategy_params.get("technical_ma", True),
                    "rsi_period": strategy_params.get("technical_rsi_period", 14),
                    "macd_fast": strategy_params.get("technical_macd_fast", 12),
                    "macd_slow": strategy_params.get("technical_macd_slow", 26),
                    "macd_signal": strategy_params.get("technical_macd_signal", 9),
                    "ma_short": strategy_params.get("technical_ma_short", 20),
                    "ma_long": strategy_params.get("technical_ma_long", 60)
                }
                render_strategy_card(
                    strategy_name=f"기술지표 복합 | {weights.get('technical', 0):.0%}",
                    strategy_type="technical",
                    strategy_params=technical_params,
                    card_key="hybrid_technical",
                    show_button=False,
                    is_hybrid_sub=True
                )

            # 하이브리드 설정 버튼
            button_clicked = st.button(
                f"{strategy_name} 설정",
                key=f"config_btn_{strategy_type}",
                use_container_width=True,
                type="primary" if not strategy_params else "secondary"
            )
        else:
            # 일반 전략 카드 렌더링
            button_clicked = render_strategy_card(
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                strategy_params=strategy_params,
                card_key=strategy_type
            )

        # 설정 버튼 클릭 시 모달 열기
        if button_clicked:
            show_strategy_config_modal(
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                current_params=strategy_params
            )

        # 설정되지 않은 경우 기본 파라미터 사용
        if not strategy_params:
            if strategy_type == "momentum":
                strategy_params = {
                    "price_weight": 0.4,
                    "volume_weight": 0.3,
                    "rsi_weight": 0.3,
                    "period_1d": True,
                    "period_7d": True,
                    "period_30d": True
                }
            elif strategy_type == "volume":
                strategy_params = {
                    "amount_weight": 0.5,
                    "surge_weight": 0.5,
                    "threshold": 1.5,
                    "period": 20
                }
            elif strategy_type == "technical":
                strategy_params = {
                    "rsi_weight": 0.3,
                    "macd_weight": 0.4,
                    "ma_weight": 0.3,
                    "use_rsi": True,
                    "use_macd": True,
                    "use_ma": True,
                    "rsi_period": 14,
                    "macd_fast": 12,
                    "macd_slow": 26,
                    "macd_signal": 9,
                    "ma_short": 20,
                    "ma_long": 60
                }
            elif strategy_type == "hybrid":
                strategy_params = {
                    "strategy_weights": {
                        "momentum": 0.40,
                        "volume": 0.30,
                        "technical": 0.30
                    },
                    "min_score": 0.5,
                    "momentum_price_weight": 0.4,
                    "momentum_volume_weight": 0.3,
                    "momentum_rsi_weight": 0.3,
                    "momentum_period_1d": True,
                    "momentum_period_7d": True,
                    "momentum_period_30d": True,
                    "volume_amount_weight": 0.5,
                    "volume_surge_weight": 0.5,
                    "volume_threshold": 1.5,
                    "volume_period": 20,
                    "technical_rsi_weight": 0.3,
                    "technical_macd_weight": 0.4,
                    "technical_ma_weight": 0.3,
                    "technical_rsi": True,
                    "technical_macd": True,
                    "technical_ma": True,
                    "technical_rsi_period": 14,
                    "technical_macd_fast": 12,
                    "technical_macd_slow": 26,
                    "technical_macd_signal": 9,
                    "technical_ma_short": 20,
                    "technical_ma_long": 60
                }

    # 메인 영역 - 항상 결과 페이지 표시

    # 스크리닝 실행 시 결과 업데이트
    if run_screening:
        # 디폴트 값으로 실행한 경우, 사이드바 전략 설정도 업데이트 (rerun 없이)
        strategy_key = f"{strategy_type}_strategy_config"
        if strategy_key not in st.session_state:
            # 디폴트 값을 사이드바 설정으로도 저장
            st.session_state[strategy_key] = strategy_params

        with st.spinner("스크리닝 실행 중..."):
            try:
                # 스크리닝 실행
                results = screening_service.screen_symbols(
                    market=market,
                    strategy_type=strategy_type,
                    strategy_params=strategy_params,
                    top_n=top_n
                )

                # 결과 저장
                st.session_state.screening_results = results
                st.session_state.screening_market = market
                st.session_state.screening_strategy = strategy_type
                st.session_state.screening_params = strategy_params
                st.session_state.screening_time = datetime.now()
                # st.success(f"스크리닝 완료: {len(results)}개 종목 선정")

            except Exception as e:
                logger.error(f"스크리닝 실패: {e}")
                st.error(f"스크리닝 실패: {e}")
                import traceback
                st.text(traceback.format_exc())

    # 결과 준비: 스크리닝 결과가 있으면 사용, 없으면 빈 리스트
    results = st.session_state.get('screening_results', [])

    # 페이지 상단 타이틀과 메타 정보
    st.markdown("""
    <style>
    .page-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    .page-title {
        font-size: 2rem;
        font-weight: 600;
        margin: 0;
        margin-right: 1rem;
    }
    .meta-cards {
        display: flex;
        gap: 8px;
    }
    .meta-card-small {
        background-color: #1E1E1E;
        border-radius: 4px;
        padding: 8px 16px;
        border: 1px solid #3d3d4a;
        font-size: 0.875rem;
        white-space: nowrap;
    }
    .meta-label {
        color: #9ca3af;
        margin-right: 4px;
    }
    .meta-value {
        color: #FAFAFA;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    # 타이틀과 메타카드를 한 줄에
    if results and 'screening_market' in st.session_state:
        strategy_name = {
            "momentum": "모멘텀",
            "volume": "거래량",
            "technical": "기술지표",
            "hybrid": "하이브리드"
        }.get(st.session_state.screening_strategy, "Unknown")

        st.markdown(f"""
        <div class="page-header">
            <h1 class="page-title">종목선정</h1>
            <div class="meta-cards" style="margin-left: 80px;">
                <div class="meta-card-small">
                    <span class="meta-label">시장</span>
                    <span class="meta-value">{st.session_state.screening_market}</span>
                </div>
                <div class="meta-card-small">
                    <span class="meta-label">전략</span>
                    <span class="meta-value">{strategy_name}</span>
                </div>
                <div class="meta-card-small">
                    <span class="meta-label">실행</span>
                    <span class="meta-value">{st.session_state.screening_time.strftime('%H:%M:%S')}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<h1 class="page-title">종목선정</h1>', unsafe_allow_html=True)

    # if not results and len(st.session_state.get('pinned_symbols', set())) == 0:
    #    st.info("스크리닝을 실행하거나 지정 종목을 추가하여 매수 분석을 시작하세요.")

    # 결과 테이블 타이틀과 버튼을 한 줄에
    # DB 저장된 지정종목 수와 스크리닝 종목 수 계산
    saved_pinned = st.session_state.get('pinned_symbols', set())
    saved_count = len(saved_pinned)
    screening_count = len(results) - len([r for r in results if r.symbol in saved_pinned]) if results else 0
    title_text = f"선정 종목 | {saved_count}+{screening_count}" if saved_count > 0 or screening_count > 0 else "선정 종목"

    col_title, col_spacer, col_btn1, col_btn2, col_btn3 = st.columns([0.4, 0.15, 0.15, 0.15, 0.15])
    with col_title:
        st.markdown(f"<h3 style='margin: 0; padding-top: 0.3rem;'>{title_text}</h3>", unsafe_allow_html=True)
    with col_btn1:
        save_pinned_btn = st.button("지정종목저장", use_container_width=True, type="secondary")
    with col_btn2:
        single_analysis_btn = st.button("단일매수분석", use_container_width=True, type="secondary")
    with col_btn3:
        if 'continuous_analysis_running' not in st.session_state:
            st.session_state.continuous_analysis_running = False

        if st.session_state.continuous_analysis_running:
            stop_analysis_btn = st.button("매수분석정지", use_container_width=True, type="primary")
            if stop_analysis_btn:
                st.session_state.continuous_analysis_running = False
                st.success("연속 매수 분석이 정지되었습니다.")
                st.rerun()
        else:
            continuous_analysis_btn = st.button("연속매수분석", use_container_width=True, type="secondary")
            if continuous_analysis_btn:
                st.session_state.continuous_analysis_running = True
                st.success("연속 매수 분석이 시작되었습니다.")
                st.rerun()

    st.markdown("<div style='margin: 0.8rem 0;'></div>", unsafe_allow_html=True)

    # 지정 종목 DB에서 로드 (초기화 시에만)
    if 'pinned_symbols' not in st.session_state or st.session_state.get('pinned_symbols_loaded') != market:
        db_pinned = pinned_repo.get_all_active(market=market)
        st.session_state.pinned_symbols = set([p.symbol for p in db_pinned])
        st.session_state.pinned_symbols_loaded = market
        st.session_state.checkbox_pending_pinned = st.session_state.pinned_symbols.copy()

    # 현재 스크리닝 결과의 고유 키 생성
    screening_key = f"{market}_{strategy_type}_{st.session_state.get('screening_time', '')}"

    # DataFrame 생성 - 체크박스 선택 종목과 일반 종목 분리
    pinned_data = []
    unpinned_data = []

    # 스크리닝 결과를 dict로 변환 (빠른 조회를 위해)
    results_dict = {r.symbol: r for r in results}

    # 체크박스 임시 상태 초기화
    if 'checkbox_pending_pinned' not in st.session_state:
        st.session_state.checkbox_pending_pinned = st.session_state.pinned_symbols.copy()

    # 1. 먼저 체크박스 선택된 종목을 상단에 표시 (DB 저장 여부와 무관)
    # 점수 기준으로 정렬하기 위해 먼저 리스트 생성
    pinned_with_scores = []
    for symbol in st.session_state.checkbox_pending_pinned:
        if symbol in results_dict:
            result = results_dict[symbol]
            pinned_with_scores.append((symbol, result.score, result))
        else:
            # 스크리닝 결과에 없는 종목은 점수 0
            pinned_with_scores.append((symbol, 0.0, None))

    # 점수 기준 내림차순 정렬
    pinned_with_scores.sort(key=lambda x: x[1], reverse=True)

    # 정렬된 순서대로 데이터 생성
    for symbol, _, result in pinned_with_scores:
        if result:
            row = {
                "종목": result.symbol,
                "점수": result.score,
                # DB 저장된 종목만 "✓" 표시
                "순위": "✓" if symbol in st.session_state.pinned_symbols else ""
            }
            # 세부 점수 추가
            for key, value in result.details.items():
                if isinstance(value, (int, float)):
                    row[key] = value
                else:
                    row[key] = str(value)
        else:
            # 스크리닝 결과에 없는 종목
            row = {
                "종목": symbol,
                "점수": 0.0,
                "순위": "✓" if symbol in st.session_state.pinned_symbols else ""
            }
        pinned_data.append(row)

    # 2. 일반 종목 처리 (체크박스 선택되지 않은 종목만)
    unpinned_rank = 1

    # DB 저장된 종목 중 체크박스 해제된 종목도 포함
    all_symbols_to_show = set(results_dict.keys()) | st.session_state.pinned_symbols

    # 스크리닝 결과부터 처리
    for result in results:
        if result.symbol not in st.session_state.checkbox_pending_pinned:
            # DB 저장된 종목은 "✓", 아니면 순위 번호
            if result.symbol in st.session_state.pinned_symbols:
                rank_display = "✓"
            else:
                rank_display = unpinned_rank
                unpinned_rank += 1

            row = {
                "종목": result.symbol,
                "점수": result.score,
                "순위": rank_display
            }

            # 세부 점수 추가
            for key, value in result.details.items():
                if isinstance(value, (int, float)):
                    row[key] = value
                else:
                    row[key] = str(value)

            unpinned_data.append(row)

    # DB 저장된 종목 중 스크리닝 결과에 없고 체크박스도 해제된 종목 추가
    for symbol in st.session_state.pinned_symbols:
        if symbol not in st.session_state.checkbox_pending_pinned and symbol not in results_dict:
            row = {
                "종목": symbol,
                "점수": 0.0,
                # DB 저장된 종목은 체크박스 해제되어도 "✓" 유지
                "순위": "✓"
            }
            unpinned_data.append(row)

    # 지정 종목을 상단에, 일반 종목을 하단에 배치
    data = pinned_data + unpinned_data

    # 데이터가 있을 때만 DataFrame 처리
    if data:
        df = pd.DataFrame(data)

        # 숫자형 컬럼 식별
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns

        # 컬럼 순서를 재배열하기 위한 새로운 DataFrame 구성
        new_columns = ["순위", "종목"]
    else:
        # 빈 DataFrame 생성
        df = pd.DataFrame(columns=["순위", "종목"])
        numeric_columns = []
        new_columns = ["순위", "종목"]

    for col in numeric_columns:
        if col not in ["순위"]:  # 전체 순위 컬럼은 제외
            # 순위 계산 (내림차순 - 높은 값이 좋음)
            # NaN 값 처리: NaN은 순위 계산에서 제외하고, 나중에 빈 문자열로 대체
            rank_col = f"{col}_R"
            df[rank_col] = df[col].rank(ascending=False, method='min', na_option='keep')
            # NaN이 아닌 값만 int로 변환, NaN은 유지
            df[rank_col] = df[rank_col].apply(lambda x: int(x) if pd.notna(x) else None)

            # 값 컬럼과 순위 컬럼을 순서대로 추가
            new_columns.append(col)
            new_columns.append(rank_col)

    # 문자열 컬럼 추가 (순위가 없는 컬럼들)
    for col in df.columns:
        if col not in new_columns and col not in numeric_columns:
            new_columns.append(col)

    # 컬럼 순서 재배열
    df = df[new_columns]

    # 체크박스 임시 상태 관리 (DB 저장 전)
    if 'checkbox_pending_pinned' not in st.session_state:
        st.session_state.checkbox_pending_pinned = st.session_state.pinned_symbols.copy()

    # '지정' 컬럼 추가 (첫 번째 컬럼) - pending 상태 사용
    if data:
        is_pinned_list = [row["종목"] in st.session_state.checkbox_pending_pinned for row in data]
        df.insert(0, '지정', is_pinned_list)

    # 1-5위 순위를 강조하기 위해 텍스트로 변환
    display_df = df.copy()
    for col in df.columns:
        if col.endswith("_R"):
            # 1-5위는 "1 ●", "2 ●" 형식으로 표시, None은 빈 문자열
            display_df[col] = df[col].apply(
                lambda x: f"{int(x)} ●" if pd.notna(x) and x <= 5 else (str(int(x)) if pd.notna(x) else "")
            )

    # 컬럼 설정
    column_config = {}
    for col in display_df.columns:
        if col == "지정":
            column_config[col] = st.column_config.CheckboxColumn(
                col,
                width=50,
                help="체크: 지정 종목으로 저장, 해제: 지정 종목에서 제거"
            )
        elif col == "순위":
            column_config[col] = st.column_config.NumberColumn(
                col,
                width=60
            )
        elif col == "종목":
            column_config[col] = st.column_config.TextColumn(
                col,
                width=100
            )
        elif col.endswith("_R"):
            # 순위 컬럼 - "R"로 표시
            column_config[col] = st.column_config.TextColumn(
                "R",
                width=45
            )
        elif col in numeric_columns and col != "순위":
            column_config[col] = st.column_config.NumberColumn(
                col,
                width=90,
                format="%.2f"
            )

    # 데이터 표시 및 편집 - data_editor (지정 체크박스 + 행 선택)
    event = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config=column_config,
        disabled=[col for col in display_df.columns if col != "지정"],  # '지정' 컬럼만 편집 가능
        key="screening_results_editor"
    )

    # 편집된 데이터프레임 가져오기
    edited_df = event

    # 체크박스 변경사항을 pending 상태로 저장 (DB 저장은 하지 않음)
    if not edited_df.empty and "지정" in edited_df.columns and "종목" in edited_df.columns:
        try:
            # 지정 컬럼의 모든 행을 확인
            checked_symbols = []
            for _, row in edited_df.iterrows():
                if row["지정"]:  # True인 경우
                    checked_symbols.append(row["종목"])

            new_pending = set(checked_symbols)

            # pending 상태가 변경되었으면 rerun (상단 이동만)
            if new_pending != st.session_state.checkbox_pending_pinned:
                st.session_state.checkbox_pending_pinned = new_pending
                st.rerun()

        except Exception as e:
            # 에러 발생시 로그 출력
            import traceback
            st.error(f"체크박스 처리 에러: {e}")
            st.text(traceback.format_exc())

    # 지정 종목 관리 - multiselect 컴포넌트
    st.markdown("<div style='margin: 0.5rem 0;'></div>", unsafe_allow_html=True)

    # 현재 지정된 종목과 시장의 전체 종목 리스트
    current_pinned = list(st.session_state.pinned_symbols)

    # 시장의 전체 종목 가져오기
    try:
        from infrastructure.exchanges.upbit_client import UpbitClient
        temp_exchange = UpbitClient()
        market_symbols = temp_exchange.get_market_symbols(market)
        # 스크리닝 결과와 지정 종목 포함
        all_symbols = list(set(market_symbols + [row["종목"] for row in data] + current_pinned)) if data else list(set(market_symbols + current_pinned))
    except:
        # 에러시 기존 로직 사용
        all_symbols = list(set([row["종목"] for row in data] + current_pinned)) if data else current_pinned

    all_symbols.sort()

    new_pinned_list = st.multiselect(
        "지정 종목 관리 (추가/제거)",
        options=all_symbols,
        default=current_pinned,
        key="pinned_symbols_multiselect",
        help="지정 종목을 선택/해제하세요. 지정 종목은 스크리닝 결과와 무관하게 유지됩니다."
    )

    # multiselect 변경 감지 및 DB 동기화 (multiselect는 즉시 DB 저장)
    new_pinned_symbols_from_multi = set(new_pinned_list)
    if new_pinned_symbols_from_multi != st.session_state.pinned_symbols:
        # 추가된 종목
        added = new_pinned_symbols_from_multi - st.session_state.pinned_symbols
        for symbol in added:
            pinned_repo.add(symbol, market)

        # 제거된 종목
        removed = st.session_state.pinned_symbols - new_pinned_symbols_from_multi
        for symbol in removed:
            pinned_repo.remove(symbol)

        # DB 저장 상태와 pending 상태 모두 업데이트
        st.session_state.pinned_symbols = new_pinned_symbols_from_multi
        st.session_state.checkbox_pending_pinned = new_pinned_symbols_from_multi.copy()
        st.rerun()

    # 지정종목저장 버튼 처리 - 새 세션으로 DB에 저장
    if save_pinned_btn:
        try:
            # 디버그 정보
            debug_info = []
            debug_info.append(f"현재 DB 저장 상태: {sorted(st.session_state.pinned_symbols)}")
            debug_info.append(f"Pending 상태: {sorted(st.session_state.checkbox_pending_pinned)}")

            # pending 상태와 DB 저장 상태 비교
            added = st.session_state.checkbox_pending_pinned - st.session_state.pinned_symbols
            removed = st.session_state.pinned_symbols - st.session_state.checkbox_pending_pinned
            debug_info.append(f"추가할 종목: {sorted(added)}")
            debug_info.append(f"제거할 종목: {sorted(removed)}")

            # 새 세션으로 DB 작업
            from infrastructure.database.connection import SessionLocal
            fresh_db = SessionLocal()
            fresh_repo = PinnedSymbolRepository(fresh_db)

            try:
                # DB 동기화
                for symbol in added:
                    result = fresh_repo.add(symbol, market)
                    debug_info.append(f"추가: {symbol} -> {result}")

                for symbol in removed:
                    result = fresh_repo.remove(symbol)
                    debug_info.append(f"제거: {symbol} -> {result}")

                # 커밋
                fresh_db.commit()
                debug_info.append("커밋 완료")

                # DB에서 실제 확인
                db_check = fresh_repo.get_all_active(market=market)
                db_symbols = set([p.symbol for p in db_check])
                debug_info.append(f"DB 확인 결과: {sorted(db_symbols)}")

                # 세션 상태를 DB 확인 결과로 즉시 업데이트
                st.session_state.pinned_symbols = db_symbols
                st.session_state.checkbox_pending_pinned = db_symbols.copy()

            finally:
                fresh_db.close()

            # 저장 완료 메시지 (DB 확인 결과 사용)
            if db_symbols:
                st.session_state.save_message = f"{len(db_symbols)}개의 지정 종목이 DB에 저장되었습니다."
                st.session_state.save_info = "지정 종목: " + ", ".join(sorted(db_symbols)) + "\n\n" + "\n".join(debug_info)
            else:
                st.session_state.save_message = "지정된 종목이 없습니다."
                st.session_state.save_info = "\n".join(debug_info)

        except Exception as e:
            import traceback
            st.session_state.save_message = f"저장 중 오류 발생: {e}"
            st.session_state.save_info = traceback.format_exc()

        st.rerun()

    # 다운로드 버튼 - 스크리닝 결과가 있을 때만 표시
    if data:
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        if 'screening_market' in st.session_state and 'screening_time' in st.session_state:
            file_name = f"screening_{st.session_state.screening_market}_{st.session_state.screening_time.strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            file_name = f"screening_{market}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        st.download_button(
            label="CSV 다운로드",
            data=csv,
            file_name=file_name,
            mime="text/csv"
        )

    # 저장 완료 메시지 표시 (CSV 다운로드 아래)
    if 'save_message' in st.session_state:
        if st.session_state.get('save_info'):
            st.success(st.session_state.save_message)
            st.info(st.session_state.save_info)
        else:
            st.warning(st.session_state.save_message)
        # 메시지 표시 후 삭제
        del st.session_state.save_message
        if 'save_info' in st.session_state:
            del st.session_state.save_info

    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    # 상세 정보 - 타이틀과 selectbox를 한 줄에
    title_col, select_col = st.columns([1, 3])

    with title_col:
        st.markdown("<h3 style='margin: 0; padding-top: 0.3rem;'>종목 상세 정보</h3>", unsafe_allow_html=True)

    with select_col:
        if data:
            symbol_options = [""] + [row["종목"] for row in data]
            selected_symbol = st.selectbox(
                "종목 선택",
                options=symbol_options,
                key="detail_symbol_selector",
                help="종목을 선택하면 상세 정보가 표시됩니다.",
                label_visibility="collapsed"
            )
        else:
            selected_symbol = None

    if not selected_symbol:
        st.info("위의 selectbox에서 종목을 선택하면 상세 정보가 표시됩니다.")
    else:
        # 선택된 종목의 데이터를 data에서 찾기
        selected_data = next((row for row in data if row["종목"] == selected_symbol), None)

        # results에서도 찾기 (스크리닝 결과가 있는 경우)
        selected_result = next((r for r in results if r.symbol == selected_symbol), None) if results else None

        if not selected_data:
            st.warning(f"선택된 종목 {selected_symbol}의 정보를 찾을 수 없습니다.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.write("**기본 정보**")
                st.write(f"- 종목: {selected_data['종목']}")
                st.write(f"- 총점: {selected_data.get('점수', 0):.2f}")
                if selected_result:
                    st.write(f"- 평가 시간: {selected_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            with col2:
                st.write("**세부 점수**")

                # 숫자형 세부 점수만 추출
                numeric_scores = {}
                if selected_result:
                    for key, value in selected_result.details.items():
                        if isinstance(value, (int, float)):
                            numeric_scores[key] = value
                else:
                    # 지정종목이지만 스크리닝 결과가 없는 경우 data에서 추출
                    for key, value in selected_data.items():
                        if key not in ["종목", "점수", "순위"] and isinstance(value, (int, float)):
                            numeric_scores[key] = value

                if numeric_scores:
                    # Radar chart 생성
                    import plotly.graph_objects as go

                    categories = list(numeric_scores.keys())
                    values = list(numeric_scores.values())

                    # 극단값 처리: IQR 방식으로 아웃라이어 제한
                    if values and len(values) > 3:
                        import numpy as np
                        q1 = np.percentile(values, 25)
                        q3 = np.percentile(values, 75)
                        iqr = q3 - q1
                        # 상한값: Q3 + 1.5 * IQR
                        upper_bound = q3 + 1.5 * iqr

                        # 극단값을 상한값으로 제한
                        capped_values = [min(v, upper_bound) for v in values]
                        # radial axis 범위 설정
                        max_range = upper_bound * 1.1
                    elif values:
                        capped_values = values
                        max_range = max(values) * 1.1 if values else 100
                    else:
                        capped_values = values
                        max_range = 100

                    fig = go.Figure()

                    fig.add_trace(go.Scatterpolar(
                        r=capped_values,
                        theta=categories,
                        fill='toself',
                        name=selected_result.symbol,
                        line=dict(color='#54A0FD'),
                        fillcolor='rgba(84, 160, 253, 0.3)'
                    ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor='#262730',
                            radialaxis=dict(
                                visible=True,
                                range=[0, max_range],
                                gridcolor='#3d3d4a',
                                linecolor='#3d3d4a'
                            ),
                            angularaxis=dict(
                                gridcolor='#3d3d4a',
                                linecolor='#3d3d4a',
                                color='#FAFAFA'
                            )
                        ),
                        showlegend=False,
                        height=400,
                        margin=dict(l=80, r=80, t=40, b=40),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#FAFAFA')
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    # 세부 점수가 없는 경우
                    st.info("스크리닝을 실행하면 세부 점수가 표시됩니다.")

                # 비숫자형 항목은 텍스트로 표시 (selected_result가 있을 때만)
                if selected_result:
                    non_numeric = {k: v for k, v in selected_result.details.items()
                                  if not isinstance(v, (int, float))}
                    if non_numeric:
                        st.write("**기타 정보**")
                        for key, value in non_numeric.items():
                            st.write(f"- {key}: {value}")

    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    st.markdown("<h3 style='margin-bottom: 0.8rem;'>주의사항</h3>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background-color: #40424890; border-left: 4px solid #00CCAC; padding: 16px; border-radius: 4px;'>
        <div style='font-size: 0.875rem; color: #FAFAFA; line-height: 1.6;'>
            • 스크리닝 결과는 투자 참고 자료일 뿐, 투자 결정의 근거가 될 수 없습니다<br>
            • 시장 상황에 따라 점수가 달라질 수 있습니다<br>
            • 여러 전략을 조합하여 사용하는 것을 권장합니다<br>
            • 백테스팅을 통해 전략의 유효성을 검증하세요
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    # 전략 설명 가이드 (expander)
    with st.expander("📘 전략 설명 가이드", expanded=False):
        st.markdown("""
### 모멘텀 기반 전략
가격과 거래량의 상승세를 기반으로 종목을 선정합니다.
- **가격 모멘텀**: 1일/7일/30일 가격 상승률
- **거래량 모멘텀**: 거래량 증가율
- **RSI 모멘텀**: RSI 지표 변화

**추천 상황**: 상승 추세 시장, 단기 트레이딩

---

### 거래량 기반 전략
거래 활발도를 기준으로 종목을 선정합니다.
- **거래대금**: 24시간 거래대금 순위
- **거래량 급증**: 평균 대비 거래량 증가율
- **유동성 점수**: 거래량/시가총액 비율

**추천 상황**: 변동성 확대 구간, 신규 자금 유입 시

---

### 기술지표 복합 전략
RSI, MACD, 이동평균선을 조합하여 종목을 선정합니다.
- **RSI**: 과매도/과매수 구간 판단
- **MACD**: 추세 전환 신호
- **이동평균**: 골든/데드 크로스

**추천 상황**: 추세 전환 예상 시점, 기술적 분석 선호

---

### 하이브리드 전략
여러 전략을 가중치로 조합하여 종목을 선정합니다.
- 각 전략별 점수를 계산
- 가중치를 적용하여 종합 점수 산출
- 복합적인 관점에서 종목 평가

**추천 상황**: 안정적인 종목 선정, 리스크 분산
        """)

if __name__ == "__main__":
    main()
