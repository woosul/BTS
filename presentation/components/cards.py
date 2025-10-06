"""
BTS 카드 컴포넌트

카드형 UI 컴포넌트
"""
import streamlit as st
from decimal import Decimal
from typing import Optional


def render_metric_card(label: str, value: str, delta: Optional[str] = None, help_text: Optional[str] = None) -> None:
    """
    메트릭 카드 렌더링

    Args:
        label: 라벨
        value: 값
        delta: 변화량 (선택)
        help_text: 도움말 (선택)
    """
    card_style = """
    <div style="
        background: linear-gradient(135deg, #000000 0%, #181818 100%);
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #404040;
        height: 100%;
    ">
        <div style="
            font-size: 0.75rem;
            color: #9ca3af;
            margin-bottom: 8px;
        ">{label}</div>
        <div style="
            font-size: 1.5rem;
            font-weight: 600;
            color: #FAFAFA;
            margin-bottom: 4px;
        ">{value}</div>
        {delta_html}
    </div>
    """

    delta_html = ""
    if delta:
        delta_html = f'<div style="font-size: 0.85rem; color: #54A0FD;">{delta}</div>'

    st.markdown(
        card_style.format(label=label, value=value, delta_html=delta_html),
        unsafe_allow_html=True
    )


def render_wallet_card(title: str, balance: Decimal, total_value: Decimal, wallet_type: str) -> None:
    """
    지갑 정보 카드 렌더링

    Args:
        title: 카드 제목
        balance: 원화 잔고
        total_value: 총 자산
        wallet_type: 지갑 유형
    """
    # 수익 계산
    initial_balance = Decimal("10000000")
    profit = total_value - initial_balance
    profit_rate = (profit / initial_balance) * 100 if initial_balance > 0 else Decimal("0")

    profit_color = "#10b981" if profit >= 0 else "#ef4444"

    card_html = f"""<div style="background: linear-gradient(135deg, #000000 0%, #181818 100%); border-radius: 12px; padding: 20px; border: 1px solid #404040; margin-bottom: 12px;">
    <div style="font-size: 1.1rem; font-weight: 600; color: #FAFAFA; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #404040;">{title}</div>
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
        <div>
            <div style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 4px;">원화 잔고</div>
            <div style="font-size: 1.3rem; font-weight: 600; color: #FAFAFA;">₩{balance:,.0f}</div>
        </div>
        <div>
            <div style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 4px;">총 자산</div>
            <div style="font-size: 1.3rem; font-weight: 600; color: #FAFAFA;">₩{total_value:,.0f}</div>
        </div>
        <div>
            <div style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 4px;">수익률</div>
            <div style="font-size: 1.3rem; font-weight: 600; color: {profit_color};">{profit_rate:+.2f}%</div>
            <div style="font-size: 0.75rem; color: {profit_color};">₩{profit:+,.0f}</div>
        </div>
        <div>
            <div style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 4px;">지갑 유형</div>
            <div style="font-size: 1.3rem; font-weight: 600; color: #FAFAFA;">{wallet_type}</div>
        </div>
    </div>
</div>"""

    st.markdown(card_html, unsafe_allow_html=True)
