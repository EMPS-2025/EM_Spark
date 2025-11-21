# parsers/bulletproof_parser.py
"""Deterministic query parser that handles every supported phrasing."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import List, Tuple, Optional
from core.models import QuerySpec

from parsers.date_parser import DateParser
from parsers.time_parser import TimeParser
from utils.text_utils import normalize_text
from .query_parser import QueryExclusion

class BulletproofParser:
    """High-confidence parser with layered deterministic fallbacks."""

    def __init__(self, config):
        self.config = config
        self.date_parser = DateParser()
        self.time_parser = TimeParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    
    def parse(self, query: str) -> List[QuerySpec]:
        """Parse user query into one or more QuerySpec objects."""

        if not query or not query.strip():
            return [self._default_spec()]
        
        exclusion = QueryExclusion.parse(query)

        # Remove exclusion clause from query for normal parsing
        clean_query = query
        if exclusion:
            for keyword in ['excluding', 'except', 'without', 'skip', 'ignore', 'not including', 'exclude']:
                if keyword in query.lower():
                    idx = query.lower().find(keyword)
                    clean_query = query[:idx].strip()
                    break

        normalized = normalize_text(query)
        markets = self._extract_markets(normalized)
        stat = self._detect_stat(normalized)
        periods = self._extract_periods(normalized)
        time_groups = self.time_parser.parse_time_groups(normalized)

        if not time_groups:
            time_groups = [
                {"granularity": "hour", "hours": list(range(1, 25)), "slots": None}
            ]

        specs: List[QuerySpec] = []
        for market in markets:
            for start_date, end_date in periods:
                for group in time_groups:
                    specs.append(
                        QuerySpec(
                            market=market,
                            start_date=start_date,
                            end_date=end_date,
                            granularity=group["granularity"],
                            hours=group.get("hours"),
                            slots=group.get("slots"),
                            stat=stat,
                            exclusion=exclusion
                        )
                    )

        return self._deduplicate(specs) if specs else [self._default_spec()]

    # ------------------------------------------------------------------
    # Component extractors
    # ------------------------------------------------------------------
    def _extract_markets(self, text: str) -> List[str]:
        """Return ordered list of markets mentioned in the query."""

        locations: List[Tuple[int, str]] = []
        patterns = [
            (r"\brtm\b|real\s*time", "RTM"),
            (r"\bgdam\b|green\s*day", "GDAM"),
            (r"\bdam\b|day\s*-?ahead", "DAM"),
        ]

        for pattern, label in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                locations.append((match.start(), label))

        locations.sort(key=lambda item: item[0])
        ordered = [label for _, label in locations]
        return ordered or ["DAM"]

    def _detect_stat(self, text: str) -> str:
        """Infer statistic type requested by the user."""

        lower = text.lower()
        if re.search(r"\b(vwap|weighted)\b", lower):
            return "vwap"
        if re.search(r"\bdaily\s+(avg|average)\b", lower):
            return "daily_avg"
        if re.search(r"\b(list|table|rows|detailed)\b", lower):
            return "list"
        if re.search(r"\b(avg|average|mean|twap)\b", lower):
            return "twap"

        return getattr(self.config, "DEFAULT_STAT", "twap")

    def _extract_periods(self, text: str) -> List[Tuple[date, date]]:
        """Extract one or many date periods from the query."""

        start, end = self.date_parser.parse_single_range(text)
        if start and end:
            return [(start, end)]
        
        # 2. Try multi-period lists (e.g., "Nov 2022, Nov 2023")
        periods = self.date_parser.parse_periods(text)
        if periods:
            return periods
        
        # 3. Fallback: Loose extraction (dangerous but sometimes needed)
        periods = self._extract_loose_dates(text)
        if periods:
            return periods
        
        # periods = self.date_parser.parse_periods(text)
        # if not periods:
        #     start, end = self.date_parser.parse_single_range(text)
        #     if start and end:
        #         periods = [(start, end)]

        # if not periods:
        #     periods = self._extract_loose_dates(text)

        # 4. Default to today
        today = date.today()
        return [(today, today)]

        # if not periods:
        #     today = date.today()
        #     periods = [(today, today)]

        # return periods

    def _extract_loose_dates(self, text: str) -> List[Tuple[date, date]]:
        """Fallback: find every standalone '14 Nov 2025' like token."""

        matches = re.findall(
            r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(\d{2,4})\b",
            text,
            flags=re.I,
        )
        
        periods: List[Tuple[date, date]] = []
        for day_str, month_str, year_str in matches:

            try:
                month = DateParser.MONTHS[month_str.lower()[:3]]
                year = self._normalize_year(year_str)
                day = int(day_str)
                periods.append((date(year, month, day), date(year, month, day)))
            except Exception:
                continue

        if periods:
            return periods

        # Handle "Nov 2024, Nov 2025" style without explicit ranges.
        month_year = re.findall(
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(\d{4})\b",
            text,
            flags=re.I,
        )

        for month_str, year_str in month_year:
            try:
                month = DateParser.MONTHS[month_str.lower()[:3]]
                year = int(year_str)
                start = date(year, month, 1)
                
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                end = date(year, month, last_day)
                
                periods.append((start, end))
            except Exception:
                continue

        return periods

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _deduplicate(self, specs: List[QuerySpec]) -> List[QuerySpec]:
        seen = set()
        unique: List[QuerySpec] = []

        for spec in specs:
            key = (
                spec.market,
                spec.start_date,
                spec.end_date,
                spec.granularity,
                tuple(spec.hours or []),
                tuple(spec.slots or []),
                spec.stat,
            )
            if key not in seen:
                seen.add(key)
                unique.append(spec)

        return unique
    
    def _default_spec(self) -> QuerySpec:
        today = date.today()
        return QuerySpec(
            market="DAM",
            start_date=today,
            end_date=today,
            granularity="hour",
            hours=list(range(1, 25)),
            slots=None,
            stat="twap"
        )
    
    @staticmethod
    def _normalize_year(year_str: str) -> int:
        year = int(year_str)
        if year < 100:
            year += 2000
        return year


# ═══════════════════════════════════════════════════════════════
# Test the parser
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Quick smoke test
    class _Cfg:
        DEFAULT_STAT = "twap"

    parser = BulletproofParser(_Cfg())
    tests = [
        "DAM rate for 14 Nov 2025",
        "GDAM 6-8 and 12-14 hours for 31/10/2025",
        "RTM 20-50 slots on 31 Oct 2025",
        "Compare DAM and GDAM for Nov 2022, 2023, 2024",
        "RTM yesterday",
        "Prices between 12 Nov 2024 to 15 Nov 2024 8-9 hrs",
    ]
    
    for q in tests:
        print(q)
        for spec in parser.parse(q):
            print("  ", spec)