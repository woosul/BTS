"""
모달창 공통 유틸리티
"""
import streamlit as st


def apply_modal_styles():
    """
    모달창 공통 스타일 적용
    
    - 체크박스 라벨 폰트 크기
    - 슬라이더 라벨 폰트 크기
    - 기타 공통 스타일
    """
    st.markdown("""
        <style>
        /* 체크박스 라벨 폰트 설정 - 체크박스 내부에만 적용 */
        label[data-testid*="stCheckbox"] [data-testid="stMarkdownContainer"] p {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-size: 0.875rem !important;
            font-weight: 400 !important;
            line-height: 1.5 !important;
        }
        
        label[data-testid*="stCheckbox"] p {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-size: 0.875rem !important;
            font-weight: 400 !important;
        }
        
        /* 슬라이더 라벨 폰트 설정 */
        [data-testid="stSlider"] label {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-size: 0.875rem !important;
            font-weight: 400 !important;
        }
        [data-testid="stSlider"] label div {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-size: 0.875rem !important;
            font-weight: 400 !important;
        }
        </style>
    """, unsafe_allow_html=True)
