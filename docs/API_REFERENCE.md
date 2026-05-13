# Quorum API Reference

Base URL (production): `https://quorum-backend-74691596771.us-central1.run.app`

Base URL (local): `http://localhost:8000`

Interactive docs: `https://quorum-backend-74691596771.us-central1.run.app/docs`

---

## Authentication

No authentication required for the current version. All endpoints are open.

---

## Core Endpoints

### GET /

Health and version info.

```json
{
  "name": "Quorum API",
  "version": "1.0.0",
  "status": "running",
  "timestamp": "2025-05-03T10:00:00"
}
```

---

### GET /health

System health check including Locus wallet status.

```json
{
  "status": "healthy",
  "pipeline_ready": true,
  "db_ready": true,
  "locus_ready": true,
  "locus_wallet": "0x...",
  "timestamp": "2025-05-03T10:00:00"
}
```

---

### POST /analyze

Run the full 13-agent pipeline directly (no payment required).

**Request:**
```json
{
  "ticker": "AAPL",
  "asset_type": "stock",
  "trade_date": "2025-05-03",
  "selected_analysts": ["market", "sentiment", "news", "fundamentals"]
}
```

| Field | Type | Required | Description |
|:------|:-----|:--------:|:------------|
| `ticker` | string | Yes | Stock symbol or crypto pair (e.g. `BTC/USD`) |
| `asset_type` | string | No | `stock` or `crypto`. Default: `stock` |
| `trade_date` | string | No | ISO date. Default: today |
| `selected_analysts` | array | No | Subset of analysts to run. Default: all four |

**Response:** Full pipeline state including all analyst reports, debate transcripts, trade signal, and final decision.

**Errors:**
- `429` — Groq rate limit. Wait 1–2 minutes.
- `504` — Pipeline timeout (>600s).
- `503` — Pipeline not initialized.

---

### GET /search

Ticker auto-suggest search.

**Query params:**
- `q` (required) — Search string, 1–20 chars
- `asset_type` — `stock`, `crypto`, or `all`. Default: `all`
- `limit` — Max results, 1–20. Default: 8

**Response:**
```json
[
  { "ticker": "AAPL", "name": "Apple Inc.", "asset_type": "stock" },
  { "ticker": "AMZN", "name": "Amazon.com Inc.", "asset_type": "stock" }
]
```

---

## Portfolio

### GET /portfolio

Current portfolio state.

```json
{
  "cash": 100000.0,
  "equity": 0.0,
  "total_value": 100000.0,
  "positions": [],
  "daily_pnl": 0.0,
  "total_pnl": 0.0
}
```

---

### GET /portfolio/history

Portfolio value history for charting.

**Query params:**
- `limit` — Max snapshots, 1–500. Default: 100

---

## Trades

### GET /trades

Trade history.

**Query params:**
- `ticker` — Filter by ticker symbol
- `limit` — Max records, 1–200. Default: 50

---

### GET /trades/performance

Aggregate performance metrics.

```json
{
  "total_trades": 12,
  "winning_trades": 8,
  "losing_trades": 4,
  "win_rate": 0.6667,
  "total_pnl": 2340.50,
  "avg_trade_pnl": 195.04,
  "best_trade": 890.00,
  "worst_trade": -210.00
}
```

---

## Price & Indicators

### GET /price/{ticker}

Current price and fundamental data.

**Query params:**
- `asset_type` — `stock` or `crypto`. Default: `stock`

---

### GET /price/{ticker}/chart

OHLCV candlestick data for charting.

**Query params:**
- `asset_type` — `stock` or `crypto`. Default: `stock`

**Response:**
```json
[
  {
    "time": "2025-04-01",
    "open": 172.50,
    "high": 175.20,
    "low": 171.80,
    "close": 174.10,
    "volume": 52341200
  }
]
```

---

### GET /indicators/{ticker}

Technical indicators.

**Query params:**
- `asset_type` — `stock` or `crypto`. Default: `stock`

**Response (stock):**
```json
{
  "ticker": "AAPL",
  "current_price": 174.10,
  "rsi_14": 58.3,
  "macd": 1.24,
  "macd_signal": 0.98,
  "macd_hist": 0.26,
  "sma_20": 171.50,
  "sma_50": 168.20,
  "sma_200": 162.40,
  "bollinger_upper": 178.90,
  "bollinger_middle": 171.50,
  "bollinger_lower": 164.10,
  "price_change_1d": 0.82,
  "price_change_5d": 2.14,
  "price_change_1m": 5.30
}
```

---

## Analysis History

### GET /analysis/history

Past analysis summaries (without full state JSON).

**Query params:**
- `ticker` — Filter by ticker
- `limit` — Max records, 1–100. Default: 20

---

### GET /analysis/{thread_id}/state

Full state of a specific analysis pipeline run.

---

## HITL Trade Approval

### POST /trades/{thread_id}/approve

Approve or reject a paused trade (human-in-the-loop).

**Request:**
```json
{ "approval": "approve" }
```

`approval` must be `"approve"` or `"reject"`.

---

## Agents

### GET /agents/accuracy

Historical accuracy stats per agent.

```json
[
  {
    "agent_name": "market_analyst",
    "total_predictions": 45,
    "correct_predictions": 31,
    "accuracy": 0.6889,
    "weight": 1.189,
    "last_updated": "2025-05-03T09:45:00"
  }
]
```

---

## Locus / LocusFounder

### GET /locus/business

Public storefront — machine-readable service catalog.

```json
{
  "name": "Quorum Trading Intelligence",
  "description": "Autonomous AI trading research firm...",
  "services": [
    {
      "id": "analysis_single",
      "name": "Single Analysis Report",
      "description": "Full 13-agent analysis...",
      "price_usdc": 5.00,
      "delivery": "~3 minutes"
    }
  ],
  "wallet_address": "0x...",
  "payment_currency": "USDC",
  "payment_chain": "Base"
}
```

---

### GET /locus/wallet

Agent wallet balance.

```json
{
  "balance_usdc": 10.00,
  "wallet_address": "0x...",
  "currency": "USDC",
  "chain": "Base"
}
```

---

### GET /locus/revenue

Revenue summary across all checkout sessions.

```json
{
  "total_sessions": 6,
  "paid_sessions": 5,
  "fulfilled_sessions": 4,
  "pending_sessions": 1,
  "total_revenue_usdc": 25.00,
  "fulfilled_revenue_usdc": 20.00,
  "price_per_analysis_usdc": 5.00
}
```

---

### POST /locus/checkout

Create a $5 USDC checkout session.

**Request:**
```json
{
  "ticker": "AAPL",
  "asset_type": "stock",
  "selected_analysts": ["market", "news"]
}
```

**Response:**
```json
{
  "session_id": "abc123...",
  "ticker": "AAPL",
  "asset_type": "stock",
  "price_usdc": 5.00,
  "checkout_url": "https://checkout.paywithlocus.com/...",
  "status": "pending",
  "created_at": "2025-05-03T10:00:00",
  "expires_at": "2025-05-03T10:30:00"
}
```

---

### GET /locus/checkout/{session_id}

Get session state.

---

### GET /locus/checkout/{session_id}/status

Poll payment status. Returns `paid: true` once confirmed. Automatically triggers the analysis pipeline on first confirmation.

**Response (paid):**
```json
{
  "paid": true,
  "status": "paid",
  "analysis_triggered": true,
  "analysis_id": "xyz789...",
  "session_id": "abc123...",
  "ticker": "AAPL",
  "tx_hash": "0x..."
}
```

---

### POST /locus/mock-pay/{session_id}

Simulate a USDC payment for development and demo purposes. Only works for mock sessions.

**Response:**
```json
{
  "success": true,
  "message": "Mock payment confirmed",
  "session_id": "abc123...",
  "next": "/locus/checkout/abc123.../status"
}
```

---

## WebSocket

### WS /ws/live

Real-time event stream.

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live');
```

**Ping/pong:**
```json
// Send
{ "type": "ping" }
// Receive
{ "type": "pong" }
```

**Event types:**

| Type | Description |
|:-----|:------------|
| `analysis_start` | Pipeline started for a ticker |
| `analysis_log` | Per-agent progress update |
| `analysis_complete` | Full pipeline result |
| `analysis_error` | Pipeline failed |
| `trade_approved` | HITL trade approved |
| `trade_rejected` | HITL trade rejected |

**analysis_log payload:**
```json
{
  "type": "analysis_log",
  "analysis_id": "abc123...",
  "data": {
    "agent": "Market Analyst",
    "stage": "completed",
    "message": "Done — Sentiment: bullish",
    "details": "RSI at 58, MACD positive crossover...",
    "timestamp": "2025-05-03T10:01:30"
  }
}
```

---

## Error Codes

| Code | Meaning |
|:----:|:--------|
| 400 | Bad request — invalid parameters |
| 404 | Resource not found |
| 429 | Groq API rate limit — wait 1–2 minutes |
| 500 | Internal server error |
| 503 | Service not initialized |
| 504 | Pipeline timeout (>600s) |
