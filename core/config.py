# core/config.py
"""Centralized configuration management."""

import os
from dotenv import load_dotenv


class Config:
    """Application configuration loaded from environment variables."""
    
    def __init__(self):
        load_dotenv(override=True)
        
        # Database configuration
        self.DB_URL = os.getenv("APP_DATABASE_URL", "").strip()
        self.DB_HOST = os.getenv("DB_HOST", "").strip()
        self.DB_PORT = int(os.getenv("DB_PORT", os.getenv("PGPORT", "5432")))
        self.DB_NAME = os.getenv("DB_NAME", "").strip()
        self.DB_USER = os.getenv("DB_USER", "").strip()
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
        self.DB_SSLMODE = os.getenv("DB_SSLMODE", "require").strip()
        
        # OpenAI configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
        self.LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5-nano").strip()
        
        # Application settings
        self.DEFAULT_STAT = os.getenv("DEFAULT_STAT", "twap").strip().lower()
        if self.DEFAULT_STAT not in ("twap", "vwap", "list", "daily_avg"):
            self.DEFAULT_STAT = "twap"
        
        self.ASSISTANT_NAME = "EMPS_v2"
        self.ANALYTICS_ACTIVE_WINDOW_SEC = int(os.getenv("ANALYTICS_ACTIVE_WINDOW_SEC", "120"))
        
    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.OPENAI_API_KEY)
