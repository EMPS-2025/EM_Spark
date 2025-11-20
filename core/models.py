# core/models.py
"""Data models for the application."""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional
#from parsers.query_parser import QueryExclusion


@dataclass
class QuerySpec:
    """Structured representation of a user query."""
    market: str                     # 'DAM' or 'GDAM'
    start_date: date
    end_date: date
    granularity: str                # 'hour' or 'quarter'
    hours: Optional[List[int]]      # 1-24 for hourly data
    slots: Optional[List[int]]      # 1-96 for 15-min slots
    stat: str                       # 'list', 'twap', 'vwap', 'daily_avg'
    area: str = "ALL"
    auto_added: bool = False
    exclusion: Optional['QueryExclusion'] = None
    
    def __repr__(self):
        time_range = f"hours={self.hours}" if self.hours else f"slots={self.slots}"
        return (
            f"QuerySpec({self.market}, {self.start_date} to {self.end_date}, "
            f"{self.granularity}, {time_range}, stat={self.stat})"
        )
