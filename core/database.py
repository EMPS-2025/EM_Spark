# core/database.py - FIXED with correct field names
"""Database connection management with proper bid/ask field handling."""
import os
import psycopg2
import psycopg2.extras
from typing import List, Dict, Optional
from datetime import date

BID_FIELD_KEYWORDS = ("purchase_bid", "sell_bid", "buy_bid", "sell_offer")


def _as_float(value):
    """Best-effort conversion for text columns (e.g. *_txt)."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return 0.0
        for token in (",", "₹", "rs", "RS", "Rs", "MW", "mw", "kWh", "MWh"):
            cleaned = cleaned.replace(token, "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_bid_fields(row: Dict) -> None:
    """Ensure any bid/offer related fields are safe floats."""
    for key, value in list(row.items()):
        key_lower = str(key).lower()
        if not any(token in key_lower for token in BID_FIELD_KEYWORDS):
            continue
        try:
            row[key] = _as_float(value)
        except (TypeError, ValueError):
            row[key] = 0.0


class DatabaseManager:
    """Manages database connections and queries."""
    
    def __init__(self, config=None):
        dsn = os.getenv("DATABASE_URL", "").strip()
        if not dsn:
            raise RuntimeError("DATABASE_URL is not set in .env")
        self.dsn = dsn
    
    def _connect(self):
        return psycopg2.connect(self.dsn, sslmode="require")
    
    # ═══════════════════════════════════════════════════════════
    # DAM/GDAM/RTM Queries - FIXED
    # ═══════════════════════════════════════════════════════════
    
    def fetch_hourly(
        self,
        market: str,
        start_date: date,
        end_date: date,
        block_start: Optional[int] = None,
        block_end: Optional[int] = None
    ) -> List[Dict]:
        """Fetch hourly price data with correct aggregations."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if block_start and block_end:
                    cur.execute(
                        """
                        SELECT * FROM public.rpc_get_hourly_prices_range(%s,%s,%s,%s,%s);
                        """,
                        (market, start_date, end_date, block_start, block_end)
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM public.rpc_get_hourly_prices_range(%s,%s,%s,NULL,NULL);
                        """,
                        (market, start_date, end_date)
                    )
                
                rows = [dict(r) for r in cur.fetchall()]
                
                # DEBUG: Print first row to verify fields
                if rows:
                    print(f"✓ Fetched {len(rows)} hourly rows for {market}")
                    print(f"  Sample: Price={rows[0].get('price_avg_rs_per_mwh')}, "
                          f"Scheduled={rows[0].get('scheduled_mw_sum')}, "
                          f"PurchaseBid={rows[0].get('purchase_bid_avg')}, "
                          f"SellBid={rows[0].get('sell_bid_avg')}")
                    bid_keys = [
                        str(k)
                        for k in rows[0].keys()
                        if any(token in str(k).lower() for token in BID_FIELD_KEYWORDS)
                    ]
                    if bid_keys:
                        print(f"  Bid fields present: {', '.join(sorted(bid_keys))}")
                else:
                    print(f"⚠️  No hourly data found for {market} on {start_date}")
                
                # Ensure numeric fields with correct names
                for row in rows:
                    row['price_avg_rs_per_mwh'] = _as_float(
                        row.get('price_avg_rs_per_mwh', row.get('mcp_rs_per_mwh', 0))
                    )
                    row['scheduled_mw_sum'] = _as_float(
                        row.get('scheduled_mw_sum', row.get('scheduled_mw_txt', row.get('scheduled_mw', 0)))
                    )
                    row['duration_min'] = int(row.get('duration_min', 60) or 60)
                    row['purchase_bid_avg'] = _as_float(row.get('purchase_bid_avg'))
                    row['sell_bid_avg'] = _as_float(row.get('sell_bid_avg'))
                    row['mcv_sum'] = _as_float(row.get('mcv_sum', row.get('mcv_txt', 0)))
                    for alias in ('purchase_bid_txt', 'sell_bid_txt', 'mcv_txt'):
                        if alias in row:
                            row[alias] = _as_float(row[alias])
                    _coerce_bid_fields(row)
                
                return rows
    
    def fetch_quarter(
        self,
        market: str,
        start_date: date,
        end_date: date,
        slot_start: Optional[int] = None,
        slot_end: Optional[int] = None
    ) -> List[Dict]:
        """Fetch 15-minute slot price data."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if slot_start and slot_end:
                    cur.execute(
                        """
                        SELECT * FROM public.rpc_get_quarter_prices_range(%s,%s,%s,%s,%s);
                        """,
                        (market, start_date, end_date, slot_start, slot_end)
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM public.rpc_get_quarter_prices_range(%s,%s,%s,NULL,NULL);
                        """,
                        (market, start_date, end_date)
                    )
                
                rows = [dict(r) for r in cur.fetchall()]
                
                # DEBUG
                if rows:
                    print(f"✓ Fetched {len(rows)} quarter rows for {market}")
                else:
                    print(f"⚠️  No quarter data found for {market} on {start_date}")
                
                # Ensure numeric fields
                for row in rows:
                    row['price_rs_per_mwh'] = _as_float(
                        row.get('price_rs_per_mwh', row.get('mcp_rs_per_mwh', 0))
                    )
                    row['scheduled_mw'] = _as_float(row.get('scheduled_mw', row.get('scheduled_mw_txt', 0)))
                    row['duration_min'] = int(row.get('duration_min', 15) or 15)
                    row['purchase_bid'] = _as_float(row.get('purchase_bid', row.get('purchase_bid_txt', 0)))
                    row['sell_bid'] = _as_float(row.get('sell_bid', row.get('sell_bid_txt', 0)))
                    row['mcv'] = _as_float(row.get('mcv', row.get('mcv_txt', 0)))
                    _coerce_bid_fields(row)
                
                return rows
            
    def fetch_derivative_data(self, trading_date: date) -> List[Dict]:
        """Fetch derivative market data"""
        try:
            rows = self.fetch_deriv_daily_fallback(trading_date, exchange)
            return rows if rows else []
        except Exception as e:
            print(f"Error fetching derivative data: {e}")
            return []

    
    # ═══════════════════════════════════════════════════════════
    # Derivative Queries
    # ═══════════════════════════════════════════════════════════
    
    def fetch_deriv_daily_fallback(
        self,
        target_day: date,
        exchange: Optional[str] = None
    ) -> List[Dict]:
        """Fetch derivative daily close with fallback."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    "SELECT * FROM public.rpc_deriv_daily_with_fallback(%s,%s);",
                    (exchange, target_day)
                )
                return [dict(r) for r in cur.fetchall()]
    
    def fetch_deriv_month_expiry(
        self,
        contract_month_first: date,
        exchange: Optional[str] = None
    ) -> List[Dict]:
        """Fetch derivative expiry data."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    "SELECT * FROM public.rpc_deriv_expiry_for_month(%s,%s);",
                    (exchange, contract_month_first)
                )
                return [dict(r) for r in cur.fetchall()]