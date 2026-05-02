# Quorum

**Multi-Agent LLM Trading Framework**

Quorum is an AI-powered stock and crypto analysis platform that orchestrates 13 specialized LLM agents through a structured multi-stage pipeline. Agents run in parallel, engage in adversarial debates, and pass through a risk committee before producing a final trade recommendation — mimicking the decision structure of a professional trading desk.

---

## Overview

Most AI trading tools reduce the problem to a single prompt. Quorum treats it as a deliberation problem. Each analysis runs through four distinct phases:

| Phase | Agents | Role |
|:------|:------:|:-----|
| Analysis | 4 | Market, sentiment, news, and fundamentals analysts run in parallel |
| Research Debate | 3 | Bull and Bear researchers argue the evidence; a Research Judge delivers a verdict |
| Trade Planning | 1 | Trader agent converts the thesis into a concrete plan with entry, target, stop-loss, and sizing |
| Risk Committee | 5 | Aggressive, Conservative, and Neutral analysts debate the trade; a CRO Judge makes the final call |

The entire flow is compiled into a LangGraph state machine and executed asynchronously, with results streamed to the frontend in real-time via WebSockets.

---

## Architecture

### Agent Pipeline

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

### System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js 16)                        │
│                                                                      │
│   Dashboard        Agents View        Trade History       Settings   │
│   (live data,      (reasoning,        (records,                      │
│    charts,          debates)           P&L)                          │
│    portfolio)                                                         │
│                                                                      │
│                        WebSocket + REST                              │
└──────────────────────────────┬───────────────────────────────────────┘
                               |
┌──────────────────────────────┼───────────────────────────────────────┐
│                         Backend (FastAPI)                            │
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
```

---

## Project Structure

```
quorum/
├── backend/
│   ├── agents/
│   │   ├── analysts/
│   │   │   ├── market_analyst.py          # Technical indicators, price action, momentum
│   │   │   ├── sentiment_analyst.py       # Social sentiment, market mood
│   │   │   ├── news_analyst.py            # Headlines, press releases, filings
│   │   │   └── fundamentals_analyst.py    # P/E, revenue, margins, balance sheet
│   │   ├── researchers/
│   │   │   └── researchers.py             # Bull researcher, Bear researcher, Research Judge
│   │   ├── traders/
│   │   │   ├── trader.py                  # Converts thesis into a validated trade plan
│   │   │   └── risk_debaters.py           # Aggressive, Conservative, Neutral + CRO Judge
│   │   └── confidence.py                  # Adaptive weight scoring + Kelly Criterion sizing
│   ├── api/
│   │   └── main.py                        # FastAPI server — REST + WebSocket endpoints
│   ├── data/
│   │   ├── stock_provider.py              # yfinance wrapper with TTL caching
│   │   ├── crypto_provider.py             # CCXT wrapper with TTL caching
│   │   └── ticker_search.py               # Ticker auto-suggest search
│   ├── graph/
│   │   └── pipeline.py                    # LangGraph state machine with pipeline timeout
│   ├── memory/
│   │   ├── vector_store.py                # ChromaDB semantic memory
│   │   └── trade_db.py                    # SQLite async DB — trades, portfolio, performance
│   ├── models/
│   │   └── schemas.py                     # Pydantic models (reports, debates, signals)
│   ├── utils/
│   │   ├── json_parser.py                 # Resilient JSON extraction from LLM output
│   │   └── event_bus.py                   # Async pub/sub for WebSocket broadcasting
│   ├── config.py                          # Central configuration — all env-var driven
│   ├── llm_client.py                      # Groq client with backoff, timeout, empty-response guard
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                       # Dashboard
│   │   ├── agents/                        # Agent reasoning and debate viewer
│   │   ├── trades/                        # Trade history
│   │   └── settings/                      # Configuration panel
│   ├── components/
│   │   ├── DashboardContent.tsx
│   │   ├── Sidebar.tsx
│   │   ├── AppShell.tsx
│   │   └── ParticleScene.tsx
│   └── public/
└── README.md
```

---

## How the Pipeline Works

### Phase 1 — Parallel Analysis

All four analysts execute simultaneously using LangGraph's fan-out pattern. Each uses a fast `quick_thinker` LLM and produces a structured `AnalystReport` containing sentiment, confidence score, key findings, and raw data. Data is cached per-ticker for 5 minutes to avoid redundant network calls across parallel agents.

| Analyst | Data Source | Key Metrics |
|:--------|:------------|:------------|
| Market | yfinance / CCXT | RSI, MACD, Bollinger Bands, SMA 20/50/200, EMA, volume profile |
| Sentiment | News headlines | Social buzz, fear/greed signals, momentum sentiment |
| News | Headlines and filings | Event impact, catalyst identification, insider transactions |
| Fundamentals | Company financials | P/E, revenue growth, margins, debt-to-equity, free cash flow |

### Phase 2 — Investment Debate

The analyst reports feed into an adversarial debate between a Bull Researcher and a Bear Researcher. The debate runs for a configurable number of rounds. A Research Judge — using a `deep_thinker` LLM — evaluates both sides and produces a verdict (`bullish`, `bearish`, or `neutral`), a confidence score, and a synthesized investment thesis.

### Phase 3 — Trade Planning

The Trader Agent receives the research thesis and converts it into a validated trade plan: action (`buy`, `sell`, `hold`, `short`, `cover`), entry price, target price, stop-loss, and position size. All numeric outputs from the LLM are validated and sanitized — invalid prices, out-of-range confidence scores, and malformed actions are caught and corrected before the signal is passed downstream.

### Phase 4 — Risk Committee

Three risk analysts debate the proposed trade across two rounds. The Risk Judge (CRO) makes the final call — approve, modify, or reject — and sets the final position size. Position sizes are clamped to configured bounds regardless of what the LLM returns.

### Adaptive Confidence

Each agent's historical prediction accuracy is tracked via `ConfidenceTracker`. Weights adjust using an EMA-like formula (`weight = 0.5 + accuracy`). Position sizing uses the Kelly Criterion at half-Kelly, capped at 25% of portfolio.

---

## Tech Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| Agent Framework | LangChain + LangGraph | Agent nodes, state management, parallel DAG execution |
| LLM Provider | Groq | Fast inference — `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` |
| API Server | FastAPI + WebSockets | REST endpoints and real-time streaming |
| Stock Data | yfinance + stockstats | OHLCV, fundamentals, technical indicators, news |
| Crypto Data | CCXT (Binance) | Candles, ticker info, order books |
| Vector Memory | ChromaDB | Semantic search over past trade situations |
| Trade Database | SQLite (aiosqlite) | Trade history, portfolio snapshots, performance metrics |
| Frontend | Next.js 16, TypeScript | App Router, server and client components |
| UI Libraries | Recharts, Three.js, Framer Motion | Charts, 3D effects, animations |
| Styling | Tailwind CSS 4 | Utility-first responsive design |

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- A Groq API key — free at [console.groq.com](https://console.groq.com)

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
# Open .env and set GROQ_API_KEY

python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

### Environment Variables

Copy `backend/.env.example` to `backend/.env`. Only `GROQ_API_KEY` is required — everything else has sensible defaults.

| Variable | Required | Default | Description |
|:---------|:--------:|:-------:|:------------|
| `GROQ_API_KEY` | Yes | — | Free at [console.groq.com](https://console.groq.com) |
| `DEEP_THINK_MODEL` | No | `llama-3.3-70b-versatile` | LLM for debates and final decisions |
| `QUICK_THINK_MODEL` | No | `llama-3.1-8b-instant` | LLM for analyst data processing |
| `LLM_TIMEOUT` | No | `120` | Seconds before an LLM call is cancelled |
| `LLM_CONCURRENCY` | No | `3` | Max parallel LLM calls |
| `PIPELINE_TIMEOUT` | No | `600` | Max seconds for a full analysis run |
| `MAX_POSITION_SIZE` | No | `0.25` | Max portfolio allocation per trade (25%) |
| `AUTO_TRADE_CONFIDENCE` | No | `0.85` | Confidence threshold for auto-approval |
| `ENABLE_HITL` | No | `true` | Enable human-in-the-loop trade approval |
| `INITIAL_CAPITAL` | No | `100000.0` | Starting portfolio value |
| `DATA_CACHE_TTL` | No | `300` | Seconds to cache price/indicator data |
| `TELEGRAM_BOT_TOKEN` | No | — | Telegram alert notifications |
| `DISCORD_WEBHOOK_URL` | No | — | Discord alert webhook |
| `ALPACA_API_KEY` | No | — | Paper trading via Alpaca |

---

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|:------:|:---------|:------------|
| POST | `/analyze` | Run the full 13-agent pipeline for a ticker |
| GET | `/portfolio` | Current portfolio state (cash, positions, P&L) |
| GET | `/portfolio/history` | Portfolio value history for charting |
| GET | `/trades` | Trade history with optional ticker filter |
| GET | `/trades/performance` | Aggregate performance metrics (win rate, P&L, etc.) |
| GET | `/price/{ticker}` | Current price and fundamental data |
| GET | `/price/{ticker}/chart` | OHLCV candlestick data |
| GET | `/indicators/{ticker}` | Technical indicators (RSI, MACD, Bollinger, etc.) |
| GET | `/search` | Ticker auto-suggest search |
| GET | `/agents/accuracy` | Historical accuracy stats per agent |
| GET | `/analysis/history` | Past analysis summaries |
| POST | `/trades/{thread_id}/approve` | Approve or reject a paused HITL trade |
| GET | `/health` | Health check with pipeline and DB status |

### WebSocket

| Endpoint | Description |
|:---------|:------------|
| `/ws/live` | Real-time broadcast of analysis updates, trade signals, and portfolio changes |

Message types: `analysis_start`, `analysis_log`, `analysis_complete`, `analysis_error`, `trade_approved`, `trade_rejected`

---

## Configuration

All parameters are configurable via environment variables. Key pipeline settings in `backend/config.py`:

| Parameter | Default | Description |
|:----------|:-------:|:------------|
| `MAX_DEBATE_ROUNDS` | 2 | Bull/Bear research debate rounds |
| `MAX_RISK_DEBATE_ROUNDS` | 2 | Risk committee debate rounds |
| `ANALYST_TIMEOUT` | 60s | Max seconds per analyst agent |
| `PIPELINE_TIMEOUT` | 600s | Hard timeout for the entire analysis run |
| `AUTO_TRADE_CONFIDENCE` | 0.85 | Auto-approve trades above this threshold |
| `MAX_POSITION_SIZE` | 0.25 | Maximum position size as fraction of portfolio |
| `MIN_POSITION_SIZE` | 0.01 | Minimum position size as fraction of portfolio |
| `DATA_CACHE_TTL` | 300s | How long to cache price and indicator data |
| `LLM_TEMPERATURE` | 0.7 | Controls output variation across LLM calls |

---

## License

MIT
