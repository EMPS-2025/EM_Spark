# presenters/chart_generator.py
"""Generates interactive Plotly charts with multi-market support."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional

# Professional Color Palette
COLORS = {
    'DAM': '#0056D2',    # EM Blue
    'GDAM': '#16a34a',   # Success Green
    'RTM': '#d97706',    # Amber
    'VOL': 'rgba(148, 163, 184, 0.4)', # Slate 400 with opacity
    'BID_BUY': '#60a5fa', # Light Blue
    'BID_SELL': '#f87171' # Light Red
}

def generate_market_chart(
    market_name: str,
    time_label: str,
    rows: List[Dict[str, Any]],
    is_quarterly: bool
):
    if not rows: return None
    
    # Data Prep
    rows = sorted(rows, key=lambda x: (x['delivery_date'], x.get('block_index', x.get('slot_index', 0))))
    if is_quarterly:
        x_vals = [f"{r['delivery_date']} S-{r['slot_index']}" for r in rows]
        volumes = [r['mcv_mw'] * 0.25 for r in rows]
    else:
        x_vals = [f"{r['delivery_date']} H-{r.get('block_index', 0)}" for r in rows]
        volumes = [r['mcv_mw'] / 4.0 for r in rows]
        
    prices = [r['price_avg'] / 1000.0 for r in rows]
    buy_bids = [r['purchase_bid_mw'] for r in rows]
    sell_bids = [r['sell_bid_mw'] for r in rows]

    # Create Dual-Axis Chart
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Volume (Bar - Background)
    fig.add_trace(
        go.Bar(x=x_vals, y=volumes, name="Volume", marker_color=COLORS['VOL'], showlegend=True), 
        secondary_y=False
    )

    # 2. Bids (Lines - Dotted)
    fig.add_trace(go.Scatter(x=x_vals, y=buy_bids, name="Buy Bids", line=dict(color=COLORS['BID_BUY'], dash='dot', width=1), visible='legendonly'), secondary_y=True)
    fig.add_trace(go.Scatter(x=x_vals, y=sell_bids, name="Sell Bids", line=dict(color=COLORS['BID_SELL'], dash='dot', width=1), visible='legendonly'), secondary_y=True)

    # 3. Price (Line - Primary Focus)
    fig.add_trace(
        go.Scatter(x=x_vals, y=prices, name="Price", line=dict(color=COLORS.get(market_name, '#2563eb'), width=3)), 
        secondary_y=True
    )

    # Layout - Optimized for Chainlit 2.0 Wide Mode
    fig.update_layout(
        title=dict(
            text=f"<b>{market_name} Price & Volume</b><br><span style='font-size: 12px; color: #64748b;'>{time_label}</span>",
            x=0, xanchor='left'
        ),
        template="plotly_white",
        hovermode="x unified",
        # Note: Height/Width are now handled by app.py's update_layout
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        font=dict(family="Inter, sans-serif", size=11),
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent
        paper_bgcolor="rgba(0,0,0,0)"  # Transparent
    )

    fig.update_xaxes(showgrid=False, showline=True, linecolor='#e2e8f0')
    fig.update_yaxes(title="Vol (MWh)", secondary_y=False, showgrid=False, showline=False, showticklabels=False) 
    fig.update_yaxes(title="Price (₹/kWh)", secondary_y=True, showgrid=True, gridcolor='#f1f5f9')
    
    return fig


def generate_multi_market_chart(
    market_data: Dict[str, List[Dict[str, Any]]],
    time_label: str,
    is_quarterly: bool
) -> Optional[go.Figure]:
    if not market_data: return None

    fig = go.Figure()
    
    for market_name, rows in market_data.items():
        if not rows: continue
        rows = sorted(rows, key=lambda x: (x['delivery_date'], x.get('block_index', x.get('slot_index', 0))))
        
        if is_quarterly:
            x_vals = [f"{r['delivery_date']} S-{r['slot_index']}" for r in rows]
        else:
            x_vals = [f"{r['delivery_date']} H-{r.get('block_index', 0)}" for r in rows]
        prices = [r['price_avg'] / 1000.0 for r in rows]
        
        fig.add_trace(go.Scatter(
            x=x_vals, y=prices, name=market_name,
            line=dict(color=COLORS.get(market_name, '#666'), width=2.5)
        ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>Market Comparison</b><br><span style='font-size: 12px; color: #64748b;'>{time_label}</span>",
            x=0
        ),
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        font=dict(family="Inter, sans-serif", size=11),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='#f8fafc', showline=True, linecolor='#e2e8f0')
    fig.update_yaxes(title="Price (₹/kWh)", showgrid=True, gridcolor='#f1f5f9')
    
    return fig


def generate_comparison_chart(current_data, previous_data, year):
    markets = ['DAM', 'GDAM', 'RTM']
    
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Volume (GWh)", "Price (₹/kWh)"))
    
    has_data = False
    for market in markets:
        curr = current_data.get(market, {})
        prev = previous_data.get(market, {})
        
        if curr.get('total_volume_gwh', 0) > 0:
            has_data = True
            # Clean Bar Chart: Grouped
            fig.add_trace(go.Bar(name=f"{market} '{year}", x=[market], y=[curr.get('total_volume_gwh', 0)], marker_color=COLORS.get(market)), row=1, col=1)
            fig.add_trace(go.Bar(name=f"{market} '{year-1}", x=[market], y=[prev.get('total_volume_gwh', 0)], marker_color=COLORS.get(market), opacity=0.3, showlegend=False), row=1, col=1)
            
            fig.add_trace(go.Bar(name=f"{market}", x=[market], y=[curr.get('twap', 0)], marker_color=COLORS.get(market), showlegend=False), row=1, col=2)
            fig.add_trace(go.Bar(name=f"{market} Prev", x=[market], y=[prev.get('twap', 0)], marker_color=COLORS.get(market), opacity=0.3, showlegend=False), row=1, col=2)
            
    if not has_data: return None

    fig.update_layout(
        title=dict(text=f"<b>Year-over-Year Performance</b>", x=0),
        template="plotly_white",
        barmode='group',
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig
