"""
필터링 페이지

종목 사전 필터링 프로파일 관리
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.database.connection import SessionLocal
from application.services.filtering_service import FilteringService
from infrastructure.exchanges.upbit_client import UpbitClient
from domain.entities.filter_profile import (
    FilterProfile,
    FilterCondition,
    FilterProfileCreate,
    FilterProfileUpdate
)
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="Filtering - BTS",
    page_icon="🔍",
    layout="wide"
)

# 로고 설정
logo_path = str(project_root / "resource" / "image" / "peaknine_logo_01.svg")
icon_path = str(project_root / "resource" / "image" / "peaknine_02.png")
st.logo(
    image=logo_path,
    icon_image=icon_path
)


def get_services():
    """서비스 인스턴스 가져오기"""
    if 'filtering_db' not in st.session_state:
        st.session_state.filtering_db = SessionLocal()
    
    if 'filtering_service' not in st.session_state:
        exchange = UpbitClient(
            settings.upbit_access_key,
            settings.upbit_secret_key
        )
        st.session_state.filtering_service = FilteringService(
            st.session_state.filtering_db,
            exchange
        )
    
    return st.session_state.filtering_service


def render_filter_condition_ui(market: str, loaded_conditions: FilterCondition = None) -> FilterCondition:
    """필터 조건 UI 렌더링
    
    Args:
        market: 시장 (KRW, BTC 등)
        loaded_conditions: 로드된 필터 조건 (있을 경우 기본값으로 설정)
    """
    # 필터 조건 섹션 폰트 크기 조정 CSS (bold 유지, 섹션 타이틀 포함)
    st.markdown("""
        <style>
        /* 사이드바의 모든 텍스트 폰트 크기 */
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stCheckbox label,
        [data-testid="stSidebar"] .stNumberInput label,
        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stTextArea label,
        [data-testid="stSidebar"] .stSelectbox label {
            font-size: 0.875rem !important;
        }
        
        /* 사이드바의 h4, h5 폰트 크기 */
        [data-testid="stSidebar"] h4 {
            font-size: 1rem !important;
        }
        [data-testid="stSidebar"] h5 {
            font-size: 0.9rem !important;
        }
        
        /* 사이드바의 input 박스 폰트 크기 */
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] select {
            font-size: 0.875rem !important;
        }
        
        /* bold는 유지 */
        [data-testid="stSidebar"] strong,
        [data-testid="stSidebar"] b,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5 {
            font-weight: 600 !important;
        }
        
        /* 숫자 배지 스타일 */
        .filter-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            background-color: #6c757d;
            color: white;
            border-radius: 4px;
            font-size: 1rem;
            font-weight: 600;
            margin-right: 8px;
            flex-shrink: 0;
        }
        
        /* h5와 배지를 포함한 컨테이너 정렬 - 직접 자식만 */
        [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] h5 {
            display: flex !important;
            align-items: center !important;
        }
        
        /* 전체 사이트 체크박스 border radius - 매우 구체적인 선택자 */
        /* 체크박스 input 요소 */
        input[type="checkbox"] {
            border-radius: 2px !important;
            -webkit-border-radius: 2px !important;
            -moz-border-radius: 2px !important;
        }
        
        [data-testid="stCheckbox"] input[type="checkbox"] {
            border-radius: 2px !important;
            -webkit-border-radius: 2px !important;
            -moz-border-radius: 2px !important;
        }
        
        /* 체크박스 시각적 요소 - st-cx 클래스 */
        span.st-cx {
            border-radius: 2px !important;
            -webkit-border-radius: 2px !important;
            -moz-border-radius: 2px !important;
        }
        
        span[class*="st-cx"][class*="st-b4"] {
            border-radius: 2px !important;
            -webkit-border-radius: 2px !important;
            -moz-border-radius: 2px !important;
        }
        
        /* 모든 st- 클래스를 가진 span (체크박스 시각적 요소) */
        [data-baseweb="checkbox"] span[class^="st-"] {
            border-radius: 2px !important;
            -webkit-border-radius: 2px !important;
            -moz-border-radius: 2px !important;
        }
        
        /* 체크박스 컨테이너 */
        div[data-baseweb="checkbox"] {
            border-radius: 2px !important;
        }
        
        div[data-baseweb="checkbox"] > div {
            border-radius: 2px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 필터 조건 설정")
    
    # 필터 사용 여부
    default_enabled = loaded_conditions.enabled if loaded_conditions else True
    enabled = st.checkbox("필터 활성화", value=default_enabled, help="체크 해제 시 모든 필터 무시")
    
    st.markdown("---")
    
    # 0. 상장폐지/거래정지 필터
    st.markdown('<h5><span class="filter-badge">0</span>상장폐지 & 거래정지</h5>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        default_exclude_delisting = loaded_conditions.exclude_delisting if loaded_conditions else True
        exclude_delisting = st.checkbox(
            "상장폐지 예정 제외",
            value=default_exclude_delisting,
            disabled=not enabled
        )
    with col2:
        default_exclude_suspended = loaded_conditions.exclude_suspended if loaded_conditions else True
        exclude_suspended = st.checkbox(
            "거래정지 종목 제외",
            value=default_exclude_suspended,
            disabled=not enabled
        )
    
    st.markdown("---")
    
    # 1. 거래대금 필터
    st.markdown('<h5><span class="filter-badge">1</span>거래대금</h5>', unsafe_allow_html=True)
    default_use_trading = bool(loaded_conditions and loaded_conditions.min_trading_value)
    use_trading_value = st.checkbox("거래대금 필터 사용", value=default_use_trading, disabled=not enabled)
    min_trading_value = None
    if use_trading_value:
        default_trading_billion = (loaded_conditions.min_trading_value / 1e8) if (loaded_conditions and loaded_conditions.min_trading_value) else 100.0
        value_billion = st.number_input(
            "최소 거래대금 (억원)",
            min_value=0.0,
            max_value=10000.0,
            value=default_trading_billion,
            step=10.0,
            disabled=not enabled
        )
        min_trading_value = value_billion * 100_000_000  # 억원 → 원
    
    st.markdown("---")
    
    # 2. 시가총액 필터
    st.markdown('<h5><span class="filter-badge">2</span>시가총액</h5>', unsafe_allow_html=True)
    default_use_market_cap = bool(loaded_conditions and (loaded_conditions.min_market_cap or loaded_conditions.max_market_cap))
    use_market_cap = st.checkbox("시가총액 필터 사용", value=default_use_market_cap, disabled=not enabled)
    min_market_cap = None
    max_market_cap = None
    if use_market_cap:
        col1, col2 = st.columns(2)
        with col1:
            default_use_min_cap = bool(loaded_conditions and loaded_conditions.min_market_cap)
            use_min_cap = st.checkbox("최소값 설정", value=default_use_min_cap or (not loaded_conditions), disabled=not enabled)
            if use_min_cap:
                default_min_cap = (loaded_conditions.min_market_cap / 1e8) if (loaded_conditions and loaded_conditions.min_market_cap) else 5000.0
                min_cap_billion = st.number_input(
                    "최소 시가총액 (억원)",
                    min_value=0.0,
                    max_value=100000.0,
                    value=default_min_cap,
                    step=100.0,
                    disabled=not enabled
                )
                min_market_cap = min_cap_billion * 100_000_000
        
        with col2:
            default_use_max_cap = bool(loaded_conditions and loaded_conditions.max_market_cap)
            use_max_cap = st.checkbox("최대값 설정", value=default_use_max_cap, disabled=not enabled)
            if use_max_cap:
                default_max_cap = (loaded_conditions.max_market_cap / 1e8) if (loaded_conditions and loaded_conditions.max_market_cap) else 10000.0
                max_cap_billion = st.number_input(
                    "최대 시가총액 (억원)",
                    min_value=0.0,
                    max_value=1000000.0,
                    value=default_max_cap,
                    step=100.0,
                    disabled=not enabled
                )
                max_market_cap = max_cap_billion * 100_000_000
    
    st.markdown("---")
    
    # 3. 상장기간 필터
    st.markdown('<h5><span class="filter-badge">3</span>상장기간</h5>', unsafe_allow_html=True)
    default_use_listing = bool(loaded_conditions and loaded_conditions.min_listing_days)
    use_listing_period = st.checkbox("상장기간 필터 사용", value=default_use_listing, disabled=not enabled)
    if use_listing_period:
        st.warning("⚠️ **주의**: 상장기간 필터는 Upbit API Rate Limit으로 인해 실행 시간이 오래 걸립니다 (약 15~20초). 자주 사용하지 마세요.")
    min_listing_days = None
    if use_listing_period:
        default_listing_days = loaded_conditions.min_listing_days if (loaded_conditions and loaded_conditions.min_listing_days) else 180
        min_listing_days = st.number_input(
            "최소 상장 일수",
            min_value=0,
            max_value=3650,
            value=default_listing_days,
            step=30,
            help="예: 180일 = 6개월",
            disabled=not enabled
        )
    
    st.markdown("---")
    
    # 4. 가격범위 필터
    st.markdown('<h5><span class="filter-badge">4</span>가격범위</h5>', unsafe_allow_html=True)
    default_use_price = bool(loaded_conditions and (loaded_conditions.min_price or loaded_conditions.max_price))
    use_price_range = st.checkbox("가격범위 필터 사용", value=default_use_price, disabled=not enabled)
    min_price = None
    max_price = None
    if use_price_range:
        col1, col2 = st.columns(2)
        with col1:
            default_use_min_price = bool(loaded_conditions and loaded_conditions.min_price)
            use_min_price = st.checkbox("최소 가격 설정", value=default_use_min_price or (not loaded_conditions), disabled=not enabled)
            if use_min_price:
                default_min_price = loaded_conditions.min_price if (loaded_conditions and loaded_conditions.min_price) else 500.0
                min_price = st.number_input(
                    "최소 가격 (KRW)",
                    min_value=0.0,
                    max_value=100000000.0,
                    value=default_min_price,
                    step=100.0,
                    disabled=not enabled
                )
        
        with col2:
            default_use_max_price = bool(loaded_conditions and loaded_conditions.max_price)
            use_max_price = st.checkbox("최대 가격 설정", value=default_use_max_price or (not loaded_conditions), disabled=not enabled)
            if use_max_price:
                default_max_price = loaded_conditions.max_price if (loaded_conditions and loaded_conditions.max_price) else 10000000.0
                max_price = st.number_input(
                    "최대 가격 (KRW)",
                    min_value=0.0,
                    max_value=100000000.0,
                    value=default_max_price,
                    step=1000.0,
                    disabled=not enabled
                )
    
    st.markdown("---")
    
    # 5. 변동성 필터
    st.markdown('<h5><span class="filter-badge">5</span>변동성 (7일 기준)</h5>', unsafe_allow_html=True)
    default_use_volatility = bool(loaded_conditions and (loaded_conditions.min_volatility or loaded_conditions.max_volatility))
    use_volatility = st.checkbox("변동성 필터 사용", value=default_use_volatility, disabled=not enabled)
    min_volatility = None
    max_volatility = None
    if use_volatility:
        col1, col2 = st.columns(2)
        with col1:
            default_min_vol = loaded_conditions.min_volatility if (loaded_conditions and loaded_conditions.min_volatility) else 3.0
            min_volatility = st.number_input(
                "최소 변동성 (%)",
                min_value=0.0,
                max_value=100.0,
                value=default_min_vol,
                step=0.5,
                disabled=not enabled
            )
        
        with col2:
            default_max_vol = loaded_conditions.max_volatility if (loaded_conditions and loaded_conditions.max_volatility) else 15.0
            max_volatility = st.number_input(
                "최대 변동성 (%)",
                min_value=0.0,
                max_value=100.0,
                value=default_max_vol,
                step=0.5,
                disabled=not enabled
            )
    
    st.markdown("---")
    
    # 6. 스프레드 필터
    st.markdown('<h5><span class="filter-badge">6</span>스프레드 (매수/매도 1호가)</h5>', unsafe_allow_html=True)
    default_use_spread = bool(loaded_conditions and loaded_conditions.max_spread)
    use_spread = st.checkbox("스프레드 필터 사용", value=default_use_spread, disabled=not enabled)
    max_spread = None
    if use_spread:
        default_max_spread = loaded_conditions.max_spread if (loaded_conditions and loaded_conditions.max_spread) else 0.3
        max_spread = st.number_input(
            "최대 스프레드 (%)",
            min_value=0.0,
            max_value=10.0,
            value=default_max_spread,
            step=0.1,
            disabled=not enabled
        )
    
    # FilterCondition 객체 생성
    return FilterCondition(
        enabled=enabled,
        exclude_delisting=exclude_delisting,
        exclude_suspended=exclude_suspended,
        min_trading_value=min_trading_value,
        min_market_cap=min_market_cap,
        max_market_cap=max_market_cap,
        min_listing_days=min_listing_days,
        min_price=min_price,
        max_price=max_price,
        min_volatility=min_volatility,
        max_volatility=max_volatility,
        max_spread=max_spread
    )


def main():
    # 전역 스타일 적용
    from presentation.styles.global_styles import apply_global_styles
    apply_global_styles()
    
    st.title("종목 필터링")
    st.markdown("---")
    
    # 서비스 초기화
    filtering_service = get_services()
    
    # 사이드바: 필터 설정
    with st.sidebar:
        st.markdown("### 필터 프로파일")
        
        # 시장 선택
        market = st.selectbox(
            "대상 시장",
            options=["KRW", "BTC"],
            help="필터링할 시장 선택"
        )
        
        # 기존 프로파일 로드
        st.markdown("#### 저장된 프로파일")
        profiles = filtering_service.get_all_profiles(market=market)
        
        selected_profile_name = "새 프로파일"  # 기본값 설정
        
        if profiles:
            profile_names = ["새 프로파일"] + [p.name for p in profiles]
            
            # 세션에 로드된 프로파일이 있으면 해당 프로파일을 기본 선택
            default_index = 0  # "새 프로파일"
            if 'loaded_profile' in st.session_state:
                try:
                    default_index = profile_names.index(st.session_state.loaded_profile.name)
                except (ValueError, AttributeError):
                    default_index = 0
            
            selected_profile_name = st.selectbox(
                "프로파일 선택",
                options=profile_names,
                index=default_index,
                key="profile_selector"
            )
            
            # 기존 프로파일 로드
            if selected_profile_name != "새 프로파일":
                selected_profile = next(p for p in profiles if p.name == selected_profile_name)
                if st.button("프로파일 로드"):
                    st.session_state.loaded_profile = selected_profile
                    st.success(f"'{selected_profile.name}' 프로파일을 로드했습니다.")
                    st.rerun()
            else:
                # '새 프로파일' 선택 시 로드된 프로파일 제거
                if 'loaded_profile' in st.session_state:
                    del st.session_state.loaded_profile
        else:
            st.info("저장된 프로파일이 없습니다.")
        
        st.markdown("---")
        
        # 필터 조건 설정
        # 프로파일이 로드되어 있으면 해당 조건을 기본값으로 사용
        loaded_cond = None
        if 'loaded_profile' in st.session_state and selected_profile_name != "새 프로파일":
            loaded_cond = st.session_state.loaded_profile.conditions
            st.info(f"로드됨 : {st.session_state.loaded_profile.name}")
        
        # 필터 UI 렌더링 (항상 표시, 로드된 조건을 기본값으로 사용)
        conditions = render_filter_condition_ui(market, loaded_cond)
        
        st.markdown("---")
        
        # 프로파일 저장
        st.markdown("### 프로파일 저장")
        profile_name = st.text_input("프로파일 이름", value="", placeholder="예: 보수적 필터")
        profile_desc = st.text_area("설명 (선택)", value="", placeholder="필터 프로파일 설명")
        
        if st.button("프로파일 저장", type="primary"):
            if not profile_name:
                st.error("프로파일 이름을 입력하세요.")
            else:
                try:
                    # 동일 이름 체크
                    existing = filtering_service.get_profile_by_name(profile_name)
                    if existing:
                        st.error(f"'{profile_name}' 프로파일이 이미 존재합니다.")
                    else:
                        profile_data = FilterProfileCreate(
                            name=profile_name,
                            description=profile_desc if profile_desc else None,
                            market=market,
                            conditions=conditions,
                            is_active=True
                        )
                        new_profile = filtering_service.create_profile(profile_data)
                        
                        # 저장된 프로파일을 자동으로 로드
                        st.session_state.loaded_profile = new_profile
                        
                        st.success(f"'{profile_name}' 프로파일이 저장되고 로드되었습니다!")
                        logger.info(f"필터 프로파일 생성 및 로드: {profile_name} (ID: {new_profile.id})")
                        st.rerun()
                except Exception as e:
                    logger.error(f"프로파일 저장 실패: {e}")
                    st.error(f"저장 실패: {e}")
    
    # 메인: 필터 테스트 및 통계
    st.markdown("## 필터 테스트")
    
    # 세션 상태 초기화
    if 'filter_cache' not in st.session_state:
        st.session_state.filter_cache = {}
    if 'filter_results' not in st.session_state:
        st.session_state.filter_results = None
    if 'filter_stats' not in st.session_state:
        st.session_state.filter_stats = None
    if 'filter_initial_count' not in st.session_state:
        st.session_state.filter_initial_count = None
    if 'is_from_saved' not in st.session_state:
        st.session_state.is_from_saved = False
    
    # 버튼 스타일 CSS - 간격 16px, 버튼 크기 조정 (사이드바 제외)
    st.markdown("""
        <style>
        /* 버튼 컬럼 간격 조정 - 메인 컨텐츠만 */
        [data-testid="stAppViewBlockContainer"] div[data-testid="column"] {
            padding-left: 8px !important;
            padding-right: 8px !important;
        }
        [data-testid="stAppViewBlockContainer"] div[data-testid="column"]:first-child {
            padding-left: 0 !important;
        }
        /* 버튼 내부 패딩 조정 - 메인 컨텐츠만 */
        [data-testid="stAppViewBlockContainer"] button {
            padding: 0.4rem 0.6rem !important;
            white-space: nowrap !important;
            font-size: 0.875rem !important;
            min-width: 120px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 버튼과 메시지 창을 가로로 배치
    col1, col2, col3, col_msg = st.columns([1.2, 1.2, 1.5, 8], gap="small")
    
    with col1:
        # 필터 실행 버튼
        run_test_button = st.button("필터 실행", type="primary", use_container_width=True)
    
    with col2:
        # 결과 저장 버튼 (필터링 후에만 활성화)
        save_button_disabled = st.session_state.filter_results is None
        save_button = st.button("결과 저장", use_container_width=True, disabled=save_button_disabled)
    
    with col3:
        # 저장된 결과 불러오기 버튼
        saved_count = filtering_service.get_saved_symbols_count()
        load_button = st.button(f"저장 결과 ({saved_count})", use_container_width=True)
    
    with col_msg:
        # 필터 실행 전/후에 따라 다른 메시지 표시 (다크 모드 스타일)
        if st.session_state.filter_results is None:
            message_html = """
                <div style="
                    background-color: #1e3a4c;
                    border: 1px solid #2d5468;
                    color: #a8d5e2;
                    padding: 0.5rem 0.75rem;
                    font-size: 0.875rem;
                    display: flex;
                    align-items: center;
                    border-radius: 4px;
                    height: 40px;
                    box-sizing: border-box;
                ">
                    현재 시장의 모든 종목에 필터를 적용하여 결과를 확인합니다.
                </div>
            """
        else:
            filtered_count = len(st.session_state.filter_results)
            initial_count = st.session_state.filter_initial_count or 0
            message_html = f"""
                <div style="
                    background-color: #1e3a4c;
                    border: 1px solid #2d5468;
                    color: #a8d5e2;
                    padding: 0.5rem 0.75rem;
                    font-size: 0.875rem;
                    display: flex;
                    align-items: center;
                    border-radius: 4px;
                    height: 40px;
                    box-sizing: border-box;
                ">
                    필터링된 종목: <strong style="margin-left: 0.5rem;">{filtered_count}</strong> / {initial_count}
                </div>
            """
        
        st.markdown(message_html, unsafe_allow_html=True)
    
    if run_test_button:
        with st.spinner("필터링 중..."):
            try:
                # 시장의 모든 종목 조회
                exchange = UpbitClient(settings.upbit_access_key, settings.upbit_secret_key)
                all_symbols = exchange.get_market_symbols(market)
                
                # 초기 종목 수 저장
                st.session_state.filter_initial_count = len(all_symbols)
                
                # 임시 프로파일 생성
                temp_profile = FilterProfile(
                    name="테스트",
                    market=market,
                    conditions=conditions
                )
                
                # 필터 적용
                filtered_symbols, stats_list = filtering_service.apply_filters(
                    all_symbols,
                    temp_profile,
                    return_stats=True
                )
                
                # 결과 저장
                st.session_state.filter_results = filtered_symbols
                st.session_state.filter_stats = stats_list
                st.session_state.filter_conditions = conditions  # 필터 조건도 저장
                # 프로파일명 저장: 로드된 프로파일이 있으면 그 이름, 없으면 선택된 프로파일명 사용
                if 'loaded_profile' in st.session_state and selected_profile_name != "새 프로파일":
                    st.session_state.filter_profile_name = selected_profile_name
                else:
                    st.session_state.filter_profile_name = selected_profile_name if selected_profile_name != "새 프로파일" else "테스트"
                st.session_state.is_from_saved = False  # 새로 실행한 결과
                
                # 페이지 리로드하여 info 메시지 업데이트
                st.rerun()
                
            except Exception as e:
                logger.error(f"필터 테스트 실패: {e}")
                st.error(f"테스트 실패: {e}")
                import traceback
                st.text(traceback.format_exc())
    
    # 결과 저장 버튼 처리
    if save_button:
        if st.session_state.filter_results:
            try:
                # 프로파일명 가져오기 (없으면 "테스트")
                profile_name = st.session_state.get('filter_profile_name', '테스트')
                success = filtering_service.save_filtered_symbols(
                    st.session_state.filter_results,
                    profile_name
                )
                if success:
                    st.success(f"✓ 필터링 결과 저장 완료: {len(st.session_state.filter_results)}개 종목 (프로파일: {profile_name})")
                    st.rerun()
                else:
                    st.error("필터링 결과 저장 실패")
            except Exception as e:
                st.error(f"저장 실패: {e}")
                logger.error(f"필터링 결과 저장 실패: {e}")
    
    # 저장된 결과 불러오기 버튼 처리
    if load_button:
        try:
            saved_symbols = filtering_service.get_saved_symbols()
            if saved_symbols:
                # 세션에 저장된 결과 로드
                st.session_state.filter_results = saved_symbols
                st.session_state.filter_initial_count = len(saved_symbols)  # 초기 수를 saved 개수로
                st.session_state.filter_stats = []  # 통계는 없음
                st.session_state.is_from_saved = True  # 저장된 결과에서 로드했음을 표시
                st.rerun()
            else:
                st.warning("저장된 필터링 결과가 없습니다.")
        except Exception as e:
            st.error(f"불러오기 실패: {e}")
            logger.error(f"저장된 결과 불러오기 실패: {e}")
    
    # 필터링 결과 표시 (세션에서 가져옴)
    if st.session_state.filter_results is not None and st.session_state.filter_stats is not None:
        # 필터링 통계 표시
        st.markdown("### 필터링 단계별 통계")
        
        stats_data = []
        for stat in st.session_state.filter_stats:
            stats_data.append({
                "단계": stat.stage_name,
                "이전": stat.symbols_before,
                "이후": stat.symbols_after,
                "제외": stat.filtered_count,
                "비율 (%)": stat.filtered_percentage,  # 숫자 타입 유지
                "실행시간 (ms)": stat.execution_time_ms  # 숫자 타입 유지
            })
        
        if stats_data:
            st.dataframe(
                stats_data, 
                width='stretch', 
                hide_index=True,
                column_config={
                    "비율 (%)": st.column_config.NumberColumn(
                        "비율 (%)",
                        format="%.1f"
                    ),
                    "실행시간 (ms)": st.column_config.NumberColumn(
                        "실행시간 (ms)",
                        format="%.1f"
                    )
                }
            )
        
        # 필터링된 종목 목록 (상세 테이블)
        # 저장된 결과인지 확인
        is_from_saved = st.session_state.get('is_from_saved', False)
        if is_from_saved:
            # 마지막 필터링 시각 및 프로파일명 조회
            last_time = filtering_service.get_last_filtered_time()
            profile_name = filtering_service.get_saved_profile_name()
            
            # 제목과 부가 정보를 같은 줄에 표시 (제목 옆에 24px gap, 수직 가운데 정렬)
            info_parts = []
            if profile_name:
                info_parts.append(f"프로파일: <strong>{profile_name}</strong>")
            if last_time:
                info_parts.append(f"저장 시각: {last_time}")
            
            info_text = " | ".join(info_parts) if info_parts else ""
            
            st.markdown(
                f"""
                <div style='display: flex; align-items: baseline; margin-bottom: 1rem;'>
                    <h3 style='margin: 0; padding: 0;'>필터링된 종목 목록 [+]</h3>
                    <span style='margin-left: 24px; padding-top: 2px; font-size: 0.9rem; color: #4a5568;'>{info_text}</span>
                </div>
                """, 
                unsafe_allow_html=True
            )
        else:
            st.markdown("### 필터링된 종목 목록")
        
        if st.session_state.filter_results:
            try:
                import pandas as pd
                
                # 저장된 결과인 경우 실시간 데이터 조회 필요
                if is_from_saved:
                    # 캐시가 비어있으므로 Exchange API를 통해 실시간 데이터 조회
                    with st.spinner("상세 정보 조회 중..."):
                        exchange = UpbitClient(settings.upbit_access_key, settings.upbit_secret_key)
                        details = []
                        for i, symbol in enumerate(st.session_state.filter_results, 1):
                            try:
                                # Ticker 상세 정보 조회 (현재가 + 거래대금)
                                ticker_detail = exchange.get_ticker_detail(symbol)
                                
                                details.append({
                                    'no': i,
                                    'symbol': symbol,
                                    'korean_name': '-',
                                    'trading_value': ticker_detail.get('acc_trade_price_24h', 0),
                                    'market_cap': None,
                                    'listing_days': None,
                                    'current_price': ticker_detail.get('trade_price', 0),
                                    'volatility': None,
                                    'spread': None,
                                    'note': ''
                                })
                            except Exception as e:
                                logger.error(f"{symbol} 상세 정보 조회 실패: {e}")
                                details.append({
                                    'no': i,
                                    'symbol': symbol,
                                    'korean_name': '-',
                                    'trading_value': 0,
                                    'market_cap': None,
                                    'listing_days': None,
                                    'current_price': 0,
                                    'volatility': None,
                                    'spread': None,
                                    'note': '조회 실패'
                                })
                else:
                    # 필터링 직후에는 캐시된 데이터 사용
                    details = filtering_service.get_symbol_details(st.session_state.filter_results)
                
                # 필터 조건 가져오기
                filter_cond = st.session_state.get('filter_conditions')
                min_listing_days = filter_cond.min_listing_days if filter_cond else None
                
                # DataFrame 생성
                df_data = []
                for detail in details:
                    # 거래대금 (억원)
                    trading_value = float(detail['trading_value']) / 100_000_000.0 if detail['trading_value'] else 0.0
                    
                    # 시가총액 (억원)
                    market_cap = float(detail['market_cap']) / 100_000_000.0 if detail['market_cap'] else 0.0
                    
                    # 상장기간 표시 - 필터 조건 표시
                    if min_listing_days and detail['listing_days']:
                        listing_display = f"{min_listing_days}일 이상"
                    elif detail['listing_days']:
                        listing_display = f"{detail['listing_days']}일"
                    else:
                        listing_display = "-"
                    
                    # 가격 (원)
                    current_price = float(detail['current_price']) if detail['current_price'] else 0.0
                    
                    # 변동성 (%)
                    volatility = float(detail['volatility']) if detail['volatility'] else 0.0
                    
                    # 스프레드 (%)
                    spread = float(detail['spread']) if detail['spread'] else 0.0
                    
                    df_data.append({
                        '순번': int(detail['no']),
                        '종목코드': str(detail['symbol']),
                        '거래대금': trading_value,
                        '시가총액': market_cap,
                        '상장기간': listing_display,
                        '가격': current_price,
                        '변동성': volatility,
                        '스프레드': spread,
                        '비고': str(detail['note'])
                    })
                
                df = pd.DataFrame(df_data)
                
                # 거래대금 순으로 정렬 (내림차순)
                df = df.sort_values('거래대금', ascending=False).reset_index(drop=True)
                
                # 순번 재정렬
                df['순번'] = range(1, len(df) + 1)
                
                # 숫자 타입 유지 - Streamlit이 자동으로 우측 정렬함
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    height=400,
                    column_config={
                        '순번': st.column_config.NumberColumn('순번'),
                        '종목코드': st.column_config.TextColumn('종목코드'),
                        '거래대금': st.column_config.NumberColumn('거래대금(억)', format='%.2f'),
                        '시가총액': st.column_config.NumberColumn('시가총액(억)', format='%.2f'),
                        '상장기간': st.column_config.TextColumn('상장기간'),
                        '가격': st.column_config.NumberColumn('가격(원)', format='%.0f'),
                        '변동성': st.column_config.NumberColumn('변동성(%)', format='%.2f'),
                        '스프레드': st.column_config.NumberColumn('스프레드(%)', format='%.2f'),
                        '비고': st.column_config.TextColumn('비고')
                    }
                )
                
            except Exception as e:
                st.error(f"상세 테이블 생성 실패: {e}")
                logger.error(f"상세 테이블 생성 실패: {e}")
                import traceback
                st.text(traceback.format_exc())
        else:
            st.warning("필터 조건을 만족하는 종목이 없습니다.")
    
    # 저장된 프로파일 관리
    st.markdown("---")
    st.markdown("## 저장된 프로파일")
    
    # Expander 제목의 폰트 크기를 0.875rem으로 조정하는 CSS
    st.markdown("""
        <style>
        [data-testid="stExpander"] summary p {
            font-size: 0.875rem !important;
        }
        [data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p {
            font-size: 0.875rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    profiles = filtering_service.get_all_profiles()
    
    if profiles:
        for profile in profiles:
            status_text = "[활성]" if profile.is_active else "[비활성]"
            with st.expander(f"{status_text} {profile.name} ({profile.market})", expanded=False):
                # 프로파일 정보와 버튼을 같은 줄에 배치
                col_info, col_btn1, col_btn2 = st.columns([6, 1, 1])
                
                with col_info:
                    # 테이블 border 제거 CSS 및 좌측 항목 deep gray 적용
                    st.markdown("""
                        <style>
                        .profile-table table {
                            border: none !important;
                            font-size: 0.875rem;
                            table-layout: fixed;
                            width: 100%;
                        }
                        .profile-table th, .profile-table td {
                            border: none !important;
                            padding: 4px 8px;
                        }
                        .profile-table th {
                            color: #555;
                            text-align: left;
                            font-weight: normal;
                        }
                        .profile-table th:first-child {
                            width: 180px;
                        }
                        .profile-table th:nth-child(2) {
                            width: auto;
                        }
                        .profile-table td:first-child {
                            color: #555;
                            width: 180px;
                            white-space: nowrap;
                        }
                        .profile-table td:nth-child(2) {
                            width: auto;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    # 필터 조건 수집
                    cond = profile.conditions
                    filters_active = []
                    if cond.exclude_delisting:
                        filters_active.append(("상장폐지 제외", "제외"))
                    if cond.exclude_suspended:
                        filters_active.append(("거래정지 제외", "제외"))
                    if cond.min_trading_value:
                        filters_active.append(("거래대금", f"≥ {cond.min_trading_value/1e9:.1f}B"))
                    if cond.min_market_cap or cond.max_market_cap:
                        min_cap = f"{cond.min_market_cap/1e9:.1f}B" if cond.min_market_cap else "없음"
                        max_cap = f"{cond.max_market_cap/1e9:.1f}B" if cond.max_market_cap else "없음"
                        filters_active.append(("시가총액", f"{min_cap} ~ {max_cap}"))
                    if cond.min_listing_days:
                        filters_active.append(("상장기간", f"≥ {cond.min_listing_days}일"))
                    if cond.min_price or cond.max_price:
                        min_price = f"{cond.min_price:,}원" if cond.min_price else "없음"
                        max_price = f"{cond.max_price:,}원" if cond.max_price else "없음"
                        filters_active.append(("가격범위", f"{min_price} ~ {max_price}"))
                    if cond.min_volatility or cond.max_volatility:
                        filters_active.append(("변동성", f"{cond.min_volatility}% ~ {cond.max_volatility}%"))
                    if cond.max_spread:
                        filters_active.append(("스프레드", f"≤ {cond.max_spread}%"))
                    
                    # 마크다운 테이블 생성
                    markdown_content = '<div class="profile-table">\n\n'
                    markdown_content += "| 항목 | 값 |\n"
                    markdown_content += "|------|------|\n"
                    markdown_content += f"| 설명 | {profile.description or '없음'} |\n"
                    markdown_content += f"| 생성일 | {profile.created_at.strftime('%Y-%m-%d %H:%M')} |\n"
                    markdown_content += f"| 상태 | {'활성화' if profile.is_active else '비활성화'} |\n"
                    markdown_content += "| [적용된 필터조건] | |\n"
                    
                    if filters_active:
                        for filter_name, filter_value in filters_active:
                            markdown_content += f"| {filter_name} | {filter_value} |\n"
                    else:
                        markdown_content += "| 필터 | 없음 |\n"
                    
                    markdown_content += '\n</div>'
                    st.markdown(markdown_content, unsafe_allow_html=True)
                
                with col_btn1:
                    if profile.is_active:
                        if st.button("비활성화", key=f"deactivate_{profile.id}", use_container_width=True):
                            filtering_service.deactivate_profile(profile.id)
                            st.success("비활성화되었습니다.")
                            st.rerun()
                    else:
                        if st.button("활성화", key=f"activate_{profile.id}", use_container_width=True):
                            filtering_service.activate_profile(profile.id)
                            st.success("활성화되었습니다.")
                            st.rerun()
                
                with col_btn2:
                    if st.button("삭제", key=f"delete_{profile.id}", type="secondary", use_container_width=True):
                        # 삭제 확인을 위한 session_state 설정
                        st.session_state[f'confirm_delete_{profile.id}'] = True
                        st.rerun()
                
                # 삭제 확인 모달 (expander 밖으로 이동)
                if st.session_state.get(f'confirm_delete_{profile.id}', False):
                    @st.dialog("프로파일 삭제 확인")
                    def confirm_delete():
                        # 모달 중앙 배치 및 드래그 가능 CSS
                        st.markdown("""
                            <style>
                            /* 모달을 화면 중앙에 배치 */
                            [data-testid="stDialog"] {
                                position: fixed !important;
                                top: 50% !important;
                                left: 50% !important;
                                transform: translate(-50%, -50%) !important;
                                margin: 0 !important;
                            }
                            
                            /* 모달 제목 영역을 드래그 핸들로 만들기 */
                            [data-testid="stDialog"] > div:first-child {
                                cursor: move !important;
                                user-select: none !important;
                            }
                            </style>
                            <script>
                            // 모달 드래그 기능
                            (function() {
                                const dialog = document.querySelector('[data-testid="stDialog"]');
                                if (!dialog || dialog.dataset.draggable) return;
                                
                                dialog.dataset.draggable = 'true';
                                const header = dialog.querySelector('div:first-child');
                                if (!header) return;
                                
                                let isDragging = false;
                                let currentX, currentY, initialX, initialY;
                                
                                header.addEventListener('mousedown', dragStart);
                                document.addEventListener('mousemove', drag);
                                document.addEventListener('mouseup', dragEnd);
                                
                                function dragStart(e) {
                                    if (e.target.tagName === 'BUTTON') return;
                                    isDragging = true;
                                    initialX = e.clientX - (dialog.offsetLeft || 0);
                                    initialY = e.clientY - (dialog.offsetTop || 0);
                                }
                                
                                function drag(e) {
                                    if (!isDragging) return;
                                    e.preventDefault();
                                    currentX = e.clientX - initialX;
                                    currentY = e.clientY - initialY;
                                    dialog.style.left = currentX + 'px';
                                    dialog.style.top = currentY + 'px';
                                    dialog.style.transform = 'none';
                                }
                                
                                function dragEnd() {
                                    isDragging = false;
                                }
                            })();
                            </script>
                        """, unsafe_allow_html=True)
                        
                        st.warning(f"**'{profile.name}'** 프로파일을 정말 삭제하시겠습니까?")
                        st.caption("이 작업은 되돌릴 수 없습니다.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("취소", key=f"cancel_delete_{profile.id}", use_container_width=True):
                                # 안전하게 삭제
                                if f'confirm_delete_{profile.id}' in st.session_state:
                                    del st.session_state[f'confirm_delete_{profile.id}']
                                st.rerun()
                        with col2:
                            if st.button("삭제 확인", key=f"confirm_delete_btn_{profile.id}", type="primary", use_container_width=True):
                                if filtering_service.delete_profile(profile.id):
                                    # 안전하게 삭제
                                    if f'confirm_delete_{profile.id}' in st.session_state:
                                        del st.session_state[f'confirm_delete_{profile.id}']
                                    st.success("삭제되었습니다.")
                                    st.rerun()
                                else:
                                    st.error("삭제 실패")
                    
                    confirm_delete()
    else:
        st.info("저장된 프로파일이 없습니다. 사이드바에서 새 프로파일을 생성하세요.")


if __name__ == "__main__":
    main()
