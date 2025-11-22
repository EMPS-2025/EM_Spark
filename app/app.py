# app/app.py
import os
import sys
import traceback
from datetime import date
from dataclasses import replace
from typing import Dict, List, Any, Optional
import chainlit as cl
from openai import OpenAI

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import Config
from core.database import DatabaseManager
from parsers.bulletproof_parser import BulletproofParser
from presenters.enhanced_response_builder import EnhancedResponseBuilder
from presenters.chart_generator import (
    generate_market_chart,
    generate_multi_market_chart,
    generate_comparison_chart
)
from presenters.ai_insights import generate_ai_insights
from utils.formatters import label_hour_ranges, label_slot_ranges

# Initialize
config = Config()
db = DatabaseManager(config)
parser = BulletproofParser(config)
response_builder = EnhancedResponseBuilder()


@cl.on_chat_start
async def start_session():
    welcome = """
# 👋 EM-SPARK Intelligence Platform

**Ask about energy markets:**
- *"DAM rate today"*
- *"Compare DAM and GDAM for last week"*
- *"RTM prices for 14 Nov 2025"*
- *"Show derivative market for today"*

Ready to analyze! 📊
    """
    await cl.Message(author=config.ASSISTANT_NAME, content=welcome).send()

def describe_time_selection(spec, total_specs=1) -> Dict[str, Any]:
    """Generate human-readable time labels."""
    if spec.granularity == "quarter" and spec.slots:
        slots = sorted(set(spec.slots))
        time_label, _, count = label_slot_ranges(slots)
        duration_hours = count * 0.25
        pretty_label = f"{time_label} (All India)"
    else:
        hours = sorted(set(spec.hours or list(range(1, 25))))
        time_label, _, count = label_hour_ranges(hours)
        
        if count >= 24:
            pretty_label = "00:00–24:00 hrs"
        else:
            pretty_label = f"{time_label} hrs"
        duration_hours = float(count)
        
    if total_specs > 1:
        pretty_label += " [Multi-Period]"

    return {'time_label': pretty_label, 'duration_hours': round(duration_hours, 2)}

def calculate_segments(rows: List[Dict]) -> Dict[str, Any]:
    """Calculate Peak, Off-Peak, and Solar segment metrics."""
    solar_blocks = set(range(9, 19))  # 08:00 - 18:00
    peak_blocks = set(range(19, 24))  # 18:00 - 23:00
    
    segments = {
        'solar': {'prices': [], 'volumes': []},
        'peak': {'prices': [], 'volumes': []},
        'off_peak': {'prices': [], 'volumes': []}
    }
    
    for row in rows:
        if 'block_index' in row:
            idx = row['block_index']
        elif 'slot_index' in row:
            idx = (row['slot_index'] - 1) // 4 + 1
        else:
            continue
            
        price = row['price_avg'] / 1000.0
        vol = row.get('mcv_mw', 0)
        
        if row.get('duration_min') == 15:
            vol_mwh = vol * 0.25
        else:
            vol_mwh = vol / 4.0
        
        if idx in solar_blocks:
            segments['solar']['prices'].append(price)
            segments['solar']['volumes'].append(vol_mwh)
        elif idx in peak_blocks:
            segments['peak']['prices'].append(price)
            segments['peak']['volumes'].append(vol_mwh)
        else:
            segments['off_peak']['prices'].append(price)
            segments['off_peak']['volumes'].append(vol_mwh)
            
    results = {}
    for key, data in segments.items():
        if data['prices']:
            twap = sum(data['prices']) / len(data['prices'])
            vol = sum(data['volumes']) / 1000.0
            results[key] = {'twap': twap, 'volume_gwh': vol, 'count': len(data['prices'])}
        else:
            results[key] = {'count': 0}
    return results

def compute_aggregated_metrics(rows: List[Dict], granularity: str) -> Dict[str, Any]:
    """Compute metrics for aggregated rows."""
    if not rows:
        return {
            'purchase_bid_total_mw': 0.0,
            'sell_bid_total_mw': 0.0,
            'twap': 0.0,
            'min_price': 0.0,
            'max_price': 0.0,
            'total_volume_gwh': 0.0,
            'rows': []
        }
    
    prices = []
    mwh_volumes = []
    purchase_bids = []
    sell_bids = []
    
    for row in rows:
        prices.append(row['price_avg'])
        purchase_bids.append(row['purchase_bid_mw'])
        sell_bids.append(row['sell_bid_mw'])
        
        if granularity == 'quarter':
            mwh_volumes.append(row['mcv_mw'] * 0.25)
        else:
            mwh_volumes.append(row['mcv_mw'] / 4.0)

    twap_mwh = sum(prices) / len(prices) if prices else 0.0
    total_vol_mwh = sum(mwh_volumes)
    avg_buy_mw = sum(purchase_bids) / len(purchase_bids) if purchase_bids else 0.0
    avg_sell_mw = sum(sell_bids) / len(sell_bids) if sell_bids else 0.0
    
    return {
        'purchase_bid_total_mw': avg_buy_mw,
        'sell_bid_total_mw': avg_sell_mw,
        'twap': twap_mwh / 1000.0,
        'min_price': min(prices) / 1000.0 if prices else 0.0,
        'max_price': max(prices) / 1000.0 if prices else 0.0,
        'total_volume_gwh': total_vol_mwh / 1000.0,
        'rows': rows
    }

async def fetch_aggregated_market_data(specs: List[Any], market_override: str = None) -> Dict[str, Any]:
    """Fetch and aggregate data for multiple query specs."""
    all_rows = []
    granularity = "hour"
    
    for spec in specs:
        target_market = market_override if market_override else spec.market
        target_spec = replace(spec, market=target_market)
        granularity = target_spec.granularity
        
        if target_spec.granularity == 'quarter':
            rows = db.fetch_quarter(target_market, target_spec.start_date, target_spec.end_date, None, None, exclusion=target_spec.exclusion)
        else:
            rows = db.fetch_hourly(target_market, target_spec.start_date, target_spec.end_date, None, None, exclusion=target_spec.exclusion)
            
        filtered = []
        if target_spec.granularity == "quarter" or (target_spec.slots and len(target_spec.slots) > 0):
            allowed_slots = set(target_spec.slots or range(1, 97))
            for row in rows:
                if row['slot_index'] in allowed_slots:
                    filtered.append(row)
        else:
            allowed_hours = set(target_spec.hours or range(1, 25))
            for row in rows:
                if row['block_index'] in allowed_hours:
                    filtered.append(row)
                    
        all_rows.extend(filtered)
        
    return compute_aggregated_metrics(all_rows, granularity)


@cl.on_message
async def handle_message(msg: cl.Message):
    progress_msg = cl.Message(content="🤖 Analyzing markets...")
    await progress_msg.send()
    
    try:
        user_query = msg.content.strip()
        
        # Check if user clicked "Generate Charts" button
        if user_query.lower() in ["generate charts", "show charts", "display charts"]:
            await progress_msg.update(content="📊 Generating charts...")
            # Retrieve stored chart data from session
            chart_elements = cl.user_session.get("pending_charts", [])
            if chart_elements:
                await cl.Message(
                    author=config.ASSISTANT_NAME,
                    content="## 📊 Market Charts\n\nInteractive visualizations generated below:",
                    elements=chart_elements
                ).send()
                cl.user_session.set("pending_charts", [])
            else:
                await cl.Message(author=config.ASSISTANT_NAME, content="⚠️ No charts available. Please query market data first.").send()
            await progress_msg.remove()
            return
        
        specs = parser.parse(user_query)
        
        if not specs:
            await progress_msg.remove()
            await cl.Message(author=config.ASSISTANT_NAME, content="⚠️ Could not parse query. Try: 'DAM today' or 'GDAM yesterday'").send()
            return

        primary_market = specs[0].market
        selection_details = describe_time_selection(specs[0], total_specs=len(specs))

        # ✅ NEW: Build exclusion label
        exclusion_label = ""
        if specs[0].exclusion:
            excluded_days = specs[0].exclusion.get_excluded_day_names()
            exclusion_label = f" (excluding {', '.join(excluded_days)})"
        
        # Fetch data for ALL markets
        all_market_data = {}
        all_market_prev_year = {}
        all_market_rows = {}  # Store rows for multi-market chart
        
        for m in ["DAM", "GDAM", "RTM"]:
            # Current year
            all_market_data[m] = await fetch_aggregated_market_data(specs, market_override=m)
            all_market_rows[m] = all_market_data[m].get('rows', [])
            
            # Previous year
            prev_specs = []
            for s in specs:
                try:
                    prev_s = s.start_date.replace(year=s.start_date.year - 1)
                    prev_e = s.end_date.replace(year=s.end_date.year - 1)
                    prev_specs.append(replace(s, start_date=prev_s, end_date=prev_e))
                except ValueError:
                    pass
            
            if prev_specs:
                all_market_prev_year[m] = await fetch_aggregated_market_data(prev_specs, market_override=m)
            else:
                all_market_prev_year[m] = {}

        primary_data = all_market_data.get(primary_market, {})

        # 🌿 CALCULATE RENEWABLE MIX
        vol_dam = all_market_data.get('DAM', {}).get('total_volume_gwh', 0)
        vol_gdam = all_market_data.get('GDAM', {}).get('total_volume_gwh', 0)
        vol_rtm = all_market_data.get('RTM', {}).get('total_volume_gwh', 0)
        # 1. Renewable Mix (GDAM / Spot)
        total_market_vol = vol_dam + vol_gdam + vol_rtm
        
        renewable_mix_pct = 0.0
        if total_market_vol > 0:
            renewable_mix_pct = (vol_gdam / total_market_vol) * 100

        # Calculate segments
        segments = calculate_segments(primary_data.get('rows', []))
        
        # Fetch derivatives
        deriv_data, deriv_actual_date = db.fetch_derivative_data(specs[0].start_date)
        
        # Generate AI Insights
        comparison_data = {
            'current': all_market_data,
            'previous': all_market_prev_year
        }
        
        insights = generate_ai_insights(
            api_key=config.OPENAI_API_KEY,
            market_data=all_market_data,
            derivative_data=deriv_data,
            comparison_data=comparison_data,
            model=config.LLM_MODEL
        )
        
        # Generate Charts
        chart_elements = []
        
        # 1. Multi-market comparison chart (if multiple markets have data)
        active_markets = {k: v for k, v in all_market_rows.items() if v}
        if len(active_markets) > 1:
            multi_fig = generate_multi_market_chart(
                active_markets,
                selection_details['time_label'],
                specs[0].granularity == 'quarter'
            )
            if multi_fig:
                chart_elements.append(
                    cl.Plotly(name="Multi-Market Comparison", figure=multi_fig, display="inline")
                )
        
        # 2. Primary market detailed chart
        if primary_data.get('rows'):
            single_fig = generate_market_chart(
                primary_market,
                selection_details['time_label'],
                primary_data['rows'],
                specs[0].granularity == 'quarter'
            )
            if single_fig:
                single_fig.update_layout(
                    width=None,  # Let it be responsive
                    autosize=True,
                    margin=dict(l=60, r=60, t=80, b=60)
                )
                chart_elements.append(
                    cl.Plotly(
                        name=f"{primary_market}_chart", 
                        figure=single_fig, 
                        display="inline",
                        size="large"
                    )
                )
        
        # 3. YoY comparison chart
        if all_market_prev_year:
            yoy_fig = generate_comparison_chart(all_market_data, all_market_prev_year, specs[0].start_date.year)
            if yoy_fig:
                chart_elements.append(
                    cl.Plotly(name="Year-over-Year Comparison", figure=yoy_fig, display="inline")
                )
        
        # Build date label for comparison section
        if len(specs) > 1:
            date_label = f"{len(specs)} Periods"
            date_range_label = f"{specs[0].start_date} to {specs[-1].end_date}"
        else:
            if specs[0].start_date == specs[0].end_date:
                date_label = f"{specs[0].start_date}"
                date_range_label = specs[0].start_date.strftime("%d %b %Y")
            else:
                date_label = f"{specs[0].start_date} to {specs[0].end_date}"
                date_range_label = f"{specs[0].start_date.strftime('%d %b')} to {specs[0].end_date.strftime('%d %b %Y')}"

        # Build response sections
        sections = [
            response_builder.build_overview_header(
                f"Spot Market ({primary_market})", 
                date_label + exclusion_label, 
                selection_details,
                user_query
            ),
            response_builder.build_snapshot_card(
                primary_market,
                date_label,
                selection_details['time_label'],
                primary_data['twap'],
                primary_data['min_price'],
                primary_data['max_price'],
                primary_data['total_volume_gwh'],
                renewable_mix_pct,
                total_market_vol
            ),
            response_builder.build_derivative_section(
                deriv_data,
                actual_trading_date=deriv_actual_date,
                requested_date=specs[0].start_date
            ),
            response_builder.build_market_comparison_section(
                specs[0].start_date.year,
                all_market_data,
                all_market_prev_year,
                current_date_range=date_range_label,
                current_time_window=selection_details['time_label']
            ),
            response_builder.build_ai_insights_section(insights)
        ]
        
        response_text = response_builder.compose_dashboard(sections)

        # UPDATED FOR CHAINLIT 2.0: 'value' removed, 'description' -> 'tooltip'
        actions = [
            cl.Action(
                name="generate_charts",
                payload={"action": "show_charts"},
                label="📊 Generate Charts",
                tooltip="Click to display interactive market charts"
            )
        ]
        cl.user_session.set("pending_charts", chart_elements)
        
        await progress_msg.remove()
        await cl.Message(
            author=config.ASSISTANT_NAME,
            content=response_text,
            actions=actions,
        ).send()

    except Exception as e:
        traceback.print_exc()
        await progress_msg.remove()
        await cl.Message(author=config.ASSISTANT_NAME, content=f"❌ Error: {str(e)}").send()

@cl.action_callback("generate_charts")
async def on_generate_charts(action: cl.Action):
    """Display charts - simple version that works"""
    charts = cl.user_session.get("pending_charts", [])
    
    if not charts:
        await cl.Message(author=config.ASSISTANT_NAME, content="⚠️ No charts available. Query market data first.").send()
        return
    
    # Send title
    await cl.Message(author=config.ASSISTANT_NAME, content="## 📊 Market Visualization\n\n").send()
    
    # Send each chart in its own message
    for i, chart_elem in enumerate(charts):
        fig = chart_elem.figure
        # Set explicit width
        fig.update_layout(
            width=1000,
            height=500,
            autosize=False,
            margin=dict(l=50, r=50, t=80, b=50)
        )
        new_chart = cl.Plotly(
            name=f"chart_{i}",
            figure=fig,
            display="inline"
        )
        msg = cl.Message(author=config.ASSISTANT_NAME, content="")
        msg.elements = [new_chart]
        await msg.send()
    
    # Clear charts
    cl.user_session.set("pending_charts", [])
