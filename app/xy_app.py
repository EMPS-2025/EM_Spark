# app.py - Main application entry point
import os
import asyncio
import traceback
from typing import List, Optional
import chainlit as cl
from dotenv import load_dotenv

# Import organized modules
from core.config import Config
from core.database import DatabaseManager
from parsers.query_parser import QueryParser
from parsers.date_parser import DateParser
from parsers.time_parser import TimeParser
from services.data_service import DataService
from services.analytics_service import AnalyticsService
from presenters.response_builder import ResponseBuilder
from utils.validators import QueryValidator

# ═══════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════

load_dotenv(override=True)
config = Config()
db = DatabaseManager(config)
analytics = AnalyticsService(db)
data_service = DataService(db)
response_builder = ResponseBuilder(config)

# ═══════════════════════════════════════════════════════════════
# CHAINLIT HANDLERS
# ═══════════════════════════════════════════════════════════════

@cl.on_chat_start
async def start_session():
    """Initialize user session with analytics tracking."""
    session_id = analytics.create_session()
    cl.user_session.set("session_id", session_id)
    
    # Optional: Send welcome message
    # await cl.Message(
    #     author=config.ASSISTANT_NAME,
    #     content="👋 Welcome to EM Spark! Ask me about energy market prices."
    # ).send()


@cl.on_message
async def handle_message(msg: cl.Message):
    """Main message handler with clean error handling."""
    
    session_id = cl.user_session.get("session_id")
    user_query = msg.content.strip()
    
    # Track analytics
    analytics.log_message(session_id, user_query)
    
    # Handle special commands
    if user_query.lower() in ("/stats", "stats"):
        await handle_stats_command()
        return
    
    # Show initial progress
    progress = await show_progress("🔍 Analyzing your query...")
    
    try:
        # Parse the query
        await update_progress(progress, "🧮 Parsing dates and times...")
        query_parser = QueryParser(config)
        parsed_queries = query_parser.parse(user_query)
        
        # Validate parsed queries
        if not QueryValidator.is_valid(parsed_queries):
            await hide_progress(progress)
            await send_error_message(
                "I couldn't understand your query. Please try:\n"
                "• `DAM 31 Oct 2025`\n"
                "• `GDAM 10-15 Aug 2025 for 6-8 hours`\n"
                "• `Compare Nov 2022, Nov 2023, Nov 2024`"
            )
            return
        
        # Fetch data for each query
        await update_progress(progress, "📊 Fetching market data...")
        results = []
        for query_spec in parsed_queries:
            data = await data_service.fetch_data(query_spec)
            results.append((query_spec, data))
        
        # Build and send response
        await update_progress(progress, "✨ Preparing results...")
        response = response_builder.build_response(results, user_query)
        
        await hide_progress(progress)
        await cl.Message(
            author=config.ASSISTANT_NAME,
            content=response
        ).send()
        
    except Exception as e:
        traceback.print_exc()
        await hide_progress(progress)
        await send_error_message(
            "⚠️ An error occurred while processing your request. "
            "Please try again or contact support."
        )
        analytics.log_error(session_id, str(e))


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def handle_stats_command():
    """Display service usage statistics."""
    stats = analytics.get_stats()
    await cl.Message(
        author=config.ASSISTANT_NAME,
        content=(
            "## 📈 Service Usage\n\n"
            f"- **Active Now**: {stats['active_now']}\n"
            f"- **Today's Sessions**: {stats['today_sessions']}\n"
            f"- **Messages Today**: {stats['messages_today']}\n"
            f"- **Total Sessions**: {stats['total_sessions']}"
        )
    ).send()


async def show_progress(text: str) -> cl.Message:
    """Show loading indicator."""
    msg = cl.Message(author=config.ASSISTANT_NAME, content=text)
    await msg.send()
    return msg


async def update_progress(msg: cl.Message, text: str):
    """Update loading indicator text."""
    try:
        await msg.update(content=text)
    except Exception:
        pass


async def hide_progress(msg: cl.Message):
    """Hide loading indicator."""
    try:
        await msg.remove()
    except Exception:
        try:
            await msg.update(content="")
        except Exception:
            pass


async def send_error_message(text: str):
    """Send user-friendly error message."""
    await cl.Message(
        author=config.ASSISTANT_NAME,
        content=text
    ).send()


# ═══════════════════════════════════════════════════════════════
# MODULE STRUCTURE (to be created in separate files)
# ═══════════════════════════════════════════════════════════════

"""
Proposed file structure:

app.py (this file)
│
├── core/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connection pooling
│   └── models.py          # Data models (QuerySpec, MarketData, etc.)
│
├── parsers/
│   ├── __init__.py
│   ├── query_parser.py    # Main query orchestrator
│   ├── date_parser.py     # Date/range parsing logic
│   ├── time_parser.py     # Hour/slot parsing logic
│   └── llm_parser.py      # GPT fallback parser
│
├── services/
│   ├── __init__.py
│   ├── data_service.py    # Data fetching orchestration
│   ├── analytics_service.py  # Usage analytics
│   └── calculation_service.py  # TWAP/VWAP calculations
│
├── presenters/
│   ├── __init__.py
│   ├── response_builder.py    # Markdown response generation
│   ├── table_formatter.py     # Table formatting
│   └── derivative_presenter.py # Derivative data formatting
│
└── utils/
    ├── __init__.py
    ├── validators.py      # Input validation
    ├── formatters.py      # Date/time/money formatting
    └── text_utils.py      # Text normalization utilities
"""
