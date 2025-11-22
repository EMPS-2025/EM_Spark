# presenters/enhanced_response_builder.py
"""EM-SPARK Response Builder - Minified HTML for Chainlit 2.0"""

from typing import List, Dict, Any

class EnhancedResponseBuilder:
    
    def _format_yoy_chip(self, value: float) -> str:
        if value == 0:
            return '<span style="color: #64748b; font-size: 0.85em;">-</span>'
            
        color = "#166534" if value > 0 else "#991b1b"
        bg = "#dcfce7" if value > 0 else "#fee2e2"
        icon = "▲" if value > 0 else "▼"
        text = f"{abs(value):.1f}%"
        
        # Flattened string
        return f'<span style="background-color: {bg}; color: {color}; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">{icon} {text}</span>'

    def build_overview_header(self, market_badge: str, date_label: str, selection_details: Dict[str, Any], user_query: str) -> str:
        # Flattened string
        return f'<div class="em-header" style="margin-bottom: 24px;"><div style="font-size: 0.85rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">Market Intelligence</div><h1 style="font-size: 1.75rem; font-weight: 700; color: #0f172a; margin: 0;">{market_badge}</h1><div style="display: flex; gap: 16px; margin-top: 12px; font-size: 0.9rem; color: #475569;"><span>📅 <strong>{date_label}</strong></span><span>⏰ {selection_details["time_label"]}</span></div></div>'

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
        mix_color = "#16a34a" if renewable_mix_pct > 0 else "#64748b"
        mix_bg = "#dcfce7" if renewable_mix_pct > 0 else "#f1f5f9"
        share_pct = (total_volume_gwh / total_market_vol * 100) if total_market_vol > 0 else 0

        # Flattened string
        return (
            f'<div class="em-spark-card" style="background: white; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; margin-bottom: 24px;">'
            f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 24px;">'
            f'<div style="display: flex; flex-direction: column;"><div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; margin-bottom: 8px;">Market Clearing Price</div><div style="font-size: 2.25rem; font-weight: 700; color: #0f172a; line-height: 1;">₹{twap:.2f}<span style="font-size: 1rem; color: #64748b; font-weight: 500; margin-left: 4px;">/kWh</span></div><div style="margin-top: 8px; display: inline-flex; align-items: center; background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; width: fit-content;">📈 System Normal</div></div>'
            f'<div style="display: flex; flex-direction: column; border-left: 1px solid #f1f5f9; padding-left: 24px;"><div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; margin-bottom: 8px;">{market} Volume</div><div style="font-size: 1.75rem; font-weight: 700; color: #0f172a;">{total_volume_gwh:.1f} <span style="font-size: 1rem; color: #64748b;">GWh</span></div><div style="font-size: 0.85rem; color: #64748b; margin-top: 4px;"><strong>{share_pct:.1f}%</strong> of Total ({total_market_vol:.1f} GWh)</div></div>'
            f'<div style="display: flex; flex-direction: column; background: {mix_bg}; border-radius: 12px; padding: 16px; border: 1px solid {mix_color}30;"><div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;"><span style="font-size: 1rem;">🌿</span><div style="font-size: 0.75rem; color: {mix_color}; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Renewable Mix</div></div><div style="font-size: 1.75rem; font-weight: 700; color: {mix_color};">{renewable_mix_pct:.1f}%</div><div style="font-size: 0.75rem; color: {mix_color}; opacity: 0.9; font-weight: 500;">Green Market Share</div></div>'
            f'</div></div>'
        )

    def build_derivative_section(self, derivative_rows: List[Dict], actual_trading_date=None, requested_date=None) -> str:
        if derivative_rows is None or (isinstance(derivative_rows, list) and len(derivative_rows) == 0 and actual_trading_date is None):
            return (
                f'<div style="background: #fef3c7; border-radius: 12px; padding: 20px; border: 1px solid #fbbf24; margin-bottom: 24px;">'
                f'<div style="display: flex; align-items: center; gap: 12px;"><div style="font-size: 1.5rem;">ℹ️</div><div><div style="font-weight: 600; color: #92400e; margin-bottom: 4px;">Derivative Market Not Available</div><div style="font-size: 0.875rem; color: #78350f;">The electricity derivative market (futures) started operations from <strong>July 2025</strong> onwards.</div></div></div></div>'
            )
        
        if not derivative_rows:
            return ""
        
        date_label = ""
        if actual_trading_date and requested_date:
            if actual_trading_date != requested_date:
                date_label = f' • Showing {actual_trading_date.strftime("%d %b %Y")} (Last Trading Day)'
            else:
                date_label = f' • Trading Date: {actual_trading_date.strftime("%d %b %Y")}'
        elif actual_trading_date:
            date_label = f' • Trading Date: {actual_trading_date.strftime("%d %b %Y")}'
        
        rows_html = ""
        for row in derivative_rows:
            exchange = row.get('exchange', 'N/A')
            price_kwh = float(row.get('close_price_rs_per_mwh', 0) or 0) / 1000.0
            month = row.get('contract_month', 'N/A')
            if hasattr(month, 'strftime'):
                month = month.strftime('%b %Y')
            
            rows_html += f'<tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 12px 16px; font-weight: 600;">{exchange}</td><td style="padding: 12px 16px;">{row.get("commodity", "N/A")}</td><td style="padding: 12px 16px;">{month}</td><td style="padding: 12px 16px; text-align: right; font-family: monospace; font-weight: 600;">₹{price_kwh:.2f}</td></tr>'
        
        return (
            f'<div style="background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; margin-bottom: 24px;">'
            f'<div style="background: linear-gradient(to right, #0056D2, #0041a3); color: white; padding: 12px 16px; font-weight: 600; font-size: 0.95rem;">💹 Derivative Market (Futures){date_label}</div>'
            f'<table style="width: 100%; border-collapse: collapse;">'
            f'<thead style="background: #f8fafc; color: #64748b; font-size: 0.75rem; text-transform: uppercase;"><tr><th style="padding: 10px 16px; text-align: left;">Exchange</th><th style="padding: 10px 16px; text-align: left;">Commodity</th><th style="padding: 10px 16px; text-align: left;">Month</th><th style="padding: 10px 16px; text-align: right;">Close Price</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>'
        )

    def build_market_comparison_section(
        self, 
        spec_year: int, 
        current_year_data: Dict[str, Dict[str, Any]], 
        previous_year_data: Dict[str, Any],
        current_date_range: str = None,
        current_time_window: str = None
    ) -> str:
        """
        Build market comparison with detailed date and time information.
        """
        prev_year = spec_year - 1
        rows_html = ""
        
        comparison_label = f"{spec_year} vs {prev_year}"
        if current_date_range and current_time_window:
            comparison_subtitle = f"Comparing {spec_year} vs {prev_year} (Same Period)"
        elif current_date_range:
            comparison_subtitle = f"{current_date_range} • {spec_year} vs {prev_year}"
        else:
            comparison_subtitle = f"Volume (GWh) & Price (₹/kWh)"
        
        for market in ["DAM", "GDAM", "RTM"]:
            curr = current_year_data.get(market, {})
            prev = (previous_year_data.get(market) or {}) if previous_year_data else {}
            
            v_curr = curr.get('total_volume_gwh', 0.0)
            v_prev = prev.get('total_volume_gwh', 0.0)
            p_curr = curr.get('twap', 0.0)
            p_prev = prev.get('twap', 0.0)
            
            yoy_val = ((p_curr - p_prev) / p_prev * 100) if p_prev > 0 else 0.0
            yoy_chip = self._format_yoy_chip(yoy_val)
            
            market_color = "#0056D2" if market == "DAM" else ("#10b981" if market == "GDAM" else "#f59e0b")
            market_badge = f'<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{market_color}; margin-right:8px;"></span>{market}'
            
            prev_label = f"{prev_year}" if current_date_range else "prev"
            
            rows_html += (
                f'<tr style="border-bottom: 1px solid #f1f5f9;">'
                f'<td style="padding: 16px; font-weight: 600;">{market_badge}</td>'
                f'<td style="padding: 16px; text-align: right;"><div style="font-weight: 500;">{v_curr:,.1f} GWh</div><div style="font-size: 0.75rem; color: #94a3b8;">{v_prev:,.1f} ({prev_label})</div></td>'
                f'<td style="padding: 16px; text-align: right;"><div style="font-weight: 600; color: #0f172a;">₹{p_curr:.3f}</div><div style="font-size: 0.75rem; color: #94a3b8;">₹{p_prev:.3f} ({prev_label})</div></td>'
                f'<td style="padding: 16px; text-align: right;">{yoy_chip}</td>'
                f'</tr>'
            )
    
        return (
            f'<div style="background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; margin-bottom: 24px;">'
            f'<div style="padding: 16px; border-bottom: 1px solid #e2e8f0;">'
            f'<h3 style="margin: 0; font-size: 1rem; color: #0f172a;">📊 Market Comparison</h3>'
            f'<div style="font-size: 0.8rem; color: #64748b; margin-top: 2px;">{comparison_subtitle}</div>'
            f'</div>'
            f'<table style="width: 100%; border-collapse: collapse;">'
            f'<thead style="background: #f8fafc; color: #64748b; font-size: 0.75rem; text-transform: uppercase;"><tr><th style="padding: 10px 16px; text-align: left;">Market</th><th style="padding: 10px 16px; text-align: right;">Volume</th><th style="padding: 10px 16px; text-align: right;">Price</th><th style="padding: 10px 16px; text-align: right;">YoY Δ</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>'
        )

    def build_ai_insights_section(self, insights: List[str]) -> str:
        if not insights: return ""
        
        lis = "".join([f'<li style="margin-bottom: 8px; position: relative; padding-left: 20px;"><span style="position: absolute; left: 0; color: #00BCE4;">•</span> {i}</li>' for i in insights])
        
        return (
            f'<div style="background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%); border-radius: 12px; padding: 20px; border: 1px solid #dbeafe;">'
            f'<h3 style="margin: 0 0 12px 0; color: #1e40af; font-size: 1rem; display: flex; align-items: center; gap: 8px;">'
            f'🤖 AI Insights'
            f'</h3>'
            f'<ul style="margin: 0; padding: 0; list-style: none; font-size: 0.95rem; color: #334155;">'
            f'{lis}'
            f'</ul>'
            f'</div>'
        )

    def compose_dashboard(self, sections: List[str]) -> str:
        return "".join([s for s in sections if s and len(s.strip()) > 0])
