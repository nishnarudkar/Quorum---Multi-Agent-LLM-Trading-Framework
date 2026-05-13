"""
Quorum — Watchlist Scanner
Background loop that automatically triggers the full 13-agent analysis
pipeline for each ticker in the watchlist on a configurable schedule.

Sends Telegram/Discord alerts when a high-confidence signal is found.
Skips tickers that were recently analyzed (within SCAN_COOLDOWN_MINUTES).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Awaitable, Optional

from config import WATCHLIST_DEFAULT, AUTO_TRADE_CONFIDENCE

logger = logging.getLogger("quorum.scanner")

# How often to run a full scan of the watchlist (minutes)
SCAN_INTERVAL_MINUTES = int(__import__("os").getenv("SCAN_INTERVAL_MINUTES", "60"))

# Minimum minutes between analyses of the same ticker
SCAN_COOLDOWN_MINUTES = int(__import__("os").getenv("SCAN_COOLDOWN_MINUTES", "30"))

# Only alert if confidence is above this threshold
ALERT_CONFIDENCE_THRESHOLD = float(
    __import__("os").getenv("ALERT_CONFIDENCE_THRESHOLD", "0.65")
)


class WatchlistScanner:
    """
    Periodically runs the full analysis pipeline on each watchlist ticker.

    Usage:
        scanner = WatchlistScanner(pipeline, broadcast_fn)
        await scanner.start()
        scanner.set_watchlist([...])
        await scanner.stop()
    """

    def __init__(
        self,
        pipeline,
        broadcast: Callable[[dict], Awaitable[None]],
        trade_db=None,
    ):
        self._pipeline = pipeline
        self._broadcast = broadcast
        self._trade_db = trade_db
        self._task: asyncio.Task | None = None
        self._running = False

        # Track last analysis time per ticker to enforce cooldown
        self._last_analyzed: dict[str, datetime] = {}

        # Watchlist: [{"ticker": "AAPL", "asset_type": "stock"}, ...]
        self._watchlist: list[dict] = []
        for ticker in WATCHLIST_DEFAULT:
            asset_type = "crypto" if "/" in ticker else "stock"
            self._watchlist.append({"ticker": ticker, "asset_type": asset_type})

    # ─── Control ──────────────────────────────────────────────

    async def start(self):
        """Start the background scanner loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            f"Watchlist scanner started — {len(self._watchlist)} tickers, "
            f"scan every {SCAN_INTERVAL_MINUTES}min, "
            f"cooldown {SCAN_COOLDOWN_MINUTES}min"
        )

    async def stop(self):
        """Stop the scanner cleanly."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Watchlist scanner stopped")

    def set_watchlist(self, tickers: list[dict]):
        """Update the watchlist at runtime."""
        self._watchlist = tickers
        logger.info(f"Scanner watchlist updated — {len(tickers)} tickers")

    def add_ticker(self, ticker: str, asset_type: str = "stock"):
        entry = {"ticker": ticker.upper(), "asset_type": asset_type}
        if entry not in self._watchlist:
            self._watchlist.append(entry)

    def remove_ticker(self, ticker: str):
        self._watchlist = [
            t for t in self._watchlist if t["ticker"] != ticker.upper()
        ]

    def get_status(self) -> dict:
        """Return scanner status for the /realtime/status endpoint."""
        return {
            "running": self._running,
            "watchlist": self._watchlist,
            "scan_interval_minutes": SCAN_INTERVAL_MINUTES,
            "cooldown_minutes": SCAN_COOLDOWN_MINUTES,
            "alert_confidence_threshold": ALERT_CONFIDENCE_THRESHOLD,
            "last_analyzed": {
                k: v.isoformat() for k, v in self._last_analyzed.items()
            },
            "next_scan": self._next_scan_time.isoformat() if hasattr(self, "_next_scan_time") else None,
        }

    # ─── Loop ─────────────────────────────────────────────────

    async def _loop(self):
        """Main scanner loop — waits, then scans all tickers."""
        # First scan after a short delay so startup is clean
        await asyncio.sleep(30)

        while self._running:
            self._next_scan_time = datetime.utcnow() + timedelta(
                minutes=SCAN_INTERVAL_MINUTES
            )
            try:
                await self._scan_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scanner loop error: {e}")

            # Wait for next scan interval
            await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)

    async def _scan_all(self):
        """Run analysis on all watchlist tickers that are past their cooldown."""
        now = datetime.utcnow()
        cooldown = timedelta(minutes=SCAN_COOLDOWN_MINUTES)

        due = [
            entry for entry in self._watchlist
            if now - self._last_analyzed.get(entry["ticker"], datetime.min) > cooldown
        ]

        if not due:
            logger.info("Scanner: all tickers within cooldown, skipping scan")
            return

        logger.info(f"Scanner: starting scan of {len(due)} tickers")

        for entry in due:
            if not self._running:
                break
            ticker = entry["ticker"]
            asset_type = entry["asset_type"]

            await self._analyze_ticker(ticker, asset_type)

            # Small gap between tickers to avoid hammering the LLM
            await asyncio.sleep(5)

        logger.info("Scanner: scan complete")

    async def _analyze_ticker(self, ticker: str, asset_type: str):
        """Run the full pipeline for one ticker and handle the result."""
        import uuid
        from utils.alerts import send_analysis_alert
        from api.main import _serialize_state

        analysis_id = str(uuid.uuid4())
        logger.info(f"Scanner: analyzing {ticker} ({asset_type}) [{analysis_id[:8]}]")

        self._last_analyzed[ticker] = datetime.utcnow()

        try:
            await self._broadcast({
                "type": "scanner_start",
                "data": {
                    "ticker": ticker,
                    "asset_type": asset_type,
                    "analysis_id": analysis_id,
                    "source": "watchlist_scanner",
                },
            })

            result = await self._pipeline.analyze(
                ticker=ticker,
                asset_type=asset_type,
                trade_date=datetime.utcnow().strftime("%Y-%m-%d"),
                analysis_id=analysis_id,
            )

            serialized = _serialize_state(result)

            # Save to DB
            if self._trade_db:
                await self._trade_db.save_analysis_log(
                    ticker, asset_type,
                    datetime.utcnow().strftime("%Y-%m-%d"),
                    {**serialized, "source": "watchlist_scanner"},
                )

            # Broadcast result
            await self._broadcast({
                "type": "scanner_complete",
                "data": {
                    **serialized,
                    "source": "watchlist_scanner",
                },
            })

            # Alert if signal is strong enough
            signal = result.get("trade_signal")
            if signal:
                confidence = (
                    signal.confidence
                    if hasattr(signal, "confidence")
                    else signal.get("confidence", 0)
                )
                action = (
                    signal.action.value
                    if hasattr(signal, "action") and hasattr(signal.action, "value")
                    else signal.get("action", "hold")
                )
                if (
                    confidence >= ALERT_CONFIDENCE_THRESHOLD
                    and str(action).lower() != "hold"
                ):
                    logger.info(
                        f"Scanner: high-confidence signal for {ticker} — "
                        f"{action} @ {confidence:.0%}"
                    )
                    await send_analysis_alert(serialized)

        except Exception as e:
            logger.error(f"Scanner: analysis failed for {ticker}: {e}")
            await self._broadcast({
                "type": "scanner_error",
                "data": {
                    "ticker": ticker,
                    "error": str(e),
                    "source": "watchlist_scanner",
                },
            })
