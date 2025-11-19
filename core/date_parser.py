# parsers/date_parser.py
"""
Robust date parsing that handles:
- Single dates: "31 Oct 2025", "yesterday", "today"
- Date ranges: "10-15 Aug 2025", "Jan 2024 to Feb 2024"
- Multi-year months: "November 2022, 2023, 2024"
- Numeric formats: "31/10/2025", "10-15/08/2025"
"""

import re
import calendar
from datetime import date, timedelta
from typing import List, Tuple, Optional


class DateParser:
    """Intelligent date parser with multiple strategies."""
    
    # Month name mapping
    MONTHS = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12
    }
    
    MONTH_PATTERN = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)"
    
    DATE_MIN = date(2010, 1, 1)  # Minimum valid date
    
    def parse_periods(self, text: str) -> List[Tuple[date, date]]:
        """
        Parse multi-period queries like:
        - "November 2022, November 2023, November 2024"
        - "Nov 2022, 2023, and 2024"
        """
        results = []
        lower = text.lower()
        
        # Strategy 1: "Month YYYY, YYYY, YYYY" pattern
        month_match = re.search(
            rf'\b({self.MONTH_PATTERN})\s+(\d{{4}})\b(?:\s*,\s*(?:and\s+)?(\d{{4}}))+',
            lower,
            re.I
        )
        
        if month_match:
            month_name = month_match.group(1)
            if month_name in self.MONTHS:
                month_num = self.MONTHS[month_name]
                full_match = month_match.group(0)
                years = re.findall(r'\b\d{4}\b', full_match)
                
                for year_str in years:
                    try:
                        year = int(year_str)
                        if 2000 <= year <= 2100:
                            start = date(year, month_num, 1)
                            last_day = calendar.monthrange(year, month_num)[1]
                            end = date(year, month_num, last_day)
                            results.append((start, end))
                    except (ValueError, calendar.IllegalMonthError):
                        continue
                
                if len(results) > 1:
                    return results
        
        # Strategy 2: "Month YYYY, Month YYYY, Month YYYY" pattern
        pattern = rf'\b({self.MONTH_PATTERN})\s+(\d{{4}})\b'
        match_iter = list(re.finditer(pattern, lower, re.I))

        if len(match_iter) > 1:
            seen = set()
            for match in match_iter:
                month_name = match.group(1)
                year_str = match.group(2)
                if month_name in self.MONTHS:
                    try:
                        year = int(year_str)
                        month_num = self.MONTHS[month_name]
                        
                        if 2000 <= year <= 2100:
                            key = (year, month_num)
                            if key not in seen:
                                seen.add(key)
                                start = date(year, month_num, 1)
                                last_day = calendar.monthrange(year, month_num)[1]
                                end = date(year, month_num, last_day)
                                results.append((start, end))
                    except (ValueError, calendar.IllegalMonthError):
                        continue
            
            if len(results) > 1:
                return results
        
        return []
    
    def parse_single_range(self, text: str) -> Tuple[Optional[date], Optional[date]]:
        """Parse a single date or date range."""
        lower = " " + text.lower().strip() + " "
        today = date.today()
        
        # Relative dates
        if " yesterday " in lower:
            d = today - timedelta(days=1)
            return (d, d)
        
        if " today " in lower:
            return (today, today)
        
        if " this month " in lower:
            start = date(today.year, today.month, 1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            end = date(today.year, today.month, last_day)
            return (start, end)
        
        if " last month " in lower:
            year, month = today.year, today.month - 1
            if month == 0:
                year, month = year - 1, 12
            start = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end = date(year, month, last_day)
            return (start, end)
        
        # Try various date patterns
        patterns = [
            self._parse_day_month_to_day_month_year,
            self._parse_day_month_year_range,
            self._parse_month_to_month_range,
            self._parse_day_range_same_month,
            self._parse_numeric_range,
            self._parse_single_numeric_date,
            self._parse_single_day_month,
            self._parse_month_year,
            self._parse_year_only
        ]
        
        for parser_func in patterns:
            try:
                result = parser_func(lower, today)
                if result[0] and result[1]:
                    return result
            except Exception:
                continue
        
        return (None, None)
    
    def _parse_day_month_to_day_month_year(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """24 September to 24 October 2025"""
        m = re.search(
            rf'(?:from\s+)?(\d{{1,2}})\s+({self.MONTH_PATTERN})\s+(?:to|until|till|-)\s+(\d{{1,2}})\s+({self.MONTH_PATTERN})\s+(\d{{2,4}})',
            text, re.I
        )
        if m:
            d1 = int(m.group(1))
            mon1 = self.MONTHS[m.group(2)]
            d2 = int(m.group(3))
            mon2 = self.MONTHS[m.group(4)]
            year = int(m.group(5))
            if year < 100:
                year += 2000
            
            start = date(year, mon1, d1)
            end = date(year, mon2, d2)
            if start > end:
                start, end = end, start
            return (start, end)
        return (None, None)
    
    def _parse_day_month_year_range(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """1 Jan 2024 to 15 Feb 2024"""
        m = re.search(
            rf'\b(?:from\s*)?(\d{{1,2}})\s+{self.MONTH_PATTERN}\s+(\d{{2,4}})\s*(?:to|-)\s*(\d{{1,2}})\s+{self.MONTH_PATTERN}\s+(\d{{2,4}})\b',
            text, re.I
        )
        if m:
            d1 = int(m.group(1))
            mon1 = self.MONTHS[m.group(2)]
            y1 = int(m.group(3))
            d2 = int(m.group(4))
            mon2 = self.MONTHS[m.group(5)]
            y2 = int(m.group(6))
            
            if y1 < 100:
                y1 += 2000
            if y2 < 100:
                y2 += 2000
            
            start = date(y1, mon1, d1)
            end = date(y2, mon2, d2)
            if start > end:
                start, end = end, start
            return (start, end)
        return (None, None)
    
    def _parse_day_range_same_month(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """10-15 Aug 2025"""
        m = re.search(
            rf'\b(\d{{1,2}})\s*(?:to|-)\s*(\d{{1,2}})\s+{self.MONTH_PATTERN}(?:\s+(\d{{2,4}}))?\b',
            text, re.I
        )
        if m:
            d1, d2 = int(m.group(1)), int(m.group(2))
            mon = self.MONTHS[m.group(3)]
            year = int(m.group(4)) if m.group(4) else today.year
            if year < 100:
                year += 2000
            
            return (date(year, mon, min(d1, d2)), date(year, mon, max(d1, d2)))
        return (None, None)
    def _parse_month_to_month_range(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """Nov 2024 to Feb 2025"""

        m = re.search(
            rf'(?:from\s+)?{self.MONTH_PATTERN}\s+(\d{{2,4}})\s*(?:to|-)\s*{self.MONTH_PATTERN}\s+(\d{{2,4}})',
            text,
            re.I,
        )

        if m:
            mon1 = self.MONTHS[m.group(1)]
            year1 = int(m.group(2))
            mon2 = self.MONTHS[m.group(3)]
            year2 = int(m.group(4))

            if year1 < 100:
                year1 += 2000
            if year2 < 100:
                year2 += 2000

            start_key = (year1, mon1)
            end_key = (year2, mon2)

            if start_key <= end_key:
                start_year, start_mon = start_key
                end_year, end_mon = end_key
            else:
                start_year, start_mon = end_key
                end_year, end_mon = start_key

            start = date(start_year, start_mon, 1)
            last_day = calendar.monthrange(end_year, end_mon)[1]
            end = date(end_year, end_mon, last_day)

            return (start, end)

        return (None, None)
    
    def _normalize_year(self, year_str: Optional[str]) -> Optional[int]:
        if not year_str:
            return None
        try:
            year = int(year_str)
            if year < 100:
                year += 2000
            return year
        except ValueError:
            return None
    
    def _parse_numeric_range(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """31/10/2025 to 15/11/2025"""
        m = re.search(
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\s*(?:to|-)\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',
            text
        )
        if m:
            d1, m1, y1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
            d2, m2, y2 = int(m.group(4)), int(m.group(5)), int(m.group(6))
            y1 = y1 + 2000 if y1 < 100 else y1
            y2 = y2 + 2000 if y2 < 100 else y2
            
            start = date(y1, m1, d1)
            end = date(y2, m2, d2)
            if start > end:
                start, end = end, start
            return (start, end)
        return (None, None)
    
    def _parse_single_numeric_date(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """31/10/2025"""
        m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', text)
        if m:
            d0, m0, y0 = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if y0 < 100:
                y0 += 2000
            d = date(y0, m0, d0)
            if d >= self.DATE_MIN:
                return (d, d)
        return (None, None)
    
    def _parse_single_day_month(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """31 Oct or 31 Oct 2025"""
        m = re.search(rf'\b(\d{{1,2}})\s+{self.MONTH_PATTERN}(?:\s+(\d{{2,4}}))?\b', text, re.I)
        if m:
            d0 = int(m.group(1))
            mon0 = self.MONTHS[m.group(2)]
            y0 = int(m.group(3)) if m.group(3) else today.year
            if y0 < 100:
                y0 += 2000
            d = date(y0, mon0, d0)
            if d >= self.DATE_MIN:
                return (d, d)
        return (None, None)
    
    def _parse_month_year(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """Oct 2025"""
        m = re.search(rf'\b{self.MONTH_PATTERN}\s+(\d{{2,4}})\b', text, re.I)
        if m:
            mon = self.MONTHS[m.group(1)]
            year = int(m.group(2))
            year = year + 2000 if year < 100 else year
            last_day = calendar.monthrange(year, mon)[1]
            start = date(year, mon, 1)
            end = date(year, mon, last_day)
            if start >= self.DATE_MIN:
                return (start, end)
        return (None, None)
    
    def _parse_year_only(self, text: str, today: date) -> Tuple[Optional[date], Optional[date]]:
        """2024 (if context suggests full year)"""
        m = re.search(r'\b(20\d{2})\b', text)
        if m and re.search(r'\b(in|for|year|full\s+year)\b', text):
            year = int(m.group(1))
            return (date(year, 1, 1), date(year, 12, 31))
        return (None, None)
