"""
Quorum — Alpaca Market Provider
Handles real-time market data and trade execution via Alpaca.
Gracefully degrades if alpaca-py is not installed or keys are not set.
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER

logger = logging.getLogger("quorum.alpaca")

# Guard against missing alpaca-py package
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
    from alpaca.data.timeframe import TimeFrame
    _ALPACA_AVAILABLE = True
except ImportError:
    _ALPACA_AVAILABLE = False
    logger.warning("alpaca-py not installed — Alpaca integration disabled")

logger = logging.getLogger("quorum.alpaca")

class AlpacaProvider:
    """Provides market data and trade execution via Alpaca API."""

    def __init__(self):
        self.api_key = ALPACA_API_KEY
        self.secret_key = ALPACA_SECRET_KEY
        self.paper = ALPACA_PAPER

        self._trading_client = None
        self._stock_data_client = None
        self._crypto_data_client = None

        if not _ALPACA_AVAILABLE:
            logger.warning("AlpacaProvider inactive — alpaca-py not installed")
            return

        if self.api_key and self.secret_key:
            try:
                self._trading_client = TradingClient(self.api_key, self.secret_key, paper=self.paper)
                self._stock_data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
                self._crypto_data_client = CryptoHistoricalDataClient(self.api_key, self.secret_key)
                logger.info(f"AlpacaProvider initialized (Paper={self.paper})")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca clients: {e}")
        else:
            logger.info("Alpaca API keys not set — provider inactive")

    @property
    def is_active(self) -> bool:
        return self._trading_client is not None

    # ─── Market Data ──────────────────────────────────────────

    def get_price_data(self, ticker: str, asset_type: str = "stock", days: int = 30) -> pd.DataFrame:
        """Get OHLCV price data for the last N days."""
        if not self.is_active:
            return pd.DataFrame()

        try:
            start_time = datetime.now() - timedelta(days=days)
            
            if asset_type == "stock":
                request_params = StockBarsRequest(
                    symbol_or_symbols=ticker,
                    timeframe=TimeFrame.Day,
                    start=start_time
                )
                bars = self._stock_data_client.get_stock_bars(request_params)
            else:
                request_params = CryptoBarsRequest(
                    symbol_or_symbols=ticker,
                    timeframe=TimeFrame.Day,
                    start=start_time
                )
                bars = self._crypto_data_client.get_crypto_bars(request_params)
            
            df = bars.df
            if df.empty:
                return df
                
            # Alpaca multi-index df (symbol, timestamp) -> single index (timestamp)
            if isinstance(df.index, pd.MultiIndex):
                df = df.xs(ticker, level=0)
            
            return df
        except Exception as e:
            logger.error(f"Alpaca failed to fetch price data for {ticker}: {e}")
            return pd.DataFrame()

    def get_current_price(self, ticker: str, asset_type: str = "stock") -> Optional[float]:
        """Get the latest close price."""
        df = self.get_price_data(ticker, asset_type, days=1)
        if not df.empty:
            return float(df.iloc[-1]["close"])
        return None

    # ─── Execution ────────────────────────────────────────────

    async def execute_trade(
        self,
        ticker: str,
        action: str,
        quantity: float,
        asset_type: str = "stock"
    ) -> Dict[str, Any]:
        """Execute a market order on Alpaca."""
        if not self.is_active or not _ALPACA_AVAILABLE:
            return {"error": "Alpaca API not configured"}

        if action not in ["buy", "sell"]:
            return {"error": f"Invalid action: {action}"}

        try:
            side = OrderSide.BUY if action == "buy" else OrderSide.SELL
            order_ticker = ticker.replace("/", "")

            order_request = MarketOrderRequest(
                symbol=order_ticker,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )

            order = self._trading_client.submit_order(order_data=order_request)
            logger.info(f"Alpaca order submitted: {action} {quantity} {ticker} (ID: {order.id})")

            return {
                "order_id": str(order.id),
                "status": str(order.status),
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "client": "alpaca"
            }
        except Exception as e:
            logger.error(f"Alpaca trade execution failed for {ticker}: {e}")
            return {"error": str(e)}

    def get_account_info(self) -> Dict[str, Any]:
        """Get Alpaca account details (balance, buying power)."""
        if not self.is_active:
            return {}
        try:
            account = self._trading_client.get_account()
            return {
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "currency": account.currency,
                "status": account.status
            }
        except Exception as e:
            logger.error(f"Failed to get Alpaca account info: {e}")
            return {}
