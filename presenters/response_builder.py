# presenters/response_builder.py
"""
Advanced response builder with:
- Card-based layouts
- Automatic DAM vs GDAM comparison
- Percentage differences
- Chart data preparation
"""

from datetime import date
from typing import List, Dict, Optional, Tuple
from core.models import QuerySpec


class ResponseBuilder:
    """Build beautiful, card-based responses with comparisons."""
    
    def __init__(self):
        pass
    
    def build_market_card(
        self,
        spec: QuerySpec,
        kpi_data: Dict,
        table_html: str = ""
    ) -> str:
        """Build a single market data card."""
        
        market_badge = self._get_market_badge(spec.market)
        time_range = self._format_time_range(spec)
        
        card = f"""
## {market_badge} Spot Market — {self._format_date(spec.start_date)} to {self._format_date(spec.end_date)}

| Parameter | Value |
|-----------|-------|
| **Market** | {spec.market} |
| **Period** | {self._format_date(spec.start_date)} to {self._format_date(spec.end_date)} |
| **Duration** | {time_range} |

**Average Price: {self._format_price(kpi_data.get('primary_price'))} /kWh**
"""
        
        if table_html:
            card += f"\n{table_html}\n"
        
        return card
    
    def build_comparison_card(
        self,
        dam_spec: QuerySpec,
        gdam_spec: QuerySpec,
        dam_data: Dict,
        gdam_data: Dict
    ) -> str:
        """Build DAM vs GDAM comparison card."""
        
        dam_price = dam_data.get('primary_price')
        gdam_price = gdam_data.get('primary_price')
        
        if not dam_price or not gdam_price:
            return ""
        
        diff = gdam_price - dam_price
        diff_pct = (diff / dam_price * 100) if dam_price > 0 else 0
        
        comparison_icon = "📈" if diff > 0 else "📉"
        diff_color = "success" if diff < 0 else "danger"
        
        card = f"""
## {comparison_icon} Market Comparison — {self._format_date(dam_spec.start_date)}

| Market | Average Price | Difference |
|--------|--------------|------------|
| 📊 **DAM** | {self._format_price(dam_price)} /kWh | — |
| 🟢 **GDAM** | {self._format_price(gdam_price)} /kWh | {self._format_diff(diff, diff_pct)} |

"""
        
        if diff < 0:
            card += f"✅ **GDAM is {abs(diff_pct):.1f}% cheaper** than DAM  \n"
        else:
            card += f"⚠️ **GDAM is {diff_pct:.1f}% more expensive** than DAM  \n"
        
        card += f"\n💡 *Difference: {self._format_price(abs(diff))} /kWh*\n"
        
        return card
    
    def build_time_comparison_card(
        self,
        specs: List[QuerySpec],
        all_data: List[Dict]
    ) -> str:
        """Build time-period comparison card (e.g., Nov 2022 vs 2023 vs 2024)."""
        
        if len(specs) < 2:
            return ""
        
        card = "## 📊 Period Comparison\n\n"
        card += "| Period | Market | Average Price | vs Previous |\n"
        card += "|--------|--------|---------------|-------------|\n"
        
        prev_price = None
        for i, (spec, data) in enumerate(zip(specs, all_data)):
            price = data.get('primary_price')
            period_label = self._format_date_range(spec.start_date, spec.end_date)
            
            if prev_price and price:
                diff = price - prev_price
                diff_pct = (diff / prev_price * 100) if prev_price > 0 else 0
                diff_str = self._format_diff(diff, diff_pct)
            else:
                diff_str = "—"
            
            market_badge = "🟢" if spec.market == "GDAM" else "📊"
            
            card += f"| {period_label} | {market_badge} {spec.market} | {self._format_price(price)} /kWh | {diff_str} |\n"
            
            prev_price = price
        
        return card
    
    # ═══════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def _get_market_badge(self, market: str) -> str:
        """Get emoji badge for market type."""
        return "🟢 GDAM" if market == "GDAM" else "📊 DAM"
    
    def _format_date(self, d: date) -> str:
        """Format date as 'DD Mon YYYY'."""
        return d.strftime("%d %b %Y")
    
    def _format_date_range(self, start: date, end: date) -> str:
        """Format date range."""
        if start == end:
            return self._format_date(start)
        elif start.month == end.month and start.year == end.year:
            return f"{start.strftime('%b %Y')}"
        else:
            return f"{self._format_date(start)} to {self._format_date(end)}"
    
    def _format_time_range(self, spec: QuerySpec) -> str:
        """Format time range description."""
        if spec.granularity == "hour" and spec.hours:
            if len(spec.hours) == 24:
                return "00:00–24:00 (24 hrs)"
            ranges = self._compress_ranges(spec.hours)
            if len(ranges) == 1:
                s, e = ranges[0]
                return f"{(s-1):02d}:00–{e:02d}:00 ({e-s+1} hrs)"
            return f"{len(spec.hours)} hours"
        elif spec.granularity == "quarter" and spec.slots:
            total_hours = len(spec.slots) * 0.25
            return f"{total_hours:.1f} hrs"
        return "Full day"
    
    def _format_price(self, price: Optional[float]) -> str:
        """Format price value."""
        if price is None:
            return "—"
        return f"₹{price:.4f}"
    
    def _format_diff(self, diff: float, diff_pct: float) -> str:
        """Format difference with percentage."""
        if diff > 0:
            return f"🔺 +{abs(diff_pct):.1f}%"
        elif diff < 0:
            return f"🔻 -{abs(diff_pct):.1f}%"
        return "—"
    
    def _compress_ranges(self, indices: List[int]) -> List[Tuple[int, int]]:
        """Compress list of indices into ranges."""
        if not indices:
            return []
        
        sorted_indices = sorted(set(indices))
        ranges = []
        start = prev = sorted_indices[0]
        
        for curr in sorted_indices[1:]:
            if curr == prev + 1:
                prev = curr
            else:
                ranges.append((start, prev))
                start = prev = curr
        
        ranges.append((start, prev))
        return ranges