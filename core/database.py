# core/database.py
"""
Database Manager
Handles strict mapping between SQL RPC results and Python dicts.
"""
import os
import psycopg2
import psycopg2.extras
from typing import List, Dict, Optional
from datetime import date

class DatabaseManager:
    """Manages database connections and queries."""
    
    def __init__(self, config=None):
        dsn = os.getenv("DATABASE_URL", "").strip()
        if not dsn:
            raise RuntimeError("DATABASE_URL is not set in .env")
        self.dsn = dsn
    
    def _connect(self):
        return psycopg2.connect(self.dsn, sslmode="require")

    def _safe_float(self, val) -> float:
        """Safely convert Decimal/String/Int to float, defaulting to 0.0."""
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    # ═══════════════════════════════════════════════════════════
    # CORE MARKET FETCH (DAM/GDAM/RTM)
    # ═══════════════════════════════════════════════════════════
    
    def fetch_hourly(
        self,
        market: str,
        start_date: date,
        end_date: date,
        block_start: Optional[int] = None,
        block_end: Optional[int] = None,
        exclusion = None
    ) -> List[Dict]:
        """
        Fetch hourly aggregated data.
        RPC Return: price_avg_rs_per_mwh, scheduled_mw_sum, purchase_bid_avg_mw, sell_bid_avg_mw, mcv_sum_mw
        """
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if block_start and block_end:
                    query = "SELECT * FROM public.rpc_get_hourly_prices_range(%s,%s,%s,%s,%s);"
                    params = (market, start_date, end_date, block_start, block_end)
                else:
                    query = "SELECT * FROM public.rpc_get_hourly_prices_range(%s,%s,%s,NULL,NULL);"
                    params = (market, start_date, end_date)
                
                cur.execute(query, params)
                rows = [dict(r) for r in cur.fetchall()]

                
                
                # Normalize keys for the app
                cleaned_rows = []
                for r in rows:
                    delivery_date = r.get('delivery_date')
                    
                    # ✅ NEW: Check exclusion
                    if exclusion and delivery_date:
                        if exclusion.should_exclude_date(delivery_date):
                            continue  # Skip this row
                    
                    cleaned_rows.append({
                        'delivery_date': delivery_date,
                        'block_index': r.get('block_index'),
                        'price_avg': self._safe_float(r.get('price_avg_rs_per_mwh')),
                        'scheduled_mw': self._safe_float(r.get('scheduled_mw_sum')),
                        'purchase_bid_mw': self._safe_float(r.get('purchase_bid_avg_mw')),
                        'sell_bid_mw': self._safe_float(r.get('sell_bid_avg_mw')),
                        'mcv_mw': self._safe_float(r.get('mcv_sum_mw')),
                        'duration_min': 60
                    })
                
                return cleaned_rows

    def fetch_quarter(
        self,
        market: str,
        start_date: date,
        end_date: date,
        slot_start: Optional[int] = None,
        slot_end: Optional[int] = None,
        exclusion = None 
    ) -> List[Dict]:
        """
        Fetch 15-min slot data.
        RPC Return: price_rs_per_mwh, scheduled_mw, purchase_bid_mw, sell_bid_mw, mcv_mw
        """
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if slot_start and slot_end:
                    query = "SELECT * FROM public.rpc_get_quarter_prices_range(%s,%s,%s,%s,%s);"
                    params = (market, start_date, end_date, slot_start, slot_end)
                else:
                    query = "SELECT * FROM public.rpc_get_quarter_prices_range(%s,%s,%s,NULL,NULL);"
                    params = (market, start_date, end_date)

                cur.execute(query, params)
                rows = [dict(r) for r in cur.fetchall()]

                cleaned_rows = []
                for r in rows:
                    delivery_date = r.get('delivery_date')
                    
                    # ✅ NEW: Check exclusion
                    if exclusion and delivery_date:
                        if exclusion.should_exclude_date(delivery_date):
                            continue
                    
                    cleaned_rows.append({
                        'delivery_date': delivery_date,
                        'slot_index': r.get('slot_index'),
                        'price_avg': self._safe_float(r.get('price_rs_per_mwh')),
                        'scheduled_mw': self._safe_float(r.get('scheduled_mw')),
                        'purchase_bid_mw': self._safe_float(r.get('purchase_bid_mw')),
                        'sell_bid_mw': self._safe_float(r.get('sell_bid_mw')),
                        'mcv_mw': self._safe_float(r.get('mcv_mw')),
                        'duration_min': 15
                    })
                
                return cleaned_rows

    # ═══════════════════════════════════════════════════════════
    # DERIVATIVES
    # ═══════════════════════════════════════════════════════════

    # core/database.py - UPDATE fetch_derivative_data METHOD

    def fetch_derivative_data(self, trading_date: date) -> tuple[List[Dict], Optional[date]]:
        """
        Fetch derivative market data (fallback to nearest date).
        Returns: (data_rows, actual_trading_date)
        """
        from datetime import datetime, timedelta
        
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    # First check if derivative market exists for this date
                    cur.execute(
                        "SELECT * FROM public.rpc_deriv_daily_with_fallback(%s, %s);",
                        (None, trading_date)
                    )
                    
                    rows = [dict(r) for r in cur.fetchall()]
                    
                    if not rows:
                        # Check if derivative market started (July 2025)
                        deriv_start_date = datetime(2025, 7, 1).date()
                        if trading_date < deriv_start_date:
                            return ([], None)  # Market didn't exist yet
                        else:
                            # Market exists but closed on this day - find most recent trading day
                            for days_back in range(1, 15):  # Look back up to 2 weeks
                                fallback_date = trading_date - timedelta(days=days_back)
                                if fallback_date < deriv_start_date:
                                    return ([], None)
                                
                                cur.execute(
                                    "SELECT * FROM public.rpc_deriv_daily_with_fallback(%s, %s);",
                                    (None, fallback_date)
                                )
                                fallback_rows = [dict(r) for r in cur.fetchall()]
                                if fallback_rows:
                                    # Get actual trading date from first row
                                    actual_date = fallback_rows[0].get('trading_date', fallback_date)
                                    return (fallback_rows, actual_date)
                            
                            return ([], None)  # No data found
                    else:
                        # Get actual trading date from data
                        actual_date = rows[0].get('trading_date', trading_date)
                        return (rows, actual_date)
        
        except Exception as e:
            print(f"⚠️ Error fetching derivatives: {e}")
            return ([], None)
