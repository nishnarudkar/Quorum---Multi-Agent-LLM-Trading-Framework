"""
Quorum — Stock Data Provider
Wraps yfinance for stock market data, technicals, and fundamentals.
Includes TTL-based in-memory cache to avoid redundant network calls.
"""

import time
import logging
import yfinance as yf
import pandas as pd
from stockstats import StockDataFrame
from typing import Optional
from config import DATA_CACHE_TTL

logger = logging.getLogger("quorum.stock")


class StockProvider:
    """Provides stock market data via yfinance with TTL caching."""

    def __init__(self):
        # Cache structure: {cache_key: (data, expiry_timestamp)}
        self._cache: dict[str, tuple] = {}

    # ─── Cache helpers ────────────────────────────────────────

    def _get_cached(self, key: str):
        entry = self._cache.get(key)
        if entry and time.time() < entry[1]:
            return entry[0]
        return None

    def _set_cached(self, key: str, data):
        self._cache[key] = (data, time.time() + DATA_CACHE_TTL)

    # ─── Price Data ───────────────────────────────────────────

    def get_price_data(self, ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
        """Get OHLCV price data."""
        cache_key = f"price:{ticker}:{period}:{interval}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            if df.empty:
                logger.warning(f"No price data returned for {ticker} (period={period})")
            self._set_cached(cache_key, df)
            return df
        except Exception as e:
            logger.error(f"Failed to fetch price data for {ticker}: {e}")
            return pd.DataFrame()

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current/latest price."""
        cache_key = f"current_price:{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price:
                self._set_cached(cache_key, price)
            return price
        except Exception as e:
            logger.error(f"Failed to fetch current price for {ticker}: {e}")
            return None

    # ─── Technical Indicators ─────────────────────────────────

    def get_technical_indicators(self, ticker: str, period: str = "6mo") -> dict:
        """Calculate technical indicators using stockstats."""
        cache_key = f"technicals:{ticker}:{period}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        df = self.get_price_data(ticker, period=period)
        if df.empty:
            logger.warning(f"Cannot compute indicators for {ticker} — no price data")
            return {"error": "No price data available", "ticker": ticker}

        try:
            sdf = StockDataFrame.retype(df.copy())

            def safe_float(series, idx=-1) -> Optional[float]:
                try:
                    val = float(series.iloc[idx])
                    return val if pd.notna(val) and not pd.isna(val) else None
                except Exception:
                    return None

            indicators: dict = {
                "ticker": ticker,
                "current_price": safe_float(df["Close"]),
                "rsi_14": safe_float(sdf["rsi_14"]) if len(sdf) > 14 else None,
                "macd": safe_float(sdf["macd"]) if len(sdf) > 26 else None,
                "macd_signal": safe_float(sdf["macds"]) if len(sdf) > 26 else None,
                "macd_hist": safe_float(sdf["macdh"]) if len(sdf) > 26 else None,
                "sma_20": safe_float(df["Close"].rolling(20).mean()) if len(df) > 20 else None,
                "sma_50": safe_float(df["Close"].rolling(50).mean()) if len(df) > 50 else None,
                "sma_200": safe_float(df["Close"].rolling(200).mean()) if len(df) > 200 else None,
                "ema_12": safe_float(df["Close"].ewm(span=12).mean()) if len(df) > 12 else None,
                "ema_26": safe_float(df["Close"].ewm(span=26).mean()) if len(df) > 26 else None,
                "bollinger_upper": None,
                "bollinger_middle": None,
                "bollinger_lower": None,
                "volume_avg_20": safe_float(df["Volume"].rolling(20).mean()) if len(df) > 20 else None,
                "price_change_1d": None,
                "price_change_5d": None,
                "price_change_1m": None,
            }

            # Bollinger Bands
            if len(df) > 20:
                sma20 = df["Close"].rolling(20).mean()
                std20 = df["Close"].rolling(20).std()
                indicators["bollinger_upper"] = safe_float(sma20 + 2 * std20)
                indicators["bollinger_middle"] = safe_float(sma20)
                indicators["bollinger_lower"] = safe_float(sma20 - 2 * std20)

            # Price changes
            close = df["Close"]
            if len(close) > 1:
                indicators["price_change_1d"] = round(
                    (close.iloc[-1] / close.iloc[-2] - 1) * 100, 2
                )
            if len(close) > 5:
                indicators["price_change_5d"] = round(
                    (close.iloc[-1] / close.iloc[-5] - 1) * 100, 2
                )
            if len(close) > 21:
                indicators["price_change_1m"] = round(
                    (close.iloc[-1] / close.iloc[-21] - 1) * 100, 2
                )

            self._set_cached(cache_key, indicators)
            return indicators

        except Exception as e:
            logger.error(f"Failed to compute technical indicators for {ticker}: {e}")
            return {"error": str(e), "ticker": ticker}

    # ─── Fundamentals ─────────────────────────────────────────

    def get_fundamentals(self, ticker: str) -> dict:
        """Get fundamental company data."""
        cache_key = f"fundamentals:{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            data = {
                "ticker": ticker,
                "full_name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "dividend_yield": info.get("dividendYield"),
                "eps": info.get("trailingEps"),
                "revenue": info.get("totalRevenue"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "quick_ratio": info.get("quickRatio"),
                "free_cashflow": info.get("freeCashflow"),
                "beta": info.get("beta"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "analyst_target": info.get("targetMeanPrice"),
                "recommendation": info.get("recommendationKey"),
                "description": (info.get("longBusinessSummary") or "")[:600],
            }
            self._set_cached(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {ticker}: {e}")
            return {"error": str(e), "ticker": ticker}

    # ─── Financial Statements ─────────────────────────────────

    def get_balance_sheet(self, ticker: str) -> dict:
        """Get latest balance sheet data."""
        try:
            stock = yf.Ticker(ticker)
            bs = stock.balance_sheet
            if bs is None or bs.empty:
                return {}
            latest = bs.iloc[:, 0]
            return {str(k): (float(v) if pd.notna(v) else None) for k, v in latest.items()}
        except Exception as e:
            logger.error(f"Failed to fetch balance sheet for {ticker}: {e}")
            return {}

    def get_cashflow(self, ticker: str) -> dict:
        """Get latest cash flow statement."""
        try:
            stock = yf.Ticker(ticker)
            cf = stock.cashflow
            if cf is None or cf.empty:
                return {}
            latest = cf.iloc[:, 0]
            return {str(k): (float(v) if pd.notna(v) else None) for k, v in latest.items()}
        except Exception as e:
            logger.error(f"Failed to fetch cashflow for {ticker}: {e}")
            return {}

    def get_income_statement(self, ticker: str) -> dict:
        """Get latest income statement."""
        try:
            stock = yf.Ticker(ticker)
            inc = stock.income_stmt
            if inc is None or inc.empty:
                return {}
            latest = inc.iloc[:, 0]
            return {str(k): (float(v) if pd.notna(v) else None) for k, v in latest.items()}
        except Exception as e:
            logger.error(f"Failed to fetch income statement for {ticker}: {e}")
            return {}

    # ─── News & Insider Data ──────────────────────────────────

    def get_news(self, ticker: str, limit: int = 15) -> list[dict]:
        """Get recent news for ticker."""
        try:
            stock = yf.Ticker(ticker)
            news = stock.news or []
            return [
                {
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                    "link": item.get("link", ""),
                    "published": item.get("providerPublishTime", ""),
                    "type": item.get("type", ""),
                }
                for item in news[:limit]
                if item.get("title")  # skip items with no title
            ]
        except Exception as e:
            logger.error(f"Failed to fetch news for {ticker}: {e}")
            return []

    def get_insider_transactions(self, ticker: str, limit: int = 10) -> list[dict]:
        """Get recent insider transactions."""
        try:
            stock = yf.Ticker(ticker)
            insiders = stock.insider_transactions
            if insiders is None or insiders.empty:
                return []
            # Convert to clean dicts, handling NaN
            records = []
            for _, row in insiders.head(limit).iterrows():
                record = {}
                for col, val in row.items():
                    if pd.isna(val) if not isinstance(val, str) else False:
                        record[str(col)] = None
                    else:
                        record[str(col)] = str(val) if not isinstance(val, (int, float)) else val
                records.append(record)
            return records
        except Exception as e:
            logger.error(f"Failed to fetch insider transactions for {ticker}: {e}")
            return []
