"""
BTS 차트 컴포넌트

Plotly 기반 차트 시각화
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime

from core.models import OHLCV, TradeResponse


def render_candlestick_chart(
    ohlcv_data: List[OHLCV],
    title: str = "가격 차트",
    height: int = 500
) -> go.Figure:
    """
    캔들스틱 차트 렌더링

    Args:
        ohlcv_data: OHLCV 데이터
        title: 차트 제목
        height: 차트 높이

    Returns:
        go.Figure: Plotly Figure
    """
    if not ohlcv_data:
        # 빈 차트
        fig = go.Figure()
        fig.add_annotation(
            text="데이터가 없습니다",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False
        )
        return fig

    df = pd.DataFrame([
        {
            "timestamp": o.timestamp,
            "open": float(o.open),
            "high": float(o.high),
            "low": float(o.low),
            "close": float(o.close),
            "volume": float(o.volume)
        }
        for o in ohlcv_data
    ])

    # 캔들스틱 차트
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(title, "Volume")
    )

    # 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="",
            increasing_line_color="#EF5350",  # 양봉 (상승) - 밝은 빨강
            increasing_fillcolor="#EF5350",
            decreasing_line_color="#42A5F5",  # 음봉 (하락) - 밝은 파랑
            decreasing_fillcolor="#42A5F5",
            line=dict(width=1)  # 심지(wick) 두께 1px
        ),
        row=1,
        col=1
    )

    # 거래량
    colors = ["#42A5F5" if df.iloc[i]["close"] < df.iloc[i]["open"] else "#EF5350"
              for i in range(len(df))]

    fig.add_trace(
        go.Bar(
            x=df["timestamp"],
            y=df["volume"],
            name="Volume",
            marker_color=colors
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        height=height,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        showlegend=False
    )

    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Price (KRW)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


def render_indicator_chart(
    ohlcv_data: List[OHLCV],
    indicators: Dict,
    title: str = "지표 차트",
    height: int = 400
) -> go.Figure:
    """
    기술적 지표 차트 렌더링

    Args:
        ohlcv_data: OHLCV 데이터
        indicators: 지표 데이터
        title: 차트 제목
        height: 차트 높이

    Returns:
        go.Figure: Plotly Figure
    """
    if not ohlcv_data or not indicators:
        fig = go.Figure()
        fig.add_annotation(
            text="데이터가 없습니다",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False
        )
        return fig

    df = pd.DataFrame([
        {
            "timestamp": o.timestamp,
            "close": float(o.close)
        }
        for o in ohlcv_data
    ])

    fig = go.Figure()

    # 종가
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["close"],
            name="종가",
            line=dict(color="blue", width=1)
        )
    )

    # RSI 지표
    if "rsi" in indicators:
        rsi = indicators["rsi"]
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=rsi,
                name="RSI",
                line=dict(color="orange", width=2),
                yaxis="y2"
            )
        )

        # RSI 기준선
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="red",
            annotation_text="과매수(70)",
            yref="y2"
        )
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color="green",
            annotation_text="과매도(30)",
            yref="y2"
        )

    # 이동평균선
    if "ma_short" in indicators and "ma_long" in indicators:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=indicators["ma_short"],
                name="단기 MA",
                line=dict(color="green", width=1, dash="dot")
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=indicators["ma_long"],
                name="장기 MA",
                line=dict(color="red", width=1, dash="dot")
            )
        )

    # 볼린저 밴드
    if all(k in indicators for k in ["bb_upper", "bb_middle", "bb_lower"]):
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=indicators["bb_upper"],
                name="볼린저 상단",
                line=dict(color="gray", width=1, dash="dash")
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=indicators["bb_middle"],
                name="볼린저 중간",
                line=dict(color="gray", width=1)
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=indicators["bb_lower"],
                name="볼린저 하단",
                line=dict(color="gray", width=1, dash="dash"),
                fill="tonexty"
            )
        )

    fig.update_layout(
        title=title,
        height=height,
        hovermode="x unified",
        xaxis=dict(title="시간"),
        yaxis=dict(title="가격 (KRW)", side="left"),
        yaxis2=dict(
            title="RSI",
            overlaying="y",
            side="right",
            range=[0, 100]
        ) if "rsi" in indicators else None
    )

    return fig


def render_profit_chart(
    trades: List[TradeResponse],
    title: str = "수익률 차트",
    height: int = 400
) -> go.Figure:
    """
    수익률 차트 렌더링

    Args:
        trades: 거래 내역
        title: 차트 제목
        height: 차트 높이

    Returns:
        go.Figure: Plotly Figure
    """
    if not trades:
        fig = go.Figure()
        fig.add_annotation(
            text="거래 내역이 없습니다",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False
        )
        return fig

    # 누적 수익 계산
    cumulative_profit = Decimal("0")
    data = []

    for trade in trades:
        # 간단한 수익 계산 (실제로는 매수/매도 매칭 필요)
        if trade.side.value == "sell":
            profit = trade.total_amount - trade.fee
        else:
            profit = -(trade.total_amount + trade.fee)

        cumulative_profit += profit

        data.append({
            "timestamp": trade.created_at,
            "profit": float(profit),
            "cumulative_profit": float(cumulative_profit)
        })

    df = pd.DataFrame(data)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("거래별 손익", "누적 손익")
    )

    # 거래별 손익
    colors = ["green" if p > 0 else "red" for p in df["profit"]]
    fig.add_trace(
        go.Bar(
            x=df["timestamp"],
            y=df["profit"],
            name="거래 손익",
            marker_color=colors
        ),
        row=1,
        col=1
    )

    # 누적 손익
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["cumulative_profit"],
            name="누적 손익",
            line=dict(color="blue", width=2),
            fill="tozeroy"
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        title=title,
        height=height,
        hovermode="x unified",
        showlegend=False
    )

    fig.update_xaxes(title_text="시간", row=2, col=1)
    fig.update_yaxes(title_text="손익 (KRW)", row=1, col=1)
    fig.update_yaxes(title_text="누적 손익 (KRW)", row=2, col=1)

    return fig


def render_portfolio_pie_chart(
    holdings: List[Dict],
    title: str = "포트폴리오 구성",
    height: int = 400
) -> go.Figure:
    """
    포트폴리오 파이 차트 렌더링

    Args:
        holdings: 보유 자산 목록 [{"symbol": str, "value": Decimal}]
        title: 차트 제목
        height: 차트 높이

    Returns:
        go.Figure: Plotly Figure
    """
    if not holdings:
        fig = go.Figure()
        fig.add_annotation(
            text="보유 자산이 없습니다",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False
        )
        return fig

    labels = [h["symbol"] for h in holdings]
    values = [float(h["value"]) for h in holdings]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                textinfo="label+percent"
            )
        ]
    )

    fig.update_layout(
        title=title,
        height=height,
        showlegend=True
    )

    return fig


def render_heatmap(
    data: pd.DataFrame,
    title: str = "히트맵",
    height: int = 400
) -> go.Figure:
    """
    히트맵 렌더링

    Args:
        data: 히트맵 데이터 (DataFrame)
        title: 차트 제목
        height: 차트 높이

    Returns:
        go.Figure: Plotly Figure
    """
    if data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="데이터가 없습니다",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False
        )
        return fig

    fig = go.Figure(
        data=go.Heatmap(
            z=data.values,
            x=data.columns,
            y=data.index,
            colorscale="RdYlGn",
            text=data.values,
            texttemplate="%{text:.2f}",
            textfont={"size": 10}
        )
    )

    fig.update_layout(
        title=title,
        height=height,
        xaxis=dict(title=""),
        yaxis=dict(title="")
    )

    return fig
