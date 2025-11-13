# app/app.py - Simplified Chainlit application
"""
EM Spark - Energy Market AI Assistant
Modular, clean version with separated concerns
"""

import asyncio
import traceback
import uuid
from typing import List

import chainlit as cl

# Import our new modules
from core.config import Config
from core.database import DatabaseManager
from core.models import QuerySpec
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

# ═══════════════════════════════════════════════════════════════
# CHAINLIT EVENT HANDLERS
# ═══════════════════════════════════════════════════════════════

@cl.on_chat_start
async def start_session():
    """Initialize user session."""
    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)


@cl.on_message
async def handle_message(msg: cl.Message):
    """Main message handler."""
    user_query = msg.content.strip()
    
    # Special commands
    if user_query.lower() in ("/stats", "stats"):
        await handle_stats_command()
        return
    
    # Show progress
    progress = await show_progress("🔍 Analyzing your query...")
    
    try:
        # Parse the query
        await update_progress(progress, "📅 Parsing dates and times...")
        specs = parse_query(user_query)
        
        if not specs:
            await hide_progress(progress)
            await send_error("I couldn't understand your query. Try:\n"
                           "• `DAM 31 Oct 2025`\n"
                           "• `GDAM 10-15 Aug 2025 for 6-8 hours`\n"
                           "• `Compare Nov 2022, Nov 2023, Nov 2024`")
            return
        
        # Fetch data
        await update_progress(progress, "📊 Fetching market data...")
        sections = []
        
        for spec in specs:
            section = await build_response_section(spec, user_query)
            sections.append(section)
        
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
            "⚠️ An error occurred while processing your request. "
            "Please try again."
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
    import re
    if re.search(r'\b(gdam|green\s*day[-\s]*ahead)\b', text, re.I):
        return "GDAM"
    return "DAM"


def parse_stat(text: str) -> str:
    """Extract statistic type."""
    import re
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
        hours_str = str(hours_count)
    
    return (
        f"## Spot Market ({spec.market}) — {format_date(spec.start_date)} to {format_date(spec.end_date)}\n\n"
        "| **Parameter** | **Value** |\n"
        "|---------------|------------|\n"
        f"| **Market** | {spec.market} |\n"
        f"| **Period** | {format_date(spec.start_date)} to {format_date(spec.end_date)} |\n"
        f"| **Duration** | {time_label} ({hours_str} hrs) |\n"
    )


async def fetch_and_format_data(spec: QuerySpec) -> tuple[str, str]:
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
    # For now, keep your existing derivative logic
    # This can be refactored later into a separate module
    return ""  # Placeholder


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
