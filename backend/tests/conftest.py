"""Shared pytest setup: make the backend package importable and keep tests offline."""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Tests must never reach real services, even if a developer's backend/.env has keys.
# config.py loads .env without overriding variables that are already set.
for var in (
    "ALPACA_API_KEY", "ALPACA_SECRET_KEY",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "DISCORD_WEBHOOK_URL",
):
    os.environ[var] = ""
os.environ.setdefault("GROQ_API_KEYS", "test-key-1;test-key-2")
