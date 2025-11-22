# presenters/enhanced_response_builder.py
"""EM-SPARK Response Builder - Markdown Format for Chainlit 2.0"""

from typing import List, Dict, Any

class EnhancedResponseBuilder:
    
    def _format_yoy_chip(self, value: float) -> str:
        if value == 0:
            return "-"
        
        symbol = "▲" if value > 0 else "▼"
        # Use HTML span for color, which is usually allowed inside Markdown tables
        color_class = "em-badge-green" if value > 0 else "em-badge-red"
        # Fallback to emoji if span fails, but try span first
        return f'<span class="{color_class}">{symbol} {abs(value):.1f}%</span>'

    def build_overview_header(self, market_badge: str, date_label: str, selection_details: Dict[str, Any], user_query: str) -> str:
        return (
            f"# {market_badge}\n\n"
            f"📅 **{date_label}** |  ⏰ {selection_details['time_label']}\n"
            f"\n"
        )

    def build_snapshot_card(
        self, 
        market: str, 
        delivery_label: str, 
        time_window: str, 
        twap: float, 
        min_price: float, 
        max_price: float, 
        total_volume_gwh: float,
        renewable_mix_pct: float = 0.0,
        total_market_vol: float = 0.0
    ) -> str:
        """
        Builds a Markdown table that CSS transforms into a Card.
        """
        share_pct = (total_volume_gwh / total_market_vol * 100) if total_market_vol > 0 else 0
        
        # Using HTML line breaks <br> inside Markdown cells is standard and supported
        price_cell = f"**₹{twap:.2f}** /kWh<br>_📈 System Normal_"
        vol_cell = f"**{total_volume_gwh:.1f} GWh**<br>_{share_pct:.1f}% of Total_"
        mix_cell = f"**{renewable_mix_pct:.1f}%**<br>_Green Share_"

        return (
            f"| Market Clearing Price | {market} Volume | Renewable Mix |\n"
            f"| :--- | :--- | :--- |\n"
            f"| {price_cell} | {vol_cell} | {mix_cell} |"
        )

    def build_derivative_section(self, derivative_rows: List[Dict], actual_trading_date=None, requested_date=None) -> str:
        if derivative_rows is None or (isinstance(derivative_rows, list) and len(derivative_rows) == 0 and actual_trading_date is None):
            return "> ℹ️ **Derivative Market Not Available** (Started July 2025)"
        
        if not derivative_rows:
            return ""
        
        date_label = f"({actual_trading_date.strftime('%d %b %Y')})" if actual_trading_date else ""
        
        rows_md = ""
        for row in derivative_rows:
            price = float(row.get('close_price_rs_per_mwh', 0) or 0) / 1000.0
            month = row.get('contract_month').strftime('%b %Y') if hasattr(row.get('contract_month'), 'strftime') else row.get('contract_month')
            rows_md += f"| {row.get('exchange')} | {row.get('commodity')} | {month} | **₹{price:.2f}** |\n"

        return (
            f"### 💹 Derivative Market {date_label}\n\n"
            f"| Exchange | Commodity | Month | Close Price |\n"
            f"| :--- | :--- | :--- | ---: |\n"
            f"{rows_md}"
        )

    def build_market_comparison_section(
        self, 
        spec_year: int, 
        current_year_data: Dict[str, Dict[str, Any]], 
        previous_year_data: Dict[str, Any],
        current_date_range: str = None,
        current_time_window: str = None
    ) -> str:
        prev_year = spec_year - 1
        
        rows_md = ""
        for market in ["DAM", "GDAM", "RTM"]:
            curr = current_year_data.get(market, {})
            prev = previous_year_data.get(market, {}) if previous_year_data else {}
            
            p_curr = curr.get('twap', 0.0)
            p_prev = prev.get('twap', 0.0)
            v_curr = curr.get('total_volume_gwh', 0.0)
            v_prev = prev.get('total_volume_gwh', 0.0)
            
            yoy_val = ((p_curr - p_prev) / p_prev * 100) if p_prev > 0 else 0.0
            yoy_chip = self._format_yoy_chip(yoy_val)
            
            # Emoji badges for market names
            market_map = {"DAM": "🟦 DAM", "GDAM": "🟩 GDAM", "RTM": "🟧 RTM"}
            market_label = market_map.get(market, market)
            
            rows_md += (
                f"| **{market_label}** | {v_curr:.1f} GWh <br> <small>({v_prev:.1f})</small> "
                f"| **₹{p_curr:.3f}** <br> <small>(₹{p_prev:.3f})</small> | {yoy_chip} |\n"
            )

        return (
            f"### 📊 Market Comparison ({spec_year} vs {prev_year})\n\n"
            f"| Market | Volume | Price | YoY Δ |\n"
            f"| :--- | ---: | ---: | ---: |\n"
            f"{rows_md}"
        )

    def build_ai_insights_section(self, insights: List[str]) -> str:
        if not insights: return ""
        
        lis = "\n".join([f"- {i}" for i in insights])
        
        return (
            f"### 🤖 AI Insights\n\n"
            f"{lis}"
        )

    def compose_dashboard(self, sections: List[str]) -> str:
        return "\n\n".join([s for s in sections if s and len(s.strip()) > 0])
