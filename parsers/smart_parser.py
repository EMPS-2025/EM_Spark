# parsers/smart_parser.py
"""
Intelligent query parser with OpenAI fallback.
Uses deterministic parsing first, then OpenAI for complex queries.
"""

import re
import json
from typing import List, Optional, Dict
from datetime import date, datetime

from openai import OpenAI
from parsers.date_parser import DateParser
from parsers.time_parser import TimeParser
from core.models import QuerySpec
from utils.text_utils import normalize_text


class SmartParser:
    """
    Three-tier parsing strategy:
    1. Simple pattern matching (fast, free)
    2. Rule-based parsing (medium complexity)
    3. OpenAI GPT (complex queries, costs money)
    """
    
    def __init__(self, config):
        self.config = config
        self.date_parser = DateParser()
        self.time_parser = TimeParser()
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
    
    def parse(self, user_query: str) -> List[QuerySpec]:
        """
        Parse user query with intelligent fallback.
        
        Examples it handles:
        - "DAM today"
        - "show me gdam prices for yesterday"
        - "what was the price on 31 oct 2025"
        - "compare dam and gdam for last week"
        - "November 2022, 2023, 2024 comparison"
        """
        normalized = normalize_text(user_query)
        
        # Tier 1: Try simple pattern matching (instant, free)
        specs = self._simple_parse(normalized)
        if specs:
            print("✓ Parsed using simple patterns")
            return specs
        
        # Tier 2: Try rule-based parsing (fast, free)
        specs = self._rule_based_parse(normalized)
        if specs:
            print("✓ Parsed using rule-based logic")
            return specs
        
        # Tier 3: Use OpenAI (slower, costs money, but handles anything)
        if self.openai_client:
            specs = self._openai_parse(user_query)
            if specs:
                print("✓ Parsed using OpenAI GPT")
                return specs
        
        # Failed to parse
        print("✗ Could not parse query")
        return []
    
    # ═══════════════════════════════════════════════════════════
    # Tier 1: Simple Pattern Matching
    # ═══════════════════════════════════════════════════════════
    
    def _simple_parse(self, text: str) -> Optional[List[QuerySpec]]:
        """Handle simple, common queries instantly."""
        lower = text.lower()
        
        # Pattern: "DAM today"
        if re.match(r'^(dam|gdam)\s+(today|yesterday)$', lower):
            market = "GDAM" if "gdam" in lower else "DAM"
            
            if "today" in lower:
                d = date.today()
            else:  # yesterday
                from datetime import timedelta
                d = date.today() - timedelta(days=1)
            
            return [QuerySpec(
                market=market,
                start_date=d,
                end_date=d,
                granularity="hour",
                hours=list(range(1, 25)),
                slots=None,
                stat="twap"
            )]
        
        # Pattern: "GDAM 31 Oct 2025"
        match = re.match(r'^(dam|gdam)\s+(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})$', lower)
        if match:
            market = match.group(1).upper()
            day = int(match.group(2))
            month_name = match.group(3)
            year = int(match.group(4))
            
            months = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4,
                "may": 5, "jun": 6, "jul": 7, "aug": 8,
                "sep": 9, "oct": 10, "nov": 11, "dec": 12
            }
            month = months[month_name]
            
            d = date(year, month, day)
            
            return [QuerySpec(
                market=market,
                start_date=d,
                end_date=d,
                granularity="hour",
                hours=list(range(1, 25)),
                slots=None,
                stat="twap"
            )]
        
        return None
    
    # ═══════════════════════════════════════════════════════════
    # Tier 2: Rule-Based Parsing
    # ═══════════════════════════════════════════════════════════
    
    def _rule_based_parse(self, text: str) -> Optional[List[QuerySpec]]:
        """Use existing parsers with better fallback."""
        
        # Detect market
        market = self._parse_market(text)
        stat = self._parse_stat(text)
        
        # Parse dates
        periods = self.date_parser.parse_periods(text)
        if not periods:
            start, end = self.date_parser.parse_single_range(text)
            if start and end:
                periods = [(start, end)]
        
        if not periods:
            return None
        
        # Parse time ranges
        time_groups = self.time_parser.parse_time_groups(text)
        if not time_groups:
            time_groups = [{"granularity": "hour", "hours": list(range(1, 25)), "slots": None}]
        
        # Build specs
        specs = []
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
        
        return self._deduplicate_specs(specs) if specs else None
    
    # ═══════════════════════════════════════════════════════════
    # Tier 3: OpenAI-Powered Parsing
    # ═══════════════════════════════════════════════════════════
    
    def _openai_parse(self, user_query: str) -> Optional[List[QuerySpec]]:
        """Use OpenAI to understand complex queries."""
        
        if not self.openai_client:
            return None
        
        system_prompt = """You are a query parser for an energy market analysis system.

Parse the user's query and extract:
- market: "DAM" or "GDAM" (default: "DAM")
- start_date: in YYYY-MM-DD format
- end_date: in YYYY-MM-DD format
- granularity: "hour" or "quarter" (default: "hour")
- hours: array of integers 1-24 (if granularity is hour)
- slots: array of integers 1-96 (if granularity is quarter)
- stat: "twap", "vwap", "list", or "daily_avg" (default: "twap")

For comparison queries, return multiple queries in an array.

Examples:
- "DAM today" → {"market": "DAM", "start_date": "2025-11-13", "end_date": "2025-11-13", "granularity": "hour", "hours": [1-24], "stat": "twap"}
- "Compare Nov 2022 and Nov 2023" → [{"start_date": "2022-11-01", "end_date": "2022-11-30", ...}, {"start_date": "2023-11-01", ...}]

Return ONLY valid JSON. No explanations."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Parse this query: {user_query}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Handle single or multiple queries
            if isinstance(data, dict) and "queries" in data:
                queries = data["queries"]
            elif isinstance(data, list):
                queries = data
            else:
                queries = [data]
            
            # Convert to QuerySpec objects
            specs = []
            for q in queries:
                try:
                    spec = QuerySpec(
                        market=q.get("market", "DAM").upper(),
                        start_date=datetime.strptime(q["start_date"], "%Y-%m-%d").date(),
                        end_date=datetime.strptime(q["end_date"], "%Y-%m-%d").date(),
                        granularity=q.get("granularity", "hour"),
                        hours=q.get("hours") or list(range(1, 25)),
                        slots=q.get("slots"),
                        stat=q.get("stat", "twap")
                    )
                    specs.append(spec)
                except Exception as e:
                    print(f"Failed to parse OpenAI response item: {e}")
                    continue
            
            return specs if specs else None
            
        except Exception as e:
            print(f"OpenAI parsing error: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def _parse_market(self, text: str) -> str:
        """Extract market type."""
        if re.search(r'\b(gdam|green\s*day[-\s]*ahead)\b', text, re.I):
            return "GDAM"
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
    
    def _deduplicate_specs(self, specs: List[QuerySpec]) -> List[QuerySpec]:
        """Remove duplicate specifications."""
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


# ═══════════════════════════════════════════════════════════
# Example Usage
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    from core.config import Config
    
    config = Config()
    parser = SmartParser(config)
    
    test_queries = [
        "DAM today",
        "show me gdam prices for yesterday",
        "what was the price on 31 oct 2025",
        "compare dam and gdam for last week",
        "November 2022, 2023, 2024",
        "give me detailed list for 20-50 slots on Oct 12 2024",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        specs = parser.parse(query)
        if specs:
            for spec in specs:
                print(f"  ✓ {spec}")
        else:
            print("  ✗ Failed to parse")