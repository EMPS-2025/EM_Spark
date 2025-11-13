# utils/formatters.py
"""Formatting utilities for dates, times, and money."""

from datetime import date
from typing import List, Tuple, Optional


def format_date(d: date) -> str:
    """Format date as '01 Jan 2025'."""
    if isinstance(d, str):
        return d
    return d.strftime("%d %b %Y")


def format_money(value: Optional[float]) -> str:
    """Format money value as ₹X.XXXX."""
    if value is None:
        return "—"
    return f"₹{value:.4f}"


def format_time_hhmm(total_minutes: int) -> str:
    """Format minutes as HH:MM (24:00 for end of day)."""
    if total_minutes == 24 * 60:
        return "24:00"
    h = (total_minutes // 60) % 24
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"


def compress_ranges(indices: List[int]) -> List[Tuple[int, int]]:
    """Compress list of indices into contiguous ranges.
    
    Example: [1, 2, 3, 5, 6, 8] → [(1, 3), (5, 6), (8, 8)]
    """
    if not indices:
        return []
    
    sorted_unique = sorted(set(indices))
    ranges = []
    start = prev = sorted_unique[0]
    
    for current in sorted_unique[1:]:
        if current == prev + 1:
            prev = current
        else:
            ranges.append((start, prev))
            start = prev = current
    
    ranges.append((start, prev))
    return ranges


def label_hour_ranges(hours: List[int]) -> Tuple[str, str, int]:
    """Convert hour list to time labels and count.
    
    Returns: (time_label, index_label, total_hours)
    Example: ([1, 2, 3, 6, 7]) → ("00:00–03:00 + 05:00–07:00", "1–3, 6–7", 5)
    """
    ranges = compress_ranges(hours)
    
    time_parts = [
        f"{format_time_hhmm((s-1)*60)}–{format_time_hhmm(e*60)}"
        for s, e in ranges
    ]
    
    idx_parts = [
        f"{s}–{e}" if s != e else f"{s}"
        for s, e in ranges
    ]
    
    total_count = sum(e - s + 1 for s, e in ranges)
    
    return " + ".join(time_parts), ", ".join(idx_parts), total_count


def label_slot_ranges(slots: List[int]) -> Tuple[str, str, int]:
    """Convert 15-min slot list to time labels and count.
    
    Returns: (time_label, index_label, total_slots)
    """
    ranges = compress_ranges(slots)
    
    time_parts = [
        f"{format_time_hhmm((s-1)*15)}–{format_time_hhmm(e*15)}"
        for s, e in ranges
    ]
    
    idx_parts = [
        f"{s}–{e}" if s != e else f"{s}"
        for s, e in ranges
    ]
    
    total_count = sum(e - s + 1 for s, e in ranges)
    
    return " + ".join(time_parts), ", ".join(idx_parts), total_count
