import time
import logging
import pandas as pd
from typing import Optional
from config import DATA_CACHE_TTL
from .alpaca_provider import AlpacaProvider

logger = logging.getLogger("quorum.crypto")


class CryptoProvider:
    """Provides cryptocurrency market data via Alpaca (formerly Binance/CCXT)."""

    def __init__(self):
        self._cache: dict[str, tuple] = {}
        self.alpaca = AlpacaProvider()
        if not self.alpaca.is_active:
            logger.warning("AlpacaProvider not active for crypto — check API keys")

    # ─── Cache helpers ────────────────────────────────────────

    def _get_cached(self, key: str):
        entry = self._cache.get(key)
        if entry and time.time() < entry[1]:
            return entry[0]
        return None

    def _set_cached(self, key: str, data):
        self._cache[key] = (data, time.time() + DATA_CACHE_TTL)

    # ─── Symbol normalization ─────────────────────────────────

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to Alpaca standard (e.g. BTC/USDT → BTC/USD)."""
        symbol = symbol.upper().strip()
        if symbol.endswith("/USDT"):
            symbol = symbol[:-5] + "/USD"
        if "/" not in symbol:
            symbol = f"{symbol}/USD"
        return symbol

    # ─── Price Data ───────────────────────────────────────────

    def get_price_data(self, symbol: str, timeframe: str = "1d", limit: int = 90) -> pd.DataFrame:
        """Get OHLCV candle data from Alpaca."""
        symbol = self._normalize_symbol(symbol)
        cache_key = f"ohlcv:{symbol}:{timeframe}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            # AlpacaProvider handles the client call
            df = self.alpaca.get_price_data(symbol, asset_type="crypto", days=limit)
            if df.empty:
                logger.warning(f"No OHLCV data returned for {symbol} from Alpaca")
                return pd.DataFrame()
            
            self._set_cached(cache_key, df)
            return df
        except Exception as e:
            logger.error(f"Alpaca OHLCV fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a crypto pair from Alpaca."""
        symbol = self._normalize_symbol(symbol)
        cache_key = f"price:{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            price = self.alpaca.get_current_price(symbol, asset_type="crypto")
            if price:
                self._set_cached(cache_key, price)
            return price
        except Exception as e:
            logger.error(f"Alpaca price fetch failed for {symbol}: {e}")
            return None

    def get_ticker_info(self, symbol: str) -> dict:
        """Get 24h ticker statistics approximated from bars."""
        symbol = self._normalize_symbol(symbol)
        cache_key = f"ticker:{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            df = self.get_price_data(symbol, limit=2)
            if df.empty:
                return {"error": "No data", "symbol": symbol}
            
            last_close = float(df["close"].iloc[-1])
            prev_close = float(df["close"].iloc[-2]) if len(df) > 1 else last_close
            
            data = {
                "symbol": symbol,
                "last_price": last_close,
                "high_24h": float(df["high"].iloc[-1]),
                "low_24h": float(df["low"].iloc[-1]),
                "volume_24h": float(df["volume"].iloc[-1]),
                "change_24h": round(last_close - prev_close, 4),
                "change_pct_24h": round((last_close / prev_close - 1) * 100, 2) if prev_close else 0,
            }
            self._set_cached(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Ticker info approx failed for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}

    # ─── Technical Indicators ─────────────────────────────────

    def get_technical_indicators(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> dict:
        """Calculate technical indicators for crypto."""
        norm_symbol = self._normalize_symbol(symbol)
        cache_key = f"technicals:{norm_symbol}:{timeframe}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        df = self.get_price_data(symbol, timeframe, limit)
        if df.empty:
            logger.warning(f"Cannot compute indicators for {symbol} — no price data")
            return {"error": "No price data available", "symbol": symbol}

        try:
            close = df["close"]
            indicators: dict = {
                "symbol": norm_symbol,
                "current_price": float(close.iloc[-1]),
                "price_change_24h": None,
                "price_change_7d": None,
                "price_change_30d": None,
                "rsi_14": None,
                "sma_20": None,
                "sma_50": None,
                "ema_12": None,
                "bollinger_upper": None,
                "bollinger_middle": None,
                "bollinger_lower": None,
                "volume_avg_20": None,
            }

            if len(close) > 1:
                indicators["price_change_24h"] = round(
                    (close.iloc[-1] / close.iloc[-2] - 1) * 100, 2
                )
            if len(close) > 7:
                indicators["price_change_7d"] = round(
                    (close.iloc[-1] / close.iloc[-7] - 1) * 100, 2
                )
            if len(close) > 30:
                indicators["price_change_30d"] = round(
                    (close.iloc[-1] / close.iloc[-30] - 1) * 100, 2
                )

            # RSI — guard against division by zero when all candles are up/down
            if len(close) > 14:
                delta = close.diff()
                gain = delta.where(delta > 0, 0.0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
                last_loss = loss.iloc[-1]
                if last_loss and last_loss > 0:
                    rs = gain.iloc[-1] / last_loss
                    indicators["rsi_14"] = round(100 - 100 / (1 + rs), 2)
                else:
                    # All gains — RSI is effectively 100
                    indicators["rsi_14"] = 100.0

            # SMAs
            if len(close) > 20:
                indicators["sma_20"] = round(float(close.rolling(20).mean().iloc[-1]), 4)
            if len(close) > 50:
                indicators["sma_50"] = round(float(close.rolling(50).mean().iloc[-1]), 4)

            # EMA
            if len(close) > 12:
                indicators["ema_12"] = round(float(close.ewm(span=12).mean().iloc[-1]), 4)

            # Bollinger Bands
            if len(close) > 20:
                sma20 = close.rolling(20).mean()
                std20 = close.rolling(20).std()
                indicators["bollinger_upper"] = round(float((sma20 + 2 * std20).iloc[-1]), 4)
                indicators["bollinger_middle"] = round(float(sma20.iloc[-1]), 4)
                indicators["bollinger_lower"] = round(float((sma20 - 2 * std20).iloc[-1]), 4)

            # Volume
            if len(df) > 20:
                indicators["volume_avg_20"] = float(df["volume"].rolling(20).mean().iloc[-1])

            self._set_cached(cache_key, indicators)
            return indicators

        except Exception as e:
            logger.error(f"Failed to compute indicators for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}

    # ─── Order Book ───────────────────────────────────────────

    def get_order_book(self, symbol: str, limit: int = 10) -> dict:
        """Get order book depth (mocked for Alpaca)."""
        # Alpaca historical data client doesn't provide real-time order book depth via REST easily
        # We can mock a tight spread for the agents
        price = self.get_current_price(symbol)
        if not price:
            return {"error": "Price not available"}
        
        return {
            "bids": [[price * 0.999, 1.0]],
            "asks": [[price * 1.001, 1.0]],
            "spread": round(price * 0.002, 4),
        }
