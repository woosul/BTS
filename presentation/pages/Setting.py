"""
BTS 시스템 설정

사용자, 운영시간, 운영방법 및 운영전략에 대한 시스템 설정
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.repositories.user_settings_repository import UserSettingsRepository
from domain.entities.user_settings import UserSettings
from presentation.components.metric_cards import render_metric_card_group
from presentation.styles.global_styles import apply_global_styles
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    # 전역 스타일 적용
    apply_global_styles()
    
    st.title("시스템 설정")
    st.markdown("---")
    
    # UserSettingsRepository 인스턴스 생성
    settings_repo = UserSettingsRepository()
    
    # 시스템 설정값 불러오기
    from config.market_index_config import MarketIndexConfig

    # ==================== 1. 화면 업데이트 설정 ====================
    st.markdown("**화면 업데이트 설정**")
    
    # WebSocket 활성화 설정
    current_websocket_setting = settings_repo.get_by_key(UserSettings.WEBSOCKET_ENABLED)
    websocket_enabled = current_websocket_setting.setting_value == "True" if current_websocket_setting else True
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_websocket_enabled = st.toggle(
            "WebSocket 실시간 업데이트",
            value=websocket_enabled,
            key="websocket_toggle",
            help="ON: 대시보드 접속 시 5초마다 실시간 데이터 업데이트 | OFF: 페이지 로드 시 최신 DB 데이터만 표시"
        )
    with col2:
        if st.button("저장", key="save_websocket", use_container_width=True):
            settings_repo.upsert(
                key=UserSettings.WEBSOCKET_ENABLED,
                value=str(new_websocket_enabled),
                description="WebSocket 실시간 업데이트 활성화 여부"
            )
            st.success("저장되었습니다.")
            st.rerun()
    
    # 현재 설정 상태 표시 (메트릭 카드 타이틀 - bold 추가)
    st.markdown("<div style='color: #66686a; font-size: 0.875rem; font-weight: bold; margin-top: 1rem; margin-bottom: 0.5rem;'>실시간 데이터 수집 상태</div>", unsafe_allow_html=True)
    
    # Dashboard 활성화 여부 확인
    is_dashboard_active = websocket_enabled
    
    # 메트릭 카드 데이터 구성
    upbit_interval = MarketIndexConfig.get_collection_interval('upbit', is_dashboard_active)
    coingecko_interval = MarketIndexConfig.get_collection_interval('coingecko', is_dashboard_active)
    
    metrics_data = [
        {
            "label": "WebSocket 전송",
            "value": f"{int(MarketIndexConfig.WEBSOCKET_UPDATE_INTERVAL)}초" if websocket_enabled else "OFF",
            "delta": None
        },
        {
            "label": "업비트 수집",
            "value": f"{int(upbit_interval)}초",
            "delta": None
        },
        {
            "label": "글로벌 수집",
            "value": f"{int(coingecko_interval)}초",
            "delta": None
        },
        {
            "label": "실시간성",
            "value": "95%+" if websocket_enabled else "낮음",
            "delta": None
        }
    ]
    
    render_metric_card_group(
        title="",
        metrics=metrics_data,
        columns=4
    )

    st.markdown("---")

    # ==================== 2. 백그라운드 업데이터 설정 ====================
    st.markdown("**백그라운드 업데이트 설정**")

    # 현재 설정값 가져오기
    current_general_setting = settings_repo.get_by_key(UserSettings.GENERAL_UPDATE_INTERVAL)
    current_general_interval = int(current_general_setting.setting_value) if current_general_setting else int(MarketIndexConfig.BACKGROUND_UPDATE_INTERVAL)

    # 간격 옵션을 config에서 가져오기
    available_intervals = MarketIndexConfig.get_available_background_intervals()
    interval_options = {}
    for interval in available_intervals:
        label = MarketIndexConfig.get_background_interval_label(interval)
        interval_options[label] = interval

    # 현재 설정에 맞는 라벨 찾기
    current_general_label = MarketIndexConfig.get_background_interval_label(current_general_interval)
    if current_general_label not in interval_options:
        closest = min(interval_options.values(), key=lambda x: abs(x - current_general_interval))
        current_general_label = MarketIndexConfig.get_background_interval_label(closest)
    current_general_index = list(interval_options.keys()).index(current_general_label)

    # selectbox와 버튼을 한 줄에 배치
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_general_label = st.selectbox(
            "백그라운드 업데이트 간격",
            options=list(interval_options.keys()),
            index=current_general_index,
            key="general_update_interval_setting",
            help=f"다른 페이지에 있을 때 백그라운드에서 데이터를 수집하는 간격입니다.",
            label_visibility="collapsed"
        )
    with col2:
        save_general_btn = st.button("저장", key="save_general", use_container_width=True)

    if save_general_btn:
        selected_general_interval = interval_options[selected_general_label]

        settings_repo.upsert(
            key=UserSettings.GENERAL_UPDATE_INTERVAL,
            value=str(selected_general_interval),
            description="백그라운드 일반 업데이트 간격 (초)"
        )
        st.success("저장되었습니다.")
        st.rerun()
    
    # 현재 설정 상태 (메트릭 카드 타이틀 - bold 추가)
    st.markdown("<div style='color: #66686a; font-size: 0.875rem; font-weight: bold; margin-top: 1rem; margin-bottom: 0.5rem;'>백그라운드 수집 상태</div>", unsafe_allow_html=True)
    
    background_metrics = [
        {
            "label": "백그라운드 간격",
            "value": f"{current_general_interval}초",
            "delta": None
        },
        {
            "label": "API 최소값",
            "value": f"{MarketIndexConfig.SAFE_UPBIT_SCRAPING}초",
            "delta": None
        },
        {
            "label": "권장 설정",
            "value": "60초 이상",
            "delta": None
        },
        {
            "label": "마지막 확인",
            "value": datetime.now().strftime("%H:%M:%S"),
            "delta": None
        }
    ]
    
    render_metric_card_group(
        title="",
        metrics=background_metrics,
        columns=4
    )
    
    st.markdown("---")
    
    # ==================== 3. 데이터 소스별 수집 주기 ====================
    st.markdown("**데이터 소스별 수집 주기**")

    source_col1, source_col2 = st.columns(2)

    with source_col1:
        st.markdown("<div style='color: #66686a; font-size: 0.875rem; font-weight: bold; margin-bottom: 0.5rem;'>실시간 업데이트 (Dashboard 활성 시)</div>", unsafe_allow_html=True)
        
        st.code(f"""# 업비트 웹스크래핑 + USD/KRW
API_MIN_INTERVAL_UPBIT_SCRAPING: {MarketIndexConfig.API_MIN_INTERVAL_UPBIT_SCRAPING}  # API 문서 기준
SAFETY_MARGIN_UPBIT: {MarketIndexConfig.SAFETY_MARGIN_UPBIT}  # 안전 여유 (+20%)
SAFE_UPBIT_SCRAPING: {MarketIndexConfig.SAFE_UPBIT_SCRAPING}  # 실제 사용 (자동 계산)

# 글로벌 지수 (CoinGecko)
API_MIN_INTERVAL_COINGECKO: {MarketIndexConfig.API_MIN_INTERVAL_COINGECKO}  # API 문서 기준
SAFETY_MARGIN_COINGECKO: {MarketIndexConfig.SAFETY_MARGIN_COINGECKO}  # 안전 여유 (+25%)
SAFE_COINGECKO: {MarketIndexConfig.SAFE_COINGECKO}  # 실제 사용 (자동 계산)
""", language="python")

    with source_col2:
        st.markdown("<div style='color: #66686a; font-size: 0.875rem; font-weight: bold; margin-bottom: 0.5rem;'>백그라운드 모드</div>", unsafe_allow_html=True)
        
        st.code(f"""# 백그라운드 수집 (느린 모드)
BACKGROUND_UPDATE_INTERVAL: {current_general_interval}  # 현재 설정: {MarketIndexConfig.get_background_interval_label(current_general_interval)}

# 환율 API (Fallback)
SAFE_FXRATES: {int(MarketIndexConfig.SAFE_FXRATES)}  # {int(MarketIndexConfig.SAFE_FXRATES//3600)}시간
SAFE_CURRENCY_API: {int(MarketIndexConfig.SAFE_CURRENCY_API)}  # {int(MarketIndexConfig.SAFE_CURRENCY_API//86400)}일
""", language="python")
    
if __name__ == "__main__":
    main()
