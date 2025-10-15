"""
모달창 공통 유틸리티
"""
import streamlit as st


def apply_modal_styles():
    """
    모달창 공통 스타일 적용 (CSS만 사용)

    - 체크박스 라벨 폰트 크기
    - 슬라이더 라벨 폰트 크기
    - 모달 크기 및 위치 조정
    - 기타 공통 스타일

    Note: Streamlit의 st.dialog는 iframe 제약으로 인해 JavaScript 드래그 불가능
          CSS로 크기와 위치만 조정 가능
    """
    st.markdown("""
        <style>
        /* ==================== 폼 요소 스타일 ==================== */
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

        /* ==================== 모달 스타일 커스터마이징 ==================== */
        /* 모달 컨테이너 */
        [data-testid="stModal"] {
            /* 배경 오버레이 스타일 */
            background-color: rgba(0, 0, 0, 0.5) !important;
        }

        /* 모달 다이얼로그 박스 */
        [data-testid="stModal"] > div[role="dialog"] {
            /* 크기 조정 */
            max-width: 800px !important;
            width: 90% !important;
            max-height: 85vh !important;

            /* 위치 조정 - 화면 상단에서 약간 아래로 */
            margin-top: 5vh !important;

            /* 모서리 */
            border-radius: 8px !important;

            /* 그림자 강화 */
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;

            /* 스크롤 */
            overflow-y: auto !important;
        }

        /* 모달 헤더 스타일 */
        [data-testid="stModal"] > div[role="dialog"] > div:first-child {
            /* 헤더 패딩 */
            padding: 1rem 1.5rem !important;

            /* 하단 경계선 */
            border-bottom: 1px solid rgba(128, 128, 128, 0.2) !important;

            /* Flexbox 정렬 */
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
        }

        /* 모달 제목 스타일 */
        [data-testid="stModal"] h3 {
            font-size: 1.25rem !important;
            font-weight: 600 !important;
            margin: 0 !important;
        }

        /* 모달 본문 스타일 */
        [data-testid="stModal"] > div[role="dialog"] > div:nth-child(2) {
            padding: 1.5rem !important;
        }

        /* 모달 닫기 버튼 스타일 */
        [data-testid="stModal"] button[aria-label="Close"] {
            border-radius: 4px !important;
            padding: 0.25rem 0.5rem !important;
        }

        /* 반응형: 작은 화면에서 모달 조정 */
        @media (max-width: 768px) {
            [data-testid="stModal"] > div[role="dialog"] {
                width: 95% !important;
                max-height: 90vh !important;
                margin-top: 2vh !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)
