# utils/text_utils.py
"""Text normalization utilities for query parsing."""

import re


def normalize_text(text: str) -> str:
    """
    Normalize user input for consistent parsing.
    
    Handles:
    - Different dash types (em-dash, en-dash, hyphen)
    - Multiple whitespace
    - "between X and Y" → "X to Y"
    - Month abbreviations with years (Nov-24 → Nov 2024)
    """
    s = text.strip()
    
    # Normalize dashes
    s = s.replace("—", "-").replace("–", "-").replace("−", "-")
    
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s)
    
    # "between X and Y" → "X to Y"
    s = re.sub(r"\bbetween\s+(\S.*?)\s+and\s+(\S.*?)\b", r"\1 to \2", s, flags=re.I)
    
    # "upto/through/till/until" → "to"
    s = re.sub(r"\b(upto|through|till|until)\b", "to", s, flags=re.I)
    
    # Month abbreviations with 2-digit years (Nov-24 → Nov 2024)
    month_pattern = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)"
    s = re.sub(rf"\b({month_pattern})\s*[-']\s*(\d{{2}})\b", lambda m: f"{m.group(1)} 20{m.group(2)}", s, flags=re.I)
    
    return s


def highlight_gdam(text: str) -> str:
    """Highlight GDAM with green dot emoji (works in markdown tables)."""
    return re.sub(r'\b(GDAM)\b', r'🟢 **\1**', text)


def highlight_rtm(text: str) -> str:
    """Highlight RTM with blue dot emoji."""
    return re.sub(r'\b(RTM)\b', r'🔵 **\1**', text)