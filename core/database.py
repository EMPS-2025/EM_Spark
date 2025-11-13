# core/database.py
"""Database connection management."""
import os
import psycopg2
import psycopg2.extras
from typing import List, Dict, Optional
from datetime import date


class DatabaseManager:
    """Manages database connections and queries."""
    
    def __init__(self, config=None):
        # prefer the .env URL (Supabase)
        dsn = os.getenv("DATABASE_URL", "").strip()
        if not dsn:
            # fall back to whatever your old config was
            raise RuntimeError("DATABASE_URL is not set in .env")
        self.dsn = dsn
    
    def _connect(self):
        return psycopg2.connect(self.dsn, sslmode="require")
    
    # ═══════════════════════════════════════════════════════════
    # DAM/GDAM Queries
    # ═══════════════════════════════════════════════════════════
    
    def fetch_hourly(
        self,
        market: str,
        start_date: date,
        end_date: date,
        block_start: Optional[int] = None,
        block_end: Optional[int] = None
    ) -> List[Dict]:
        """Fetch hourly price data."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if block_start and block_end:
                    cur.execute(
                        "SELECT * FROM public.rpc_get_hourly_prices_range(%s,%s,%s,%s,%s);",
                        (market, start_date, end_date, block_start, block_end)
                    )
                else:
                    cur.execute(
                        "SELECT * FROM public.rpc_get_hourly_prices_range(%s,%s,%s,NULL,NULL);",
                        (market, start_date, end_date)
                    )
                return [dict(r) for r in cur.fetchall()]
    
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
                        "SELECT * FROM public.rpc_get_quarter_prices_range(%s,%s,%s,%s,%s);",
                        (market, start_date, end_date, slot_start, slot_end)
                    )
                else:
                    cur.execute(
                        "SELECT * FROM public.rpc_get_quarter_prices_range(%s,%s,%s,NULL,NULL);",
                        (market, start_date, end_date)
                    )
                return [dict(r) for r in cur.fetchall()]
    
    # ═══════════════════════════════════════════════════════════
    # Derivative Queries
    # ═══════════════════════════════════════════════════════════
    
    def fetch_deriv_daily_fallback(
        self,
        target_day: date,
        exchange: Optional[str] = None
    ) -> List[Dict]:
        """Fetch derivative daily close with fallback to nearest prior trading day."""
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
        """Fetch derivative expiry data for a contract month."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    "SELECT * FROM public.rpc_deriv_expiry_for_month(%s,%s);",
                    (exchange, contract_month_first)
                )
                return [dict(r) for r in cur.fetchall()]
