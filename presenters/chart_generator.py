# presenters/chart_generator.py
"""Generates interactive Plotly charts with multi-market support."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional

def generate_market_chart(
    market_name: str,
    time_label: str,
    rows: List[Dict[str, Any]],
    is_quarterly: bool
):
    """
    Single market chart (backward compatible).
    """
    if not rows:
        return None

    rows = sorted(rows, key=lambda x: (x['delivery_date'], x.get('block_index', x.get('slot_index', 0))))

    if is_quarterly:
        x_vals = [f"{r['delivery_date']} S-{r['slot_index']}" for r in rows]
    else:
        x_vals = [f"{r['delivery_date']} H-{r.get('block_index', 0)}" for r in rows]

    prices = [r['price_avg'] / 1000.0 for r in rows]
    buy_bids = [r['purchase_bid_mw'] for r in rows]
    sell_bids = [r['sell_bid_mw'] for r in rows]
    
    if is_quarterly:
        volumes = [r['mcv_mw'] * 0.25 for r in rows]
    else:
        volumes = [r['mcv_mw'] / 4.0 for r in rows]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Volume bars (light grey, low opacity)
    fig.add_trace(
        go.Bar(
            x=x_vals, 
            y=volumes, 
            name="Vol (MWh)", 
            marker_color='rgba(189, 195, 199, 0.5)',
            showlegend=True
        ),
        secondary_y=False
    )

    # Buy/Sell bids (hidden by default)
    fig.add_trace(
        go.Scatter(
            x=x_vals, 
            y=buy_bids, 
            name="Buy Bid", 
            line=dict(color='#3b82f6', dash='dot', width=1),
            visible='legendonly'
        ),
        secondary_y=True
    )

    fig.add_trace(
        go.Scatter(
            x=x_vals, 
            y=sell_bids, 
            name="Sell Bid", 
            line=dict(color='#ef4444', dash='dot', width=1),
            visible='legendonly'
        ),
        secondary_y=True
    )

    # Price line (main focus)
    fig.add_trace(
        go.Scatter(
            x=x_vals, 
            y=prices, 
            name=f"{market_name} Price", 
            line=dict(color='#10b981', width=2.5)
        ),
        secondary_y=True
    )

    fig.update_layout(
        title=dict(
            text=f"{market_name} Price & Volume Analysis",
            font=dict(size=18, family='Inter, sans-serif')
        ),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,  # Move legend ABOVE the chart
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#e5e7eb",
            borderwidth=1,
            font=dict(size=12)
        ),
        margin=dict(l=80, r=80, t=100, b=80),  # Increased margins
        height=550,  # Increased from 500
        width=None,  # ✅ Let it be responsive
        autosize=True,  # ✅ Enable autosizing
        font=dict(family="Inter, sans-serif", size=13)
    )


    fig.update_yaxes(
        title_text="Volume (MWh)", 
        secondary_y=False, 
        showgrid=False,
        title_font=dict(size=14, color='#64748b'),
        tickfont=dict(size=12)
    )
    fig.update_yaxes(
        title_text="Price (₹/kWh)", 
        secondary_y=True, 
        showgrid=True, 
        gridcolor='#f3f4f6',
        title_font=dict(size=14, color='#10b981'),
        tickfont=dict(size=12)
    )
    fig.update_xaxes(
        showgrid=False, 
        showticklabels=True, 
        tickangle=-45,
        title_text="Time Period",
        title_font=dict(size=14),
        tickfont=dict(size=11)
    )
    
    return fig


def generate_multi_market_chart(
    market_data: Dict[str, List[Dict[str, Any]]],
    time_label: str,
    is_quarterly: bool
) -> Optional[go.Figure]:
    """
    Generate chart with multiple markets overlaid (DAM, GDAM, RTM).
    
    Args:
        market_data: Dict with keys 'DAM', 'GDAM', 'RTM' containing row data
        time_label: Time range description
        is_quarterly: Whether data is 15-min slots or hourly
    
    Returns:
        Plotly figure with overlaid market prices
    """
    if not market_data or all(len(rows) == 0 for rows in market_data.values()):
        return None

    fig = go.Figure()
    
    # Color scheme for markets
    colors = {
        'DAM': '#0056D2',   # Blue
        'GDAM': '#10b981',  # Green
        'RTM': '#f59e0b'    # Orange/Yellow
    }
    
    # Process each market
    for market_name, rows in market_data.items():
        if not rows:
            continue
            
        rows = sorted(rows, key=lambda x: (x['delivery_date'], x.get('block_index', x.get('slot_index', 0))))
        
        # Build x-axis labels
        if is_quarterly:
            x_vals = [f"{r['delivery_date']} S-{r['slot_index']}" for r in rows]
        else:
            x_vals = [f"{r['delivery_date']} H-{r.get('block_index', 0)}" for r in rows]
        
        # Extract prices (convert Rs/MWh to Rs/kWh)
        prices = [r['price_avg'] / 1000.0 for r in rows]
        
        # Add price line
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=prices,
                name=market_name,
                line=dict(color=colors.get(market_name, '#666'), width=2.5),
                mode='lines+markers',
                marker=dict(size=4),
                hovertemplate=f'<b>{market_name}</b><br>Price: ₹%{{y:.3f}}/kWh<extra></extra>'
            )
        )
    
    # Layout configuration
    fig.update_layout(
        title=dict(
            text=f"Multi-Market Price Comparison • {time_label}",
            font=dict(size=18, family='Inter, sans-serif')
        ),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,  # Move legend above
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#e5e7eb",
            borderwidth=1,
            font=dict(size=13)
        ),
        margin=dict(l=80, r=80, t=100, b=100),  # Increased margins
        height=600,  # Increased from 550
        width=None,  # Responsive
        autosize=True,
        font=dict(family="Inter, sans-serif", size=13),
        xaxis=dict(
            showgrid=True,
            gridcolor='#f3f4f6',
            tickangle=-45,
            title="Date & Time Block",
            title_font=dict(size=14),
            tickfont=dict(size=11)
        ),
        yaxis=dict(
            title="Price (₹/kWh)",
            showgrid=True,
            gridcolor='#e5e7eb',
            zeroline=True,
            zerolinecolor='#d1d5db',
            title_font=dict(size=14, color='#0056D2'),
            tickfont=dict(size=12)
        )
    )
    
    return fig


def generate_comparison_chart(
    current_data: Dict[str, Dict],
    previous_data: Dict[str, Dict],
    year: int
) -> Optional[go.Figure]:
    """
    Generate side-by-side comparison chart for current vs previous year.
    
    Args:
        current_data: {'DAM': {...}, 'GDAM': {...}, 'RTM': {...}}
        previous_data: Same structure for previous year
    
    Returns:
        Grouped bar chart comparing volumes and prices
    """
    markets = ['DAM', 'GDAM', 'RTM']
    colors = {
        'DAM': '#0056D2',
        'GDAM': '#10b981',
        'RTM': '#f59e0b'
    }
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Volume Comparison (GWh)", "Price Comparison (₹/kWh)"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Volume comparison
    for market in markets:
        curr = current_data.get(market, {})
        prev = previous_data.get(market, {})
        
        fig.add_trace(
            go.Bar(
                name=f"{market} Current",
                x=[market],
                y=[curr.get('total_volume_gwh', 0)],
                marker_color=colors[market],
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                name=f"{market} Previous",
                x=[market],
                y=[prev.get('total_volume_gwh', 0)],
                marker_color=colors[market],
                opacity=0.5,
                showlegend=True
            ),
            row=1, col=1
        )
    
    # Price comparison
    for market in markets:
        curr = current_data.get(market, {})
        prev = previous_data.get(market, {})
        
        fig.add_trace(
            go.Bar(
                name=f"{market} Current",
                x=[market],
                y=[curr.get('twap', 0)],
                marker_color=colors[market],
                showlegend=False
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(
                name=f"{market} Previous",
                x=[market],
                y=[prev.get('twap', 0)],
                marker_color=colors[market],
                opacity=0.5,
                showlegend=False
            ),
            row=1, col=2
        )
    
    fig.update_layout(
        barmode='group',
        height=550,  # Increased from 500
        width=None,  # Responsive
        autosize=True,
        showlegend=True,
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=13),
        margin=dict(l=80, r=80, t=100, b=80),
        title=dict(
            #text=f"Year-over-Year Market Analysis ({year} vs {year-1})",
            font=dict(size=18)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=13)
        ),
        xaxis=dict(
            title="Market",
            title_font=dict(size=14),
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            title="Value",
            title_font=dict(size=14),
            tickfont=dict(size=12),
            showgrid=True,
            gridcolor='#f3f4f6'
        )
    )
    
    return fig