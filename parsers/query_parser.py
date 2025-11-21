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
# NEW: Advanced Day Exclusion Support
# ════════════════════════════════════════════════════════════════════════

@dataclass
class QueryExclusion:
    """Represents exclusions (days, specific dates, or months) in a query."""
    excluded_days: Set[int] = None      # 0=Monday, 6=Sunday
    excluded_dates: Set[date] = None    # Specific dates (e.g. 25 Dec 2025)
    excluded_months: Set[int] = None    # Specific months (1-12)
    exclusion_text: str = ""            # Original exclusion text
    
    def __post_init__(self):
        if self.excluded_days is None: self.excluded_days = set()
        if self.excluded_dates is None: self.excluded_dates = set()
        if self.excluded_months is None: self.excluded_months = set()

    @staticmethod
    def parse(query: str) -> Optional['QueryExclusion']:
        """
        Parse exclusion clauses from query.
        
        Examples:
            - "excluding Sunday" -> {6}
            - "excluding 25 Dec 2025" -> {date(2025, 12, 25)}
            - "excluding Feb, May" -> months {2, 5}
            - "without Monday and 15 Aug 2025"
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
                idx = query_lower.find(keyword)
                # Ensure word boundary check so we don't match inside words
                if idx == 0 or not query_lower[idx-1].isalnum():
                    exclusion_start = idx
                    keyword_used = keyword
                    break
        
        if exclusion_start == -1:
            return None
        
        # Extract exclusion clause (everything after keyword)
        exclusion_clause = query[exclusion_start + len(keyword_used):].strip()
        clean_clause = exclusion_clause.lower() # for day/month matching
        
        # --- 1. Parse Specific Dates (25 Dec 2025) ---
        # Use a simplified version of DateParser logic for the exclusion clause
        excluded_dates = set()
        
        # Regex for "DD Mon YYYY" or "DD Mon" inside exclusion text
        date_matches = re.finditer(
            r'\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(\d{4})?\b', 
            clean_clause
        )
        
        parsed_date_substrs = []
        
        months_map = DateParser.MONTHS
        today_year = date.today().year
        
        for m in date_matches:
            try:
                d = int(m.group(1))
                mon_str = m.group(2)
                y = int(m.group(3)) if m.group(3) else today_year
                if mon_str in months_map:
                    excluded_dates.add(date(y, months_map[mon_str], d))
                    parsed_date_substrs.append(m.span()) # Record position to remove later
            except ValueError:
                pass
        
        # --- 2. Parse Months (Feb, May) ---
        excluded_months = set()
        # Only match months if they weren't part of a full date
        month_matches = re.finditer(
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b', 
            clean_clause
        )
        
        for m in month_matches:
            # Check if this match was part of a date we already parsed
            is_part_of_date = any(start <= m.start() and end >= m.end() for start, end in parsed_date_substrs)
            if not is_part_of_date:
                mon_str = m.group(1)
                if mon_str in months_map:
                    excluded_months.add(months_map[mon_str])

        # --- 3. Parse Days of Week (Sunday, Mon) ---
        excluded_days = set()
        
        # Special case: weekends
        if 'weekend' in clean_clause or 'sat and sun' in clean_clause:
            excluded_days.add(5)
            excluded_days.add(6)
        
        # Special case: weekdays
        if 'weekday' in clean_clause or 'working day' in clean_clause:
            excluded_days.update({0, 1, 2, 3, 4})
        
        day_mapping = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        # Tokenize and check
        # Replace commas with spaces
        tokens = clean_clause.replace(',', ' ').split()
        for token in tokens:
            # singularize
            t_sing = token.rstrip('s')
            if t_sing in day_mapping:
                excluded_days.add(day_mapping[t_sing])
        
        if not (excluded_days or excluded_dates or excluded_months):
            return None
            
        return QueryExclusion(
            excluded_days=excluded_days,
            excluded_dates=excluded_dates,
            excluded_months=excluded_months,
            exclusion_text=exclusion_clause
        )
    
    def should_exclude_date(self, check_date: date) -> bool:
        """Check if a specific date should be excluded."""
        # 1. Check Specific Date
        if check_date in self.excluded_dates:
            return True
            
        # 2. Check Month
        if check_date.month in self.excluded_months:
            return True
            
        # 3. Check Day of Week
        if check_date.weekday() in self.excluded_days:
            return True
            
        return False
    
    def get_excluded_day_names(self) -> List[str]:
        """Get human-readable names of exclusions."""
        labels = []
        
        # Days
        if self.excluded_days:
            if self.excluded_days == {5, 6}:
                labels.append("Weekends")
            else:
                day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                labels.extend([day_names[d] for d in sorted(self.excluded_days)])
        
        # Months
        if self.excluded_months:
            month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            labels.extend([month_names[m] for m in sorted(self.excluded_months)])
            
        # Dates
        if self.excluded_dates:
            labels.extend([d.strftime("%d %b") for d in sorted(list(self.excluded_dates))[:3]])
            if len(self.excluded_dates) > 3:
                labels.append(f"+{len(self.excluded_dates)-3} dates")
                
        return labels


class QueryParser:
    """
    Main query parser that orchestrates all parsing strategies.
    """
    
    def __init__(self, config):
        self.config = config
        self.date_parser = DateParser()
        self.time_parser = TimeParser()
        #self.llm_parser = LLMParser(config) if config.OPENAI_API_KEY else None
    
    def parse(self, user_query: str) -> List[QuerySpec]:
        """
        Parse user query into structured QuerySpec objects.
        """
        normalized = normalize_text(user_query)
        
        # 0. Parse Exclusions First
        exclusion = QueryExclusion.parse(user_query)
        
        # 1. Detect market type
        market = self._parse_market(normalized)
        
        # 2. Detect statistic type
        stat = self._parse_stat(normalized)
        
        # 3. Parse date periods
        periods = self.date_parser.parse_periods(normalized)
        if not periods:
            start, end = self.date_parser.parse_single_range(normalized)
            if start and end:
                periods = [(start, end)]
        
        # 4. Parse time blocks/slots
        time_groups = self.time_parser.parse_time_groups(normalized)
        
        # 5. Build QuerySpec objects
        specs = self._build_specs(market, stat, periods, time_groups, exclusion)
        
        # 7. Deduplicate identical specs
        return self._deduplicate(specs)
    
    def _parse_market(self, text: str) -> str:
        """Extract market type (DAM or GDAM)."""
        if re.search(r'\b(gdam|green\s*day[-\s]*ahead)\b', text, re.I):
            return "GDAM"
        if re.search(r'\b(rtm|real[-\s]*time)\b', text, re.I):
            return "RTM"
        return "DAM"
    
    def _parse_stat(self, text: str) -> str:
        """Extract statistic type."""
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
        time_groups: List[dict],
        exclusion: Optional[QueryExclusion]
    ) -> List[QuerySpec]:
        """Build QuerySpec objects."""
        specs = []
        
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
                    stat=stat,
                    exclusion=exclusion  # Pass the exclusion object here
                )
                specs.append(spec)
        
        return specs
    
    def _deduplicate(self, specs: List[QuerySpec]) -> List[QuerySpec]:
        """Remove duplicate query specifications."""
        seen = set()
        unique = []
        
        for spec in specs:
            # Note: excluded days aren't part of hashable key usually, 
            # but effectively same query params mean duplicates
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