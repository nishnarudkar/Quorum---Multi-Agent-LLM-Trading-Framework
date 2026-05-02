"""
Quorum — Ticker Search
Provides fuzzy search over a curated list of popular stocks and crypto pairs.
"""

from __future__ import annotations

# ─── Static ticker database ───────────────────────────────────
# Each entry: (ticker, name, asset_type)
_STOCKS: list[tuple[str, str]] = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corporation"),
    ("GOOGL", "Alphabet Inc."),
    ("GOOG", "Alphabet Inc. Class C"),
    ("AMZN", "Amazon.com Inc."),
    ("NVDA", "NVIDIA Corporation"),
    ("META", "Meta Platforms Inc."),
    ("TSLA", "Tesla Inc."),
    ("BRK-B", "Berkshire Hathaway Inc."),
    ("JPM", "JPMorgan Chase & Co."),
    ("V", "Visa Inc."),
    ("UNH", "UnitedHealth Group Inc."),
    ("XOM", "Exxon Mobil Corporation"),
    ("JNJ", "Johnson & Johnson"),
    ("WMT", "Walmart Inc."),
    ("MA", "Mastercard Inc."),
    ("PG", "Procter & Gamble Co."),
    ("HD", "The Home Depot Inc."),
    ("CVX", "Chevron Corporation"),
    ("MRK", "Merck & Co. Inc."),
    ("LLY", "Eli Lilly and Company"),
    ("ABBV", "AbbVie Inc."),
    ("PEP", "PepsiCo Inc."),
    ("KO", "The Coca-Cola Company"),
    ("AVGO", "Broadcom Inc."),
    ("COST", "Costco Wholesale Corporation"),
    ("MCD", "McDonald's Corporation"),
    ("CSCO", "Cisco Systems Inc."),
    ("CRM", "Salesforce Inc."),
    ("ACN", "Accenture plc"),
    ("AMD", "Advanced Micro Devices Inc."),
    ("NFLX", "Netflix Inc."),
    ("ADBE", "Adobe Inc."),
    ("TMO", "Thermo Fisher Scientific Inc."),
    ("TXN", "Texas Instruments Inc."),
    ("NKE", "Nike Inc."),
    ("QCOM", "Qualcomm Inc."),
    ("INTC", "Intel Corporation"),
    ("ORCL", "Oracle Corporation"),
    ("IBM", "International Business Machines"),
    ("GS", "Goldman Sachs Group Inc."),
    ("MS", "Morgan Stanley"),
    ("BAC", "Bank of America Corporation"),
    ("WFC", "Wells Fargo & Company"),
    ("C", "Citigroup Inc."),
    ("PYPL", "PayPal Holdings Inc."),
    ("SQ", "Block Inc."),
    ("SHOP", "Shopify Inc."),
    ("UBER", "Uber Technologies Inc."),
    ("LYFT", "Lyft Inc."),
    ("SNAP", "Snap Inc."),
    ("TWTR", "Twitter / X Corp."),
    ("SPOT", "Spotify Technology S.A."),
    ("COIN", "Coinbase Global Inc."),
    ("HOOD", "Robinhood Markets Inc."),
    ("PLTR", "Palantir Technologies Inc."),
    ("SNOW", "Snowflake Inc."),
    ("NET", "Cloudflare Inc."),
    ("DDOG", "Datadog Inc."),
    ("ZS", "Zscaler Inc."),
    ("CRWD", "CrowdStrike Holdings Inc."),
    ("PANW", "Palo Alto Networks Inc."),
    ("OKTA", "Okta Inc."),
    ("MDB", "MongoDB Inc."),
    ("TEAM", "Atlassian Corporation"),
    ("ZM", "Zoom Video Communications Inc."),
    ("DOCU", "DocuSign Inc."),
    ("ROKU", "Roku Inc."),
    ("ABNB", "Airbnb Inc."),
    ("DASH", "DoorDash Inc."),
    ("RBLX", "Roblox Corporation"),
    ("U", "Unity Software Inc."),
    ("RIVN", "Rivian Automotive Inc."),
    ("LCID", "Lucid Group Inc."),
    ("F", "Ford Motor Company"),
    ("GM", "General Motors Company"),
    ("BA", "The Boeing Company"),
    ("CAT", "Caterpillar Inc."),
    ("DE", "Deere & Company"),
    ("GE", "General Electric Company"),
    ("MMM", "3M Company"),
    ("HON", "Honeywell International Inc."),
    ("RTX", "Raytheon Technologies"),
    ("LMT", "Lockheed Martin Corporation"),
    ("SPY", "SPDR S&P 500 ETF Trust"),
    ("QQQ", "Invesco QQQ Trust"),
    ("DIA", "SPDR Dow Jones Industrial Average ETF"),
    ("IWM", "iShares Russell 2000 ETF"),
    ("VTI", "Vanguard Total Stock Market ETF"),
    ("VOO", "Vanguard S&P 500 ETF"),
    ("ARK", "ARK Innovation ETF"),
    ("ARKK", "ARK Innovation ETF"),
]

_CRYPTO: list[tuple[str, str]] = [
    ("BTC/USD", "Bitcoin"),
    ("ETH/USD", "Ethereum"),
    ("BNB/USD", "BNB"),
    ("SOL/USD", "Solana"),
    ("XRP/USD", "XRP"),
    ("ADA/USD", "Cardano"),
    ("DOGE/USD", "Dogecoin"),
    ("AVAX/USD", "Avalanche"),
    ("DOT/USD", "Polkadot"),
    ("MATIC/USD", "Polygon"),
    ("LINK/USD", "Chainlink"),
    ("LTC/USD", "Litecoin"),
    ("UNI/USD", "Uniswap"),
    ("ATOM/USD", "Cosmos"),
    ("XLM/USD", "Stellar"),
    ("ALGO/USD", "Algorand"),
    ("VET/USD", "VeChain"),
    ("FIL/USD", "Filecoin"),
    ("AAVE/USD", "Aave"),
    ("SAND/USD", "The Sandbox"),
    ("MANA/USD", "Decentraland"),
    ("AXS/USD", "Axie Infinity"),
    ("SHIB/USD", "Shiba Inu"),
    ("TRX/USD", "TRON"),
    ("ETC/USD", "Ethereum Classic"),
    ("BCH/USD", "Bitcoin Cash"),
    ("NEAR/USD", "NEAR Protocol"),
    ("APT/USD", "Aptos"),
    ("ARB/USD", "Arbitrum"),
    ("OP/USD", "Optimism"),
    ("SUI/USD", "Sui"),
    ("INJ/USD", "Injective"),
    ("IMX/USD", "Immutable X"),
    ("GRT/USD", "The Graph"),
    ("MKR/USD", "Maker"),
    ("SNX/USD", "Synthetix"),
    ("CRV/USD", "Curve DAO Token"),
    ("LDO/USD", "Lido DAO"),
    ("RPL/USD", "Rocket Pool"),
    ("FTM/USD", "Fantom"),
]


def search_tickers(
    query: str,
    asset_type: str = "all",
    limit: int = 8,
) -> list[dict]:
    """Search tickers by symbol or company name.

    Args:
        query: Search string (partial ticker or name)
        asset_type: "stock", "crypto", or "all"
        limit: Max results to return

    Returns:
        List of dicts with ticker, name, asset_type fields
    """
    if not query:
        return []

    q = query.strip().upper()

    candidates: list[dict] = []

    if asset_type in ("stock", "all"):
        for ticker, name in _STOCKS:
            candidates.append({"ticker": ticker, "name": name, "asset_type": "stock"})

    if asset_type in ("crypto", "all"):
        for ticker, name in _CRYPTO:
            candidates.append({"ticker": ticker, "name": name, "asset_type": "crypto"})

    results: list[tuple[int, dict]] = []

    for item in candidates:
        score = _score(q, item["ticker"], item["name"])
        if score > 0:
            results.append((score, item))

    # Sort by score descending, then alphabetically by ticker
    results.sort(key=lambda x: (-x[0], x[1]["ticker"]))

    return [item for _, item in results[:limit]]


def _score(query: str, ticker: str, name: str) -> int:
    """Return a relevance score. Higher is more relevant. 0 means no match."""
    ticker_upper = ticker.upper()
    name_upper = name.upper()

    # Exact ticker match
    if query == ticker_upper:
        return 100

    # Ticker starts with query
    if ticker_upper.startswith(query):
        return 80

    # Query is contained in ticker
    if query in ticker_upper:
        return 60

    # Name starts with query
    if name_upper.startswith(query):
        return 50

    # Any word in the name starts with query
    if any(word.startswith(query) for word in name_upper.split()):
        return 40

    # Query is contained anywhere in the name
    if query in name_upper:
        return 20

    return 0
