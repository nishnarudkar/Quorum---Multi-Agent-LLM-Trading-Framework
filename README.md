# Quorum

**Multi-Agent LLM Trading Framework — Powered by LocusFounder**

Quorum is an autonomous AI trading research firm. It employs 13 specialized LLM agents that analyze stocks and crypto through adversarial debates and a risk committee, then sells those reports for $5 USDC per analysis — with no human staff, no overhead, and no sleep.

Built for the [Locus Paygentic Hackathon Week 4 — LocusFounder](https://docs.paywithlocus.com/hackathon) track.

---

## What It Does

Quorum is not a trading tool that assists a human. It **is** the business. When a client submits a ticker and pays $5 USDC via Locus Checkout, Quorum's 13-agent pipeline runs autonomously and delivers a full institutional-grade research report. Revenue flows into the agent's Locus wallet. No human is in the loop.

```
Client pays $5 USDC via Locus Checkout
              |
              v
LocusFounder Agent confirms payment
              |
              v
13-agent pipeline runs (parallel analysis → debate → risk committee)
              |
              v
Report delivered via WebSocket + REST
              |
              v
Revenue logged to agent wallet
```

---

## Agent Pipeline

```
                        User Request (ticker + asset type)
                                       |
              ┌────────────────────────┼────────────────────────┐
              |                        |                         |
       Market Analyst          Sentiment Analyst           News Analyst
       (technicals,            (social buzz,               (headlines,
        price action)           market mood)                filings)
              |                        |                         |
              |              Fundamentals Analyst                |
              |              (P/E, revenue, margins)             |
              |                        |                         |
              └────────────────────────┼─────────────────────────┘
                                       |  parallel fan-out / merge
                                       |
                              Merge Analyst Reports
                                       |
                              Bull Researcher  <──┐
                              (bullish case)      |  debate loop
                                       |          |  (2 rounds)
                              Bear Researcher  ───┘
                              (bearish case)
                                       |
                              Research Judge
                              (verdict + thesis + confidence)
                                       |
                              Trader Agent
                              (action, entry, target, stop-loss, sizing)
                                       |
              ┌────────────────────────┼────────────────────────┐
              |                        |                         |
       Aggressive Analyst      Conservative Analyst      Neutral Analyst  <──┐
              |                        |                         |  risk loop  |
              └────────────────────────┼─────────────────────────┘  (2 rounds) |
                                       |                                        |
                              Risk Judge (CRO)  ──────────────────────────────┘
                              (approve / modify / reject)
                                       |
                              Final Trade Decision
```

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js 16)                        │
│                                                                      │
│   Dashboard        Agents View        Trade History       Settings   │
│                                                                      │
│                        WebSocket + REST                              │
└──────────────────────────────┬───────────────────────────────────────┘
                               |
┌──────────────────────────────┼───────────────────────────────────────┐
│                         Backend (FastAPI)                            │
│                               |                                      │
│   LocusFounder Layer          |                                      │
│   - Agent wallet (USDC/Base)  |                                      │
│   - Checkout sessions ($5)    |                                      │
│   - Revenue tracking          |                                      │
│                               |                                      │
│              API Layer  (REST + WebSocket /ws/live)                  │
│                               |                                      │
│              LangGraph Pipeline  (DAG with conditional edges)        │
│                               |                                      │
│    Analysts     Researchers     Trader     Risk Committee            │
│    (4 nodes)    (Bull, Bear,    (plan      (Aggressive,              │
│                  Judge)         generator)  Conservative,            │
│                                             Neutral, CRO)            │
│                               |                                      │
│    LLM Client    Data Providers    Memory Layer    Confidence        │
│    (Groq +       (yfinance,        (ChromaDB,      Tracker           │
│     backoff)      CCXT)             SQLite)        (Kelly sizing)    │
└──────────────────────────────────────────────────────────────────────┘
                               |
┌──────────────────────────────┼───────────────────────────────────────┐
│                    Locus Infrastructure                              │
│                                                                      │
│   Agent Wallet (USDC on Base)    Checkout SDK (payment sessions)    │
│   Spending Controls              Transaction Audit Log              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
quorum/
├── backend/
│   ├── locus/
│   │   ├── founder_agent.py       # Wallet registration, balance, USDC transfers
│   │   └── checkout.py            # Checkout session creation and payment confirmation
│   ├── agents/
│   │   ├── analysts/
│   │   │   ├── market_analyst.py
│   │   │   ├── sentiment_analyst.py
│   │   │   ├── news_analyst.py
│   │   │   └── fundamentals_analyst.py
│   │   ├── researchers/
│   │   │   └── researchers.py     # Bull, Bear, Research Judge
│   │   ├── traders/
│   │   │   ├── trader.py
│   │   │   └── risk_debaters.py   # Aggressive, Conservative, Neutral, CRO
│   │   └── confidence.py
│   ├── api/
│   │   └── main.py                # FastAPI — REST + WebSocket + Locus endpoints
│   ├── data/
│   │   ├── stock_provider.py
│   │   ├── crypto_provider.py
│   │   └── ticker_search.py
│   ├── graph/
│   │   └── pipeline.py
│   ├── memory/
│   │   ├── vector_store.py
│   │   └── trade_db.py
│   ├── models/
│   │   └── schemas.py
│   ├── utils/
│   │   ├── json_parser.py
│   │   └── event_bus.py
│   ├── config.py
│   ├── llm_client.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── agents/
│   │   ├── trades/
│   │   └── settings/
│   └── components/
├── docs/
│   ├── LOCUS_INTEGRATION.md       # LocusFounder integration guide
│   ├── BUSINESS_PLAN.md           # One-page business plan for hackathon
│   └── API_REFERENCE.md           # Complete API reference
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Groq API key — free at [console.groq.com](https://console.groq.com)
- Locus account — free at [beta.paywithlocus.com](https://beta.paywithlocus.com) (use code `PAYGENTIC`)

### Backend

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Set GROQ_API_KEY in .env
# Optionally set LOCUS_API_KEY — or leave blank for auto-registration

python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

On first startup, if `LOCUS_API_KEY` is not set, the agent will self-register with Locus and save credentials to `backend/db/locus_credentials.json`.

API docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. Only `GROQ_API_KEY` is required.

| Variable | Required | Default | Description |
|:---------|:--------:|:-------:|:------------|
| `GROQ_API_KEY` | Yes | — | Free at [console.groq.com](https://console.groq.com) |
| `LOCUS_API_KEY` | No | — | Pre-provisioned Locus key. Leave blank for auto-registration |
| `LOCUS_ENABLED` | No | `true` | Enable/disable Locus payment integration |
| `ANALYSIS_PRICE_USDC` | No | `5.00` | Price per analysis in USDC |
| `DEEP_THINK_MODEL` | No | `llama-3.3-70b-versatile` | LLM for debates and decisions |
| `QUICK_THINK_MODEL` | No | `llama-3.1-8b-instant` | LLM for analyst processing |
| `LLM_TIMEOUT` | No | `120` | Seconds before LLM call is cancelled |
| `PIPELINE_TIMEOUT` | No | `600` | Max seconds for a full analysis run |
| `MAX_POSITION_SIZE` | No | `0.25` | Max portfolio allocation per trade |
| `AUTO_TRADE_CONFIDENCE` | No | `0.85` | Confidence threshold for auto-approval |
| `INITIAL_CAPITAL` | No | `100000.0` | Starting portfolio value |
| `DATA_CACHE_TTL` | No | `300` | Seconds to cache price/indicator data |

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|:------:|:---------|:------------|
| POST | `/analyze` | Run the full 13-agent pipeline (free, direct) |
| GET | `/portfolio` | Current portfolio state |
| GET | `/portfolio/history` | Portfolio value history |
| GET | `/trades` | Trade history |
| GET | `/trades/performance` | Win rate, P&L, best/worst trade |
| GET | `/price/{ticker}` | Current price and fundamentals |
| GET | `/price/{ticker}/chart` | OHLCV candlestick data |
| GET | `/indicators/{ticker}` | Technical indicators |
| GET | `/search` | Ticker auto-suggest |
| GET | `/agents/accuracy` | Per-agent accuracy stats |
| GET | `/analysis/history` | Past analysis summaries |
| GET | `/health` | Health check with Locus wallet status |

### Locus / LocusFounder Endpoints

| Method | Endpoint | Description |
|:------:|:---------|:------------|
| GET | `/locus/business` | Public storefront — services and pricing |
| GET | `/locus/wallet` | Agent wallet balance (USDC) |
| GET | `/locus/revenue` | Revenue summary across all sessions |
| POST | `/locus/checkout` | Create a $5 USDC checkout session |
| GET | `/locus/checkout/{id}` | Get session state |
| GET | `/locus/checkout/{id}/status` | Poll payment status — auto-triggers analysis on confirmation |
| POST | `/locus/mock-pay/{id}` | Simulate payment (dev/demo only) |

### WebSocket

| Endpoint | Events |
|:---------|:-------|
| `/ws/live` | `analysis_start`, `analysis_log`, `analysis_complete`, `analysis_error`, `trade_approved`, `trade_rejected` |

---

## Paid Analysis Flow

```
1. POST /locus/checkout  { ticker: "AAPL", asset_type: "stock" }
   → Returns { session_id, checkout_url, price_usdc: 5.00 }

2. Client pays $5 USDC at checkout_url

3. GET /locus/checkout/{session_id}/status  (poll every 3s)
   → Returns { paid: true, analysis_triggered: true, analysis_id }

4. Subscribe to /ws/live for real-time analysis progress

5. GET /analysis/history  to retrieve the completed report
```

For development/demo, skip step 2 and call:
```
POST /locus/mock-pay/{session_id}
```

---

## Configuration

| Parameter | Default | Description |
|:----------|:-------:|:------------|
| `MAX_DEBATE_ROUNDS` | 2 | Bull/Bear research debate rounds |
| `MAX_RISK_DEBATE_ROUNDS` | 2 | Risk committee debate rounds |
| `PIPELINE_TIMEOUT` | 600s | Hard timeout for the entire analysis run |
| `AUTO_TRADE_CONFIDENCE` | 0.85 | Auto-approve trades above this threshold |
| `MAX_POSITION_SIZE` | 0.25 | Maximum position size as fraction of portfolio |
| `DATA_CACHE_TTL` | 300s | How long to cache price and indicator data |
| `ANALYSIS_PRICE_USDC` | 5.00 | Price per analysis report in USDC |

---

## Tech Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| Payment Infrastructure | Locus (USDC on Base) | Agent wallet, checkout sessions, revenue |
| Agent Framework | LangChain + LangGraph | Agent nodes, state management, parallel DAG |
| LLM Provider | Groq | Fast inference — llama-3.3-70b + llama-3.1-8b |
| API Server | FastAPI + WebSockets | REST endpoints and real-time streaming |
| Stock Data | yfinance + stockstats | OHLCV, fundamentals, technical indicators |
| Crypto Data | CCXT (Binance) | Candles, ticker info, order books |
| Vector Memory | ChromaDB | Semantic search over past trade situations |
| Trade Database | SQLite (aiosqlite) | Trade history, portfolio, performance metrics |
| Frontend | Next.js 16, TypeScript | App Router, server and client components |
| UI Libraries | Recharts, Three.js, Framer Motion | Charts, 3D effects, animations |
| Styling | Tailwind CSS 4 | Utility-first responsive design |

---

## License

MIT
