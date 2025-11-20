# parsers/time_parser.py
"""
Time range parser that handles:
- Hour blocks: "6-8 hours", "3 to 5 hrs"
- Time ranges: "06:00-08:30", "3pm to 5pm"
- Slot/block numbers: "20-50 slots", "1-24 blocks"
- Multiple groups: "6-8 and 12-14"
"""

import re
from typing import List, Dict, Optional


class TimeParser:
    """Parse time blocks and slots from natural language."""
    
    def parse_time_groups(self, text: str) -> List[Dict]:
        """
        Parse explicit time groups from text.
        Returns list of dicts with 'granularity', 'hours', and 'slots' keys.
        """
        lower = text.lower()
        
        # Check for explicit granularity hints
        prefer_quarter = bool(re.search(r'\b(blocks?|slots?|quarters?)\b', lower))
        prefer_hour = bool(re.search(r'\b(hours?|hrs?)\b', lower))
        
        hours_groups = []
        slot_groups = []
        
        # 1. Parse HH:MM[am/pm] to HH:MM[am/pm] time ranges
        time_ranges = self._parse_clock_times(lower)
        if time_ranges:
            hours_groups.extend(time_ranges["hours"])
            slot_groups.extend(time_ranges["slots"])
        
        # 2. Parse "H to H hrs/hours"
        # These are explicit hour requests (e.g., "6-8 hrs" -> 06:00 to 08:00 -> Blocks 7,8)
        hour_ranges = self._parse_hour_ranges(lower)
        if hour_ranges:
            hours_groups.extend(hour_ranges)
        
        # 3. Parse "N-M blocks/slots/quarters"
        slot_ranges = self._parse_explicit_slots(lower)
        if slot_ranges:
            slot_groups.extend(slot_ranges)
        
        # 4. Parse plain numeric ranges (6-8, 20-50, etc.)
        # CRITICAL FIX: Do NOT match if it looks like it was already caught by "hrs" regex
        # We use a negative lookahead in the regex itself, but here we just append if valid.
        numeric_ranges = self._parse_plain_numeric_ranges(lower)
        if numeric_ranges:
            for start, end in numeric_ranges:
                # If explicit "hours" were found elsewhere in text, be careful with plain numbers
                # But usually, we assume plain numbers <= 24 are hours if not specified
                if end <= 24 and not prefer_quarter:
                    # Convert plain numbers to 1-based blocks
                    # If user says "6-8" (meaning time), treat as 06:00-08:00 -> Blocks 7, 8
                    # Logic: Start 6 means 06:00 (Block 7). End 8 means 08:00 (Block 8).
                    # This is different from "Block 6 to Block 8".
                    # We assume "Time" semantics for plain small numbers.
                    
                    # However, existing logic was start, end.
                    # Let's align with "6-8 hrs" logic -> 06:00 to 08:00
                    # Block for 06:00 is 7. Block for 08:00 is 9 (exclusive) -> 8 (inclusive).
                    # So range is 7 to 8.
                    
                    # Previous logic (start, end) for 6-8 was 6,8 -> 6,7,8.
                    # We change this to match "Time" semantics: 
                    # Start H -> Block H+1. End H -> Block H.
                    s_block = start + 1
                    e_block = end
                    if e_block >= s_block:
                        hours_groups.append((s_block, e_block))
                else:
                    slot_groups.append((start, end))
        
        # Build result
        result = []
        
        if hours_groups:
            all_hours = []
            for s, e in hours_groups:
                all_hours.extend(range(s, e + 1))
            result.append({
                "granularity": "hour",
                "hours": sorted(set(all_hours)),
                "slots": None
            })
        
        if slot_groups:
            all_slots = []
            for s, e in slot_groups:
                all_slots.extend(range(s, e + 1))
            result.append({
                "granularity": "quarter",
                "hours": None,
                "slots": sorted(set(all_slots))
            })
        
        # Prefer hour or quarter based on hints
        if result:
            if prefer_quarter and len(result) > 1:
                result = [r for r in result if r["granularity"] == "quarter"]
            elif prefer_hour and len(result) > 1:
                result = [r for r in result if r["granularity"] == "hour"]
        
        return result
    
    def _parse_clock_times(self, text: str) -> Optional[Dict]:
        """Parse HH:MM[am/pm] to HH:MM[am/pm] patterns."""
        pattern = re.compile(
            r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to|-)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b',
            re.I
        )
        
        hour_groups = []
        slot_groups = []
        
        for m in pattern.finditer(text):
            h1 = int(m.group(1))
            m1 = int(m.group(2) or 0)
            a1 = m.group(3)
            
            h2 = int(m.group(4))
            m2 = int(m.group(5) or 0)
            a2 = m.group(6)
            
            # Convert to 24-hour
            H1 = self._to_24hour(h1, a1)
            H2 = self._to_24hour(h2, a2)
            
            # Hour blocks (1-24)
            # 06:00 -> Block 7. 08:00 -> End of Block 8.
            start_block = min(24, H1 + 1 + (1 if m1 > 0 else 0))
            end_block = min(24, H2 + (0 if m2 == 0 else 1))
            if m2 == 0:
                end_block = max(1, H2)
            
            if end_block >= start_block:
                hour_groups.append((start_block, end_block))
            
            # 15-min slots (1-96)
            sslot = max(1, min(96, (H1 * 60 + m1 + 14) // 15 + 1))
            eslot = max(1, min(96, (H2 * 60 + m2) // 15))
            
            if eslot >= sslot:
                slot_groups.append((sslot, eslot))
        
        if hour_groups or slot_groups:
            return {"hours": hour_groups, "slots": slot_groups}
        return None
    
    def _parse_hour_ranges(self, text: str) -> List[tuple]:
        """Parse 'H to H hrs/hours' patterns."""
        # Remove dates first to avoid false matches
        clean = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', ' ', text)
        
        pattern = re.compile(r'\b(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*(?:hours?|hrs?)\b', re.I)
        groups = []
        
        for m in pattern.finditer(clean):
            h1 = max(0, min(23, int(m.group(1))))
            h2 = max(0, min(24, int(m.group(2))))
            
            # Logic: "6-8 hrs" -> 06:00 to 08:00 -> Blocks 7, 8
            start_block = min(24, h1 + 1)
            end_block = 24 if h2 == 24 else max(1, min(24, h2))
            
            if end_block >= start_block:
                groups.append((start_block, end_block))
        
        return groups
    
    def _parse_explicit_slots(self, text: str) -> List[tuple]:
        """Parse 'N-M blocks/slots/quarters' patterns."""
        pattern = re.compile(r'\b(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*(?:blocks?|slots?|quarters?)\b', re.I)
        groups = []
        
        for m in pattern.finditer(text):
            a, b = int(m.group(1)), int(m.group(2))
            lo, hi = sorted((a, b))
            lo = max(1, lo)
            hi = min(96, hi)
            groups.append((lo, hi))
        
        return groups
    
    def _parse_plain_numeric_ranges(self, text: str) -> List[tuple]:
        """Parse plain 'N-M' or 'N to M' patterns, avoiding if 'hrs' follows."""
        # Remove dates first
        clean = text
        clean = re.sub(r'\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}\b', ' ', clean, flags=re.I)
        clean = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', ' ', clean)
        
        # Regex now negative lookahead for "hrs" or "hours" or "slots" to avoid double counting
        pattern = re.compile(r'\b(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\b(?!\s*(?:hours?|hrs?|blocks?|slots?))', re.I)
        groups = []
        
        for m in pattern.finditer(clean):
            a, b = int(m.group(1)), int(m.group(2))
            lo, hi = sorted((a, b))
            
            if 1 <= lo <= 96 and 1 <= hi <= 96:
                groups.append((lo, hi))
        
        return groups
    
    def _to_24hour(self, hour: int, ampm: Optional[str]) -> int:
        """Convert 12-hour time to 24-hour."""
        if ampm:
            hour = hour % 12
            if ampm.lower() == 'pm':
                hour += 12
        return max(0, min(23, hour))