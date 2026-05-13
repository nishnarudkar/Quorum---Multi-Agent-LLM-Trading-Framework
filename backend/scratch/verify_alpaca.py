"""
Scratch script to verify Alpaca API connection.
Run this from the backend directory.
"""
import sys
import os
from pathlib import Path

# Add parent dir to sys.path to import config
sys.path.append(str(Path(__file__).parent.parent))

from data.alpaca_provider import AlpacaProvider
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY

def main():
    print("--- Alpaca Verification ---")
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        print("ERROR: Alpaca API keys not found in .env")
        return

    provider = AlpacaProvider()
    if not provider.is_active:
        print("ERROR: AlpacaProvider failed to initialize.")
        return

    print(f"Connection: SUCCESS (Paper={provider.paper})")
    
    # Test Account Info
    account = provider.get_account_info()
    if account:
        print(f"Account Equity: ${account.get('equity')}")
        print(f"Buying Power: ${account.get('buying_power')}")
    else:
        print("FAILED to get account info.")

    # Test Market Data (AAPL)
    print("\nFetching AAPL data...")
    df = provider.get_price_data("AAPL", asset_type="stock", days=5)
    if not df.empty:
        print(f"Latest AAPL Close: {df.iloc[-1]['close']}")
        print("Market Data: SUCCESS")
    else:
        print("Market Data: FAILED")

    print("\nVerification Complete.")

if __name__ == "__main__":
    main()
