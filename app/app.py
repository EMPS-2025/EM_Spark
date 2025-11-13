# app/app.py - Complete Simplified Chainlit Application
"""
EM Spark - Energy Market AI Assistant
Modular, clean version with separated concerns
"""

# >>> MUST BE FIRST LINES IN app/app.py <<<
import os
import sys

# /.../EM-Spark/app
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# /.../EM-Spark  (parent of app, where core/, parsers/, utils/ are)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))

# add project root to sys.path so "from core ..." works
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
import traceback
import uuid
from typing import List, Optional
from datetime import date, datetime
import calendar
import re

import chainlit as cl

# Import our new modules
from presenters.response_builder import ResponseBuilder
from core.config import Config
from core.database import DatabaseManager
from core.models import QuerySpec
from parsers.smart_parser import SmartParser 
from parsers.date_parser import DateParser
from parsers.time_parser import TimeParser
from utils.text_utils import normalize_text, highlight_gdam
from utils.formatters import (
    format_date,
    format_money,
    label_hour_ranges,
    label_slot_ranges,
    compress_ranges,
)



# ═══════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════

config = Config()
db = DatabaseManager(config)
date_parser = DateParser()
time_parser = TimeParser()
response_builder = ResponseBuilder()
smart_parser = SmartParser(config)  # NEW: Smart parser with OpenAI


DISCLAIMER_FOOTER = """

---

**Primary Service:** MCX/NSE Derivative Market Analysis | **Complementary:** DAM/GDAM/RTM Spot Data  
*For research purposes only • Not financial advice • Consult licensed professionals*

© 2025 Energy Minds Power Solutions Pvt. Ltd.
"""

# ═══════════════════════════════════════════════════════════════
# CHAINLIT EVENT HANDLERS
# ═══════════════════════════════════════════════════════════════

@cl.on_chat_start
async def start_session():
    """Initialize user session."""
    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)
    
    # Send styled welcome message
    await cl.Message(
        author=config.ASSISTANT_NAME,
        content="""# 👋 Welcome to EM Spark!

I'm your AI-powered energy market analyst. I can help you with:

- 📊 **DAM prices** - Day-Ahead Market analysis
- 🟢 **GDAM prices** - Green Day-Ahead Market
- 💹 **Derivatives** - MCX/NSE futures data
- 📈 **Comparisons** - Automatic side-by-side analysis

**Try asking:**
- "DAM today"
- "Compare GDAM yesterday vs last week"
- "Show prices for 31 Oct 2025"

*Powered by GPT for intelligent query understanding* 🤖
"""
    ).send()


@cl.on_message
async def handle_message(msg: cl.Message):
    """Main message handler with smart parsing."""
    user_query = msg.content.strip()
    
    # Special commands
    if user_query.lower() in ("/stats", "stats"):
        await handle_stats_command()
        return
    
    # Show progress
    progress = await show_progress("🤖 Understanding your query...")
    
    try:
        # Parse using smart parser (with OpenAI fallback)
        await update_progress(progress, "🧠 Parsing query (AI-powered)...")
        specs = smart_parser.parse(user_query)
        
        if not specs:
            await hide_progress(progress)
            await send_error(
                "I couldn't understand your query. Try:\n\n"
                "✅ **Simple:** `DAM today`, `GDAM yesterday`\n"
                "✅ **Dates:** `31 Oct 2025`, `last week`\n"
                "✅ **Comparison:** `Compare Nov 2022 vs 2023`\n"
                "✅ **Time ranges:** `6-8 hours`, `20-50 slots`\n\n"
                "*I use AI to understand natural language!* 🤖"
            )
            return
        
        # Check if DAM query → automatically add GDAM for comparison
        if len(specs) == 1 and specs[0].market == "DAM":
            # Clone for GDAM
            gdam_spec = QuerySpec(
                market="GDAM",
                start_date=specs[0].start_date,
                end_date=specs[0].end_date,
                granularity=specs[0].granularity,
                hours=specs[0].hours,
                slots=specs[0].slots,
                stat=specs[0].stat
            )
            specs.append(gdam_spec)
            await update_progress(progress, "📊 Adding GDAM comparison...")
        
        # Fetch data
        await update_progress(progress, "📥 Fetching market data...")
        sections = []
        
        for spec in specs:
            section = await build_response_section(spec, user_query)
            sections.append(section)
        
        # Add comparison if we have DAM and GDAM
        if len(specs) == 2 and {specs[0].market, specs[1].market} == {"DAM", "GDAM"}:
            comparison = build_comparison_section(specs, sections)
            if comparison:
                sections.insert(1, comparison)
        
        # Send response
        await hide_progress(progress)
        final_response = "\n\n---\n\n".join(sections)
        final_response = highlight_gdam(final_response)
        
        await cl.Message(
            author=config.ASSISTANT_NAME,
            content=final_response
        ).send()
        
    except Exception as e:
        traceback.print_exc()
        await hide_progress(progress)
        await send_error(
            f"⚠️ An error occurred: {str(e)}\n\n"
            "Please try again or rephrase your query."
        )


# ═══════════════════════════════════════════════════════════════
# QUERY PARSING
# ═══════════════════════════════════════════════════════════════

def parse_query(user_query: str) -> List[QuerySpec]:
    """Parse user query into QuerySpec objects."""
    normalized = normalize_text(user_query)
    
    # Detect market and stat
    market = parse_market(normalized)
    stat = parse_stat(normalized)
    
    # Parse dates
    periods = date_parser.parse_periods(normalized)
    if not periods:
        start, end = date_parser.parse_single_range(normalized)
        if start and end:
            periods = [(start, end)]
    
    if not periods:
        return []
    
    # Parse time ranges
    time_groups = time_parser.parse_time_groups(normalized)
    if not time_groups:
        # Default: full day
        time_groups = [{"granularity": "hour", "hours": list(range(1, 25)), "slots": None}]
    
    # Build specs
    specs = []
    for start_date, end_date in periods:
        for time_group in time_groups:
            spec = QuerySpec(
                market=market,
                start_date=start_date,
                end_date=end_date,
                granularity=time_group["granularity"],
                hours=time_group.get("hours"),
                slots=time_group.get("slots"),
                stat=stat
            )
            specs.append(spec)
    
    return deduplicate_specs(specs)


def parse_market(text: str) -> str:
    """Extract market type (DAM or GDAM)."""
    if re.search(r'\b(gdam|green\s*day[-\s]*ahead)\b', text, re.I):
        return "GDAM"
    return "DAM"


def parse_stat(text: str) -> str:
    """Extract statistic type."""
    lower = text.lower()
    
    if re.search(r'\b(vwap|weighted)\b', lower):
        return "vwap"
    if re.search(r'\bdaily\s+(avg|average)\b', lower):
        return "daily_avg"
    if re.search(r'\b(list|table|rows|detailed)\b', lower):
        return "list"
    if re.search(r'\b(avg|average|mean|twap)\b', lower):
        return "twap"
    
    return config.DEFAULT_STAT


def deduplicate_specs(specs: List[QuerySpec]) -> List[QuerySpec]:
    """Remove duplicate query specifications."""
    seen = set()
    unique = []
    
    for spec in specs:
        key = (
            spec.market,
            spec.start_date,
            spec.end_date,
            spec.granularity,
            tuple(spec.hours or []),
            tuple(spec.slots or []),
            spec.stat
        )
        
        if key not in seen:
            seen.add(key)
            unique.append(spec)
    
    return unique


# ═══════════════════════════════════════════════════════════════
# DATA FETCHING & RESPONSE BUILDING
# ═══════════════════════════════════════════════════════════════

async def build_response_section(spec: QuerySpec, original_query: str) -> str:
    """Build a complete response section for one QuerySpec."""
    
    # Build header with selection card
    if spec.granularity == "hour":
        time_label, idx_label, count = label_hour_ranges(spec.hours)
    else:
        time_label, idx_label, count = label_slot_ranges(spec.slots)
    
    header = build_header(spec, time_label, count)
    
    # Fetch data
    kpi, table = await fetch_and_format_data(spec)
    
    # Fetch derivatives if applicable
    deriv_section = await fetch_derivatives(spec, original_query)
    
    return f"{header}\n\n{kpi}{table}{deriv_section}"


def build_header(spec: QuerySpec, time_label: str, hours_count: float) -> str:
    """Build the selection card header."""
    if spec.granularity == "quarter":
        hours_str = f"{hours_count * 0.25:.2f}".rstrip("0").rstrip(".")
    else:
        hours_str = str(int(hours_count))
    
    return (
        f"## Spot Market ({spec.market}) — {format_date(spec.start_date)} to {format_date(spec.end_date)}\n\n"
        "| **Parameter** | **Value** |\n"
        "|---------------|------------|\n"
        f"| **Market** | {spec.market} |\n"
        f"| **Period** | {format_date(spec.start_date)} to {format_date(spec.end_date)} |\n"
        f"| **Duration** | {time_label} ({hours_str} hrs) |\n"
    )

def build_comparison_section(specs: List[QuerySpec], sections: List[str]) -> Optional[str]:
    """Build comparison card between DAM and GDAM."""
    
    # Find DAM and GDAM specs
    dam_spec = next((s for s in specs if s.market == "DAM"), None)
    gdam_spec = next((s for s in specs if s.market == "GDAM"), None)
    
    if not dam_spec or not gdam_spec:
        return None
    
    # Extract prices from sections (this is a simplification)
    # In reality, you'd pass the actual data
    
    return f"""## 📈 Market Comparison

| Market | Period | Action |
|--------|--------|--------|
| 📊 DAM | {format_date(dam_spec.start_date)} | See above |
| 🟢 GDAM | {format_date(gdam_spec.start_date)} | See below |

💡 *Scroll down to see GDAM data and comparison*
"""


async def fetch_and_format_data(spec: QuerySpec) -> tuple:
    """Fetch data and return (KPI, table) as markdown strings."""
    
    if spec.granularity == "hour":
        # Try hourly first
        rows = []
        for b1, b2 in compress_ranges(spec.hours):
            rows += db.fetch_hourly(spec.market, spec.start_date, spec.end_date, b1, b2)
        
        if rows:
            twap = calculate_twap(rows, "price_avg_rs_per_mwh", "duration_min")
            vwap = calculate_vwap(rows, "price_avg_rs_per_mwh", "scheduled_mw_sum", "duration_min")
            primary_value = vwap if spec.stat == "vwap" else twap
            
            kpi = f"**Average price: {format_money(primary_value)} /kWh**\n\n"
            table = format_hourly_table(rows) if spec.stat == "list" else ""
            return kpi, table
        else:
            # Fallback to quarter
            qrows = []
            slot_ranges = hour_blocks_to_slot_ranges(compress_ranges(spec.hours))
            for s1, s2 in slot_ranges:
                qrows += db.fetch_quarter(spec.market, spec.start_date, spec.end_date, s1, s2)
            
            twap = calculate_twap(qrows, "price_rs_per_mwh", "duration_min")
            vwap = calculate_vwap(qrows, "price_rs_per_mwh", "scheduled_mw", "duration_min")
            primary_value = vwap if spec.stat == "vwap" else twap
            
            kpi = f"**Average price: {format_money(primary_value)} /kWh** _(via 15-min slots)_\n\n"
            table = format_quarter_table(qrows) if spec.stat == "list" else ""
            return kpi, table
    
    else:
        # Quarter granularity
        qrows = []
        for s1, s2 in compress_ranges(spec.slots):
            qrows += db.fetch_quarter(spec.market, spec.start_date, spec.end_date, s1, s2)
        
        twap = calculate_twap(qrows, "price_rs_per_mwh", "duration_min")
        vwap = calculate_vwap(qrows, "price_rs_per_mwh", "scheduled_mw", "duration_min")
        primary_value = vwap if spec.stat == "vwap" else twap
        
        kpi = f"**Average price: {format_money(primary_value)} /kWh**\n\n"
        table = format_quarter_table(qrows) if spec.stat == "list" else ""
        return kpi, table


async def fetch_derivatives(spec: QuerySpec, original_query: str) -> str:
    """Fetch and format derivative data if applicable."""
    deriv_block = ""
    
    if spec.start_date == spec.end_date:
        # Single day → last close
        drows = db.fetch_deriv_daily_fallback(spec.end_date, None)
        if drows:
            deriv_block = "\n" + render_deriv_companion_for_day(spec.end_date, drows)
    
    elif same_calendar_month(spec.start_date, spec.end_date) or is_month_intent(original_query, spec.start_date, spec.end_date):
        # Range in one month
        drows = db.fetch_deriv_daily_fallback(spec.end_date, None)
        
        filtered = []
        seen_ex = set()
        for r in drows:
            if is_same_contract_month(spec.end_date, r['contract_month']):
                ex = r['exchange']
                if ex not in seen_ex:
                    seen_ex.add(ex)
                    filtered.append(r)
        
        if filtered:
            deriv_block = "\n" + render_deriv_daily_for_contract_month(spec.end_date, filtered)
        else:
            cm_first = date(spec.end_date.year, spec.end_date.month, 1)
            mrows = db.fetch_deriv_month_expiry(cm_first, None)
            deriv_block = "\n" + render_deriv_expiry(cm_first, mrows)
    
    else:
        # Cross-month ranges
        drows = db.fetch_deriv_daily_fallback(spec.end_date, None)
        if drows:
            deriv_block = "\n" + render_deriv_companion_for_day(spec.end_date, drows)
    
    return deriv_block


# ═══════════════════════════════════════════════════════════════
# CALCULATIONS
# ═══════════════════════════════════════════════════════════════

def calculate_twap(rows, price_key: str, minute_key: str):
    """Calculate time-weighted average price in ₹/kWh."""
    if not rows:
        return None
    num = sum(float(r[price_key]) * float(r[minute_key]) for r in rows)
    den = sum(float(r[minute_key]) for r in rows)
    return None if den == 0 else (num / den) / 1000.0


def calculate_vwap(rows, price_key: str, sched_key: str, minute_key: str):
    """Calculate volume-weighted average price in ₹/kWh."""
    if not rows:
        return None
    weights = [float(r.get(sched_key) or 0) * float(r[minute_key]) for r in rows]
    num = sum(float(r[price_key]) * w for r, w in zip(rows, weights))
    den = sum(weights)
    if den > 0:
        return (num / den) / 1000.0
    return calculate_twap(rows, price_key, minute_key)


def hour_blocks_to_slot_ranges(hour_ranges):
    """Convert hour block ranges to slot ranges."""
    out = []
    for b1, b2 in hour_ranges:
        s1 = (b1 - 1) * 4 + 1
        s2 = b2 * 4
        out.append((s1, s2))
    return out


# ═══════════════════════════════════════════════════════════════
# TABLE FORMATTING
# ═══════════════════════════════════════════════════════════════

def format_hourly_table(rows, limit=120):
    """Format hourly data as markdown table."""
    if not rows:
        return "_No data available._"
    
    show = rows if len(rows) <= limit else rows[:60] + rows[-60:]
    lines = [
        "| Date | Hour | Block | Price (₹/kWh) | Sched MW |",
        "|------|------|------:|--------------:|---------:|"
    ]
    
    for r in show:
        dd = format_date(r["delivery_date"]) if hasattr(r["delivery_date"], "strftime") else r["delivery_date"]
        b = int(r["block_index"])
        price_kwh = float(r["price_avg_rs_per_mwh"]) / 1000.0
        sched = float(r.get("scheduled_mw_sum") or 0)
        lines.append(f"| {dd} | {hour_window(b)} | {b:>2} | {price_kwh:.4f} | {sched:.2f} |")
    
    if len(rows) > limit:
        lines.insert(2, f"_Showing first 60 and last 60 of {len(rows)} rows_")
    
    return "\n".join(lines)


def format_quarter_table(rows, limit=120):
    """Format 15-min slot data as markdown table."""
    if not rows:
        return "_No data available._"
    
    show = rows if len(rows) <= limit else rows[:60] + rows[-60:]
    lines = [
        "| Date | Slot | Slot # | Price (₹/kWh) | Sched MW |",
        "|------|------|-------:|--------------:|---------:|"
    ]
    
    for r in show:
        dd = format_date(r["delivery_date"]) if hasattr(r["delivery_date"], "strftime") else r["delivery_date"]
        s = int(r["slot_index"])
        price_kwh = float(r["price_rs_per_mwh"]) / 1000.0
        sched = float(r.get("scheduled_mw") or 0)
        lines.append(f"| {dd} | {slot_window(s)} | {s:>2} | {price_kwh:.4f} | {sched:.2f} |")
    
    if len(rows) > limit:
        lines.insert(2, f"_Showing first 60 and last 60 of {len(rows)} rows_")
    
    return "\n".join(lines)


def hour_window(block: int) -> str:
    """Format hour block as time window."""
    return f"{(block-1):02d}:00–{block:02d}:00"


def slot_window(slot: int) -> str:
    """Format 15-min slot as time window."""
    start_min = (slot - 1) * 15
    end_min = slot * 15
    return f"{start_min//60:02d}:{start_min%60:02d}–{end_min//60:02d}:{end_min%60:02d}"


# ═══════════════════════════════════════════════════════════════
# DERIVATIVE RENDERING
# ═══════════════════════════════════════════════════════════════

def render_deriv_companion_for_day(requested_day: date, rows: list) -> str:
    """Side panel for derivatives when user asked a single day."""
    if not rows:
        return f"### **Derivative Market (MCX/NSE)** — {requested_day.strftime('%d %b %Y')}\n\nN/A (no derivative data before Jul 2025)."
    
    used_dates = sorted([
        r['used_trading_date'].date() if isinstance(r['used_trading_date'], datetime) else r['used_trading_date']
        for r in rows
    ])
    
    if len(used_dates) == 1 and used_dates[0] != requested_day:
        note = f"\n\n*Market closed on {requested_day.strftime('%d %b %Y')} — showing last close on {used_dates[0].strftime('%d %b %Y')}*"
    elif len(used_dates) > 1:
        note = "\n\n*Market closed — showing last close per exchange*"
    else:
        note = ""
    
    lines = [f"### **Derivative Market (MCX/NSE)** — {requested_day.strftime('%d %b %Y')}\n{note}\n"]

    for r in rows:
        td = r['trading_date']
        cm = r['contract_month']
        
        if isinstance(td, datetime):
            td = td.date()
        if isinstance(cm, datetime):
            cm = cm.date()
        
        tag = "" if td == requested_day else f" ({td.strftime('%d %b %Y')})"
        
        lines.append(f"- **{r['exchange']} • {r['commodity']} • {cm.strftime('%b %Y')}** → ₹{float(r['close_price_rs_per_mwh']/1000):.2f}/kWh{tag}")
    
    return "\n".join(lines)


def render_deriv_daily_for_contract_month(end_day: date, rows: list) -> str:
    """Rows filtered for same contract month."""
    label = end_day.strftime("%b %Y")
    lines = [f"### **Derivative Market — {label} contract (Last close as of {end_day.strftime('%d %b %Y')})**\n"]
    for r in rows:
        used = r['used_trading_date']
        if isinstance(used, datetime):
            used = used.date()
        price_kwh = float(r['close_price_rs_per_mwh']) / 1000.0
        lines.append(f"- **{r['exchange']} • {r['commodity']}** → ₹{price_kwh:.2f}/kWh (on {used.strftime('%d %b %Y')})")
    return "\n".join(lines)


def render_deriv_expiry(cm_first: date, rows: list) -> str:
    """Show expiry as a single last-close date."""
    month_label = cm_first.strftime("%b %Y")
    if not rows:
        return f"### **Derivative Market — {month_label} (Expiry Close)**\n\n_Expiry not available yet._"

    expiry_dates = []
    for r in rows:
        ed = r["expiry_date"]
        if isinstance(ed, datetime):
            ed = ed.date()
        if isinstance(ed, date):
            expiry_dates.append(ed)
    if not expiry_dates:
        return f"### **Derivative Market — {month_label} (Expiry Close)**\n\n_Expiry date not available._"

    last_close_day = max(expiry_dates)
    lines = [f"### **Derivative Market — Expiry Close on {last_close_day.strftime('%d %b %Y')}**\n"]
    for r in rows:
        price_kwh = float(r['expiry_close']) / 1000.0
        lines.append(f"- **{r['exchange']} • {r['commodity']}** → ₹{price_kwh:.2f}/kWh")
    return "\n".join(lines)


def same_calendar_month(a: date, b: date) -> bool:
    """Check if two dates are in same calendar month."""
    return (a.year == b.year) and (a.month == b.month)


def is_same_contract_month(target_day: date, cm: date) -> bool:
    """Check if target day matches contract month."""
    if isinstance(cm, datetime):
        cm = cm.date()
    return cm.year == target_day.year and cm.month == target_day.month


def is_month_intent(text: str, start: date, end: date) -> bool:
    """Check if user asked for a full month."""
    if not start or not end:
        return False
    first = date(start.year, start.month, 1)
    last  = date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
    whole_month = (start == first and end == last)
    month_pattern = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)"
    has_month_word = bool(re.search(month_pattern, text or "", re.I))
    return whole_month and has_month_word


# ═══════════════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════════════

async def show_progress(text: str) -> cl.Message:
    """Show loading indicator."""
    msg = cl.Message(author=config.ASSISTANT_NAME, content=text)
    await msg.send()
    return msg


async def update_progress(msg: cl.Message, text: str):
    """Update loading text."""
    try:
        await msg.update(content=text)
    except Exception:
        pass


async def hide_progress(msg: cl.Message):
    """Hide loading indicator."""
    try:
        await msg.remove()
    except Exception:
        pass


async def send_error(text: str):
    """Send error message."""
    await cl.Message(author=config.ASSISTANT_NAME, content=text).send()


async def handle_stats_command():
    """Display usage statistics."""
    await cl.Message(
        author=config.ASSISTANT_NAME,
        content=(
            "## 📈 Service Usage\n\n"
            "_Statistics tracking coming soon..._"
        )
    ).send()
