"""
Quorum — Central Configuration
Loads environment variables and provides default settings.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("quorum.config")

# Load .env from backend directory
_backend_dir = Path(__file__).parent
load_dotenv(_backend_dir / ".env")

# ─── Directories ───────────────────────────────────────────────
PROJECT_DIR = _backend_dir
DATA_DIR = PROJECT_DIR / "data_cache"
DB_DIR = PROJECT_DIR / "db"
CHROMA_DIR = PROJECT_DIR / "chroma_store"

for d in [DATA_DIR, DB_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Groq LLM ─────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Validate API key on startup
if not GROQ_API_KEY:
    logger.warning(
        "GROQ_API_KEY is not set. Set it in backend/.env before running analyses."
    )

# Valid Groq models — update here if Groq retires/adds models
DEEP_THINK_MODEL = os.getenv("DEEP_THINK_MODEL", "llama-3.3-70b-versatile")   # Complex reasoning
QUICK_THINK_MODEL = os.getenv("QUICK_THINK_MODEL", "llama-3.1-8b-instant")    # Fast tasks

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))          # Seconds before LLM call times out
LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "3"))    # Max parallel LLM calls

# ─── Agent Pipeline ───────────────────────────────────────────
MAX_DEBATE_ROUNDS = int(os.getenv("MAX_DEBATE_ROUNDS", "2"))
MAX_RISK_DEBATE_ROUNDS = int(os.getenv("MAX_RISK_DEBATE_ROUNDS", "2"))
ANALYST_TIMEOUT = int(os.getenv("ANALYST_TIMEOUT", "60"))
PIPELINE_TIMEOUT = int(os.getenv("PIPELINE_TIMEOUT", "600"))   # 10 min total pipeline timeout
AUTO_TRADE_CONFIDENCE = float(os.getenv("AUTO_TRADE_CONFIDENCE", "0.85"))
APPROVAL_QUEUE_TTL = int(os.getenv("APPROVAL_QUEUE_TTL", "300"))

# Position sizing limits
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.25"))   # 25% max per trade
MIN_POSITION_SIZE = float(os.getenv("MIN_POSITION_SIZE", "0.01"))   # 1% min per trade

# ─── LangGraph ────────────────────────────────────────────────
CHECKPOINT_DB_PATH = DB_DIR / "checkpoints.db"
ENABLE_HITL = os.getenv("ENABLE_HITL", "true").lower() == "true"
DEFAULT_ANALYSTS = ["market", "sentiment", "news", "fundamentals"]

# ─── Data Providers ───────────────────────────────────────────
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Alpaca Market API
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"

NEWS_MAX_ARTICLES = int(os.getenv("NEWS_MAX_ARTICLES", "15"))
NEWS_LOOKBACK_DAYS = int(os.getenv("NEWS_LOOKBACK_DAYS", "7"))

# Data cache TTL (seconds) — avoids hammering yfinance/CCXT for same ticker
DATA_CACHE_TTL = int(os.getenv("DATA_CACHE_TTL", "300"))   # 5 minutes

# ─── Real-Time ────────────────────────────────────────────────
PRICE_POLL_INTERVAL = int(os.getenv("PRICE_POLL_INTERVAL", "15"))       # seconds between price updates
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "60"))   # minutes between full scans
SCAN_COOLDOWN_MINUTES = int(os.getenv("SCAN_COOLDOWN_MINUTES", "30"))   # min gap between same-ticker scans
ALERT_CONFIDENCE_THRESHOLD = float(os.getenv("ALERT_CONFIDENCE_THRESHOLD", "0.65"))  # min confidence to alert

# ─── Alerts ────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ─── Portfolio ────────────────────────────────────────────────
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100000.0"))
WATCHLIST_DEFAULT = ["AAPL", "NVDA", "TSLA", "BTC/USD", "ETH/USD"]

# ─── Database ─────────────────────────────────────────────────
SQLITE_DB_PATH = DB_DIR / "quorum.db"

# ─── Locus / LocusFounder ─────────────────────────────────────
LOCUS_API_KEY = os.getenv("LOCUS_API_KEY", "")          # Optional: pre-provisioned key
LOCUS_BETA_API = "https://beta-api.paywithlocus.com/api"
LOCUS_ENABLED = os.getenv("LOCUS_ENABLED", "true").lower() == "true"
ANALYSIS_PRICE_USDC = float(os.getenv("ANALYSIS_PRICE_USDC", "5.00"))

# ─── Server ───────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", 
    "http://localhost:3000,http://127.0.0.1:3000,"
    "https://quorum-frontend-74691596771.us-central1.run.app,"
    "https://svc-mp4160jcaxqzmks9.buildwithlocus.com"
).split(",")
