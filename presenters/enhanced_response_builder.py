# presenters/enhanced_response_builder.py
"""EM-SPARK Response Builder - Markdown Format"""

from datetime import date
from typing import List, Dict, Optional, Any


class EnhancedResponseBuilder:
    """Build Markdown responses"""

    def build_overview_header(self, market_badge: str, date_label: str,
        selection_details: Dict[str, Any], user_query: str) -> str:
        return f"""## {market_badge}

**Delivery:** {date_label}  
**Time Window:** {selection_details['time_label']}  
**Query:** {user_query[:80]}
"""

    def build_snapshot_card(self, market: str, delivery_label: str, time_window: str,
        twap: float, min_price: float, max_price: float, total_volume_gwh: float) -> str:
        emoji = {"DAM": "📊", "GDAM": "🟢", "RTM": "🔵"}.get(market, "📈")
        return f"""### {emoji} {market} Snapshot

| **Metric** | **Value** |
|-----------|----------|
| Delivery | {delivery_label} |
| Time Window | {time_window} |
| TWAP | ₹{twap:.4f} /kWh |
| Min / Max | ₹{min_price:.4f} / ₹{max_price:.4f} /kWh |
| Total Volume | {total_volume_gwh:.2f} GWh |
"""

    def build_derivative_section(self, derivative_rows: List[Dict]) -> str:
        """Build derivative section - THIS METHOD WAS MISSING"""
        if not derivative_rows:
            return "### 💹 Derivative Market (MCX/NSE)\n\nNo data available.\n"
        
        lines = ["### 💹 Derivative Market (MCX/NSE)\n"]
        for row in derivative_rows:
            exchange = row.get('exchange', 'N/A')
            commodity = row.get('commodity', 'N/A')
            contract_month = row.get('contract_month', 'N/A')
            close_price = float(row.get('close_price_rs_per_mwh', 0)) / 1000.0
            lines.append(f"- **{exchange} • {commodity} • {contract_month}** → ₹{close_price:.2f}/kWh")
        return "\n".join(lines) + "\n"

    def build_market_comparison_section(self, spec_year: int, 
        current_year_data: Dict[str, Dict[str, Any]], 
        previous_year_data: Dict[str, Optional[Dict[str, Any]]]) -> str:
        prev_year = spec_year - 1
        rows = ["| **Market** | **Volume (GWh)** | **Volume Prev** | **Price (₹/kWh)** | **Price Prev** | **YoY %** |"]
        rows.append("|-----------|-----------------|-----------------|------------------|----------------|---------|")
        for market in ["DAM", "GDAM", "RTM"]:
            curr = current_year_data.get(market, {})
            prev = (previous_year_data.get(market) or {}) if previous_year_data else {}
            v_curr = curr.get('total_volume_gwh', 0.0)
            v_prev = prev.get('total_volume_gwh', 0.0) if prev else 0.0
            p_curr = curr.get('twap', 0.0)
            p_prev = prev.get('twap', 0.0) if prev else 0.0
            yoy = ((p_curr - p_prev) / p_prev * 100) if p_prev > 0 else 0.0
            change_str = f"📈 +{yoy:.1f}%" if yoy > 0 else f"📉 {yoy:.1f}%"
            rows.append(f"| {market} | {v_curr:.2f} | {v_prev:.2f} | ₹{p_curr:.4f} | ₹{p_prev:.4f} | {change_str} |")
        return f"""## 📊 Volumes (GWh) and Average Prices (₹/kWh)

### Market Comparison: {spec_year} vs {prev_year}

{chr(10).join(rows)}
"""

    def build_bid_analysis_section(self, all_market_data: Dict[str, Dict[str, Any]]) -> str:
        rows = ["| **Market** | **Buy Bid (MW)** | **Sell Bid (MW)** | **Scheduled (MW)** | **B/S Ratio** |"]
        rows.append("|-----------|-----------------|------------------|-------------------|--------------|")
        ratios = []
        for market in ["DAM", "GDAM", "RTM"]:
            data = all_market_data.get(market, {})
            buy = data.get('purchase_bid_total_mw', 0.0)
            sell = data.get('sell_bid_total_mw', 0.0)
            scheduled = data.get('scheduled_total_mw', 0.0)
            ratio = buy / sell if sell > 0 else 0.0
            ratios.append(ratio)
            rows.append(f"| {market} | {buy:>15,.0f} | {sell:>18,.0f} | {scheduled:>19,.0f} | {ratio:>12.2f} |")
        avg_ratio = sum(ratios) / len(ratios) if ratios else 0.0
        status = "🔴 Demand Heavy" if avg_ratio > 1.2 else "🟢 Balanced" if avg_ratio > 0.8 else "🔵 Supply Heavy"
        return f"""## 📋 Market Bids & Scheduling

{chr(10).join(rows)}

**Status:** {status}
"""

    def build_ai_insights_section(self, insights: List[str]) -> str:
        if not insights or len(insights) == 0:
            return ""
        bullets = "\n".join(f"- {i}" for i in insights)
        return f"""## 🤖 AI-Powered Insights

{bullets}

---
"""

    def compose_dashboard(self, sections: List[str]) -> str:
        valid = [s for s in sections if s and len(s.strip()) > 0]
        return "\n\n".join(valid)
