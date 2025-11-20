# parsers/query_parser.py
"""
Unified query parser that handles all date/time/market parsing.
Supports flexible natural language input.
"""

import re
from typing import List, Optional, Tuple, Set
from datetime import date
from dataclasses import dataclass

from parsers.date_parser import DateParser
from parsers.time_parser import TimeParser
#from parsers.llm_parser import LLMParser
from core.models import QuerySpec
from utils.text_utils import normalize_text


# ════════════════════════════════════════════════════════════════════════
# NEW: Day Exclusion Support
# ════════════════════════════════════════════════════════════════════════

@dataclass
class QueryExclusion:
    """Represents day exclusions in a query."""
    excluded_days: Set[int]  # 0=Monday, 6=Sunday (Python weekday())
    exclusion_text: str      # Original exclusion text
    
    @staticmethod
    def parse(query: str) -> Optional['QueryExclusion']:
        """
        Parse exclusion clauses from query.
        
        Examples:
            - "excluding Sunday" -> {6}
            - "except weekends" -> {5, 6}
            - "without Monday and Friday" -> {0, 4}
        """
        query_lower = query.lower()
        
        # Check for exclusion keywords
        exclusion_keywords = [
            'excluding', 'except', 'without', 
            'skip', 'ignore', 'not including', 'exclude'
        ]
        
        exclusion_start = -1
        keyword_used = None
        
        for keyword in exclusion_keywords:
            if keyword in query_lower:
                exclusion_start = query_lower.find(keyword)
                keyword_used = keyword
                break
        
        if exclusion_start == -1:
            return None
        
        # Extract exclusion clause (everything after keyword)
        exclusion_clause = query[exclusion_start + len(keyword_used):].strip()
        
        # Map day names to weekday numbers
        day_mapping = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        # Special case: weekends
        weekend_keywords = ['weekend', 'weekends', 'sat and sun', 'saturday and sunday']
        for weekend_kw in weekend_keywords:
            if weekend_kw in exclusion_clause.lower():
                return QueryExclusion(
                    excluded_days={5, 6},
                    exclusion_text=exclusion_clause
                )
        
        # Special case: weekdays
        weekday_keywords = ['weekday', 'weekdays', 'working days']
        for weekday_kw in weekday_keywords:
            if weekday_kw in exclusion_clause.lower():
                return QueryExclusion(
                    excluded_days={0, 1, 2, 3, 4},
                    exclusion_text=exclusion_clause
                )
        
        # Parse individual day names
        excluded_days = set()
        words = exclusion_clause.lower().replace(',', ' ').split()
        
        for word in words:
            # Remove 's' from plural (Sundays -> Sunday)
            word_singular = word.rstrip('s')
            
            if word_singular in day_mapping:
                excluded_days.add(day_mapping[word_singular])
        
        if excluded_days:
            return QueryExclusion(
                excluded_days=excluded_days,
                exclusion_text=exclusion_clause
            )
        
        return None
    
    def should_exclude_date(self, check_date: date) -> bool:
        """Check if a specific date should be excluded."""
        return check_date.weekday() in self.excluded_days
    
    def get_excluded_day_names(self) -> List[str]:
        """Get human-readable names of excluded days."""
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return [day_names[day] for day in sorted(self.excluded_days)]


class QueryParser:
    """
    Main query parser that orchestrates all parsing strategies.
    Tries deterministic parsing first, falls back to LLM if needed.
    """
    
    def __init__(self, config):
        self.config = config
        self.date_parser = DateParser()
        self.time_parser = TimeParser()
        self.llm_parser = LLMParser(config) if config.OPENAI_API_KEY else None
    
    def parse(self, user_query: str) -> List[QuerySpec]:
        """
        Parse user query into structured QuerySpec objects.
        
        Examples:
            "DAM 20-50 slots on Oct 12, 2024 to Nov 12, 2024"
            "Compare Nov 2022, Nov 2023, Nov 2024"
            "GDAM yesterday 6-8 hours"
        """
        normalized = normalize_text(user_query)
        
        # 1. Detect market type
        market = self._parse_market(normalized)
        
        # 2. Detect statistic type
        stat = self._parse_stat(normalized)
        
        # 3. Parse date periods (handles multi-year comparisons)
        periods = self.date_parser.parse_periods(normalized)
        if not periods:
            # Fallback: try single date/range
            start, end = self.date_parser.parse_single_range(normalized)
            if start and end:
                periods = [(start, end)]
        
        # 4. Parse time blocks/slots (handles explicit groups like "6-8 and 12-14")
        time_groups = self.time_parser.parse_time_groups(normalized)
        
        # 5. Build QuerySpec objects
        specs = self._build_specs(market, stat, periods, time_groups)
        
        # 6. LLM fallback if deterministic parsing failed
        if not specs and self.llm_parser:
            specs = self.llm_parser.parse(user_query)
        
        # 7. Deduplicate identical specs
        return self._deduplicate(specs)
    
    def _parse_market(self, text: str) -> str:
        """Extract market type (DAM or GDAM)."""
        if re.search(r'\b(gdam|green\s*day[-\s]*ahead)\b', text, re.I):
            return "GDAM"
        return "DAM"
    
    def _parse_stat(self, text: str) -> str:
        """Extract statistic type (twap, vwap, list, daily_avg)."""
        lower = text.lower()
        
        if re.search(r'\b(vwap|weighted)\b', lower):
            return "vwap"
        if re.search(r'\bdaily\s+(avg|average)\b', lower):
            return "daily_avg"
        if re.search(r'\b(list|table|rows|detailed)\b', lower):
            return "list"
        if re.search(r'\b(avg|average|mean|twap)\b', lower):
            return "twap"
        
        return self.config.DEFAULT_STAT
    
    def _build_specs(
        self,
        market: str,
        stat: str,
        periods: List[Tuple[date, date]],
        time_groups: List[dict]
    ) -> List[QuerySpec]:
        """Build QuerySpec objects from parsed components."""
        specs = []
        
        # If no explicit time groups, use full day
        if not time_groups:
            time_groups = [{"granularity": "hour", "hours": list(range(1, 25)), "slots": None}]
        
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
        
        return specs
    
    def _deduplicate(self, specs: List[QuerySpec]) -> List[QuerySpec]:
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
# EXAMPLE USAGE
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test cases
    test_queries = [
        "DAM 20-50 slots on October 12, 2024 to November 12, 2024",
        "Compare November 2022, November 2023, November 2024",
        "GDAM yesterday 6-8 hours",
        "Show prices for 10-15 Aug 2025",
        "DAM for 6-8 and 12-14 from 25 Aug to 24 Dec 2024"
    ]
    
    parser = QueryParser(config=None)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        specs = parser.parse(query)
        for spec in specs:
            print(f"  → {spec}")
