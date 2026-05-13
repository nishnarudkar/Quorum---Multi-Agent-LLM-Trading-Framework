"""
Quorum — Real-Time Price Stream
Background loop that polls current prices for the active watchlist
and broadcasts updates over WebSocket every N seconds.

Clients receive:
  { "type": "price_update", "data": { "AAPL": { "price": 213.4, "change_pct": 0.82, ... }, ... } }
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Awaitable

from config import WATCHLIST_DEFAULT, DATA_CACHE_TTL

logger = logging.getLogger("quorum.pricestream")

# How often to push price updates (seconds). Shorter = more real-time, more API calls.
PRICE_POLL_INTERVAL = 15   # every 15 seconds


class PriceStream:
    """
    Polls prices for a dynamic watchlist and broadcasts updates via a callback.

    Usage:
        stream = PriceStream(broadcast_fn)
        await stream.start()          # starts background loop
        stream.set_watchlist([...])   # update tickers at runtime
        await stream.stop()           # clean shutdown
    """

    def __init__(self, broadcast: Callable[[dict], Awaitable[None]]):
        self._broadcast = broadcast
        self._watchlist: list[dict] = []   # [{"ticker": "AAPL", "asset_type": "stock"}, ...]
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_prices: dict[str, dict] = {}

        # Seed with defaults
        for ticker in WATCHLIST_DEFAULT:
            asset_type = "crypto" if "/" in ticker else "stock"
            self._watchlist.append({"ticker": ticker, "asset_type": asset_type})

    # ─── Control ──────────────────────────────────────────────

    async def start(self):
        """Start the background polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            f"Price stream started — polling {len(self._watchlist)} tickers "
            f"every {PRICE_POLL_INTERVAL}s"
        )

    async def stop(self):
        """Stop the background loop cleanly."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Price stream stopped")

    def set_watchlist(self, tickers: list[dict]):
        """
        Update the watchlist at runtime.

        Args:
            tickers: list of {"ticker": str, "asset_type": "stock"|"crypto"}
        """
        self._watchlist = tickers
        logger.info(f"Watchlist updated — {len(tickers)} tickers")

    def add_ticker(self, ticker: str, asset_type: str = "stock"):
        """Add a single ticker to the watchlist."""
        entry = {"ticker": ticker.upper(), "asset_type": asset_type}
        if entry not in self._watchlist:
            self._watchlist.append(entry)

    def remove_ticker(self, ticker: str):
        """Remove a ticker from the watchlist."""
        self._watchlist = [
            t for t in self._watchlist if t["ticker"] != ticker.upper()
        ]

    def get_watchlist(self) -> list[dict]:
        return list(self._watchlist)

    def get_last_prices(self) -> dict:
        return dict(self._last_prices)

    # ─── Loop ─────────────────────────────────────────────────

    async def _loop(self):
        """Main polling loop — runs until stopped."""
        # Stagger the first poll slightly so startup isn't noisy
        await asyncio.sleep(3)

        while self._running:
            try:
                await self._poll_and_broadcast()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Price stream poll error: {e}")

            await asyncio.sleep(PRICE_POLL_INTERVAL)

    async def _poll_and_broadcast(self):
        """Fetch prices for all watchlist tickers and broadcast changes."""
        if not self._watchlist:
            return

        # Import here to avoid circular imports at module load time
        from data.stock_provider import StockProvider
        from data.crypto_provider import CryptoProvider

        stock_provider = StockProvider()
        crypto_provider = CryptoProvider()

        updates: dict[str, dict] = {}

        for entry in self._watchlist:
            ticker = entry["ticker"]
            asset_type = entry["asset_type"]

            try:
                if asset_type == "crypto":
                    price = crypto_provider.get_current_price(ticker)
                    info = crypto_provider.get_ticker_info(ticker) if price else {}
                    if price:
                        updates[ticker] = {
                            "ticker": ticker,
                            "asset_type": "crypto",
                            "price": round(float(price), 6),
                            "change_pct_24h": info.get("change_pct_24h"),
                            "high_24h": info.get("high_24h"),
                            "low_24h": info.get("low_24h"),
                            "volume_24h": info.get("volume_24h"),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                else:
                    indicators = stock_provider.get_technical_indicators(ticker)
                    price = indicators.get("current_price")
                    if price:
                        updates[ticker] = {
                            "ticker": ticker,
                            "asset_type": "stock",
                            "price": round(float(price), 4),
                            "change_pct_1d": indicators.get("price_change_1d"),
                            "change_pct_5d": indicators.get("price_change_5d"),
                            "rsi_14": indicators.get("rsi_14"),
                            "sma_20": indicators.get("sma_20"),
                            "volume_avg_20": indicators.get("volume_avg_20"),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
            except Exception as e:
                logger.debug(f"Price fetch failed for {ticker}: {e}")

        if not updates:
            return

        # Only broadcast tickers whose price actually changed
        changed = {}
        for ticker, data in updates.items():
            prev = self._last_prices.get(ticker, {})
            if prev.get("price") != data.get("price"):
                changed[ticker] = data

        self._last_prices.update(updates)

        if changed:
            await self._broadcast({
                "type": "price_update",
                "data": changed,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.debug(f"Price update broadcast — {len(changed)} tickers changed")
