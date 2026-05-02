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
│   │   │   ├── trader.py                  # Converts thesis into a trade plan
│   │   │   └── risk_debaters.py           # Aggressive, Conservative, Neutral + CRO Judge
│   │   └── confidence.py                  # Adaptive weight scoring + Kelly Criterion sizing
│   ├── api/
│   │   └── main.py                        # FastAPI server — REST + WebSocket endpoints
│   ├── data/
│   │   ├── stock_provider.py              # yfinance wrapper (OHLCV, fundamentals, technicals)
│   │   └── crypto_provider.py             # CCXT wrapper (Binance data, order books)
│   ├── graph/
│   │   └── pipeline.py                    # LangGraph state machine
│   ├── memory/
│   │   ├── vector_store.py                # ChromaDB semantic memory
│   │   └── trade_db.py                    # SQLite async DB for trades and portfolio
│   ├── models/
│   │   └── schemas.py                     # Pydantic models (reports, debates, signals)
│   ├── utils/
│   │   └── json_parser.py                 # Resilient JSON extraction from LLM output
│   ├── config.py                          # Central configuration
│   ├── llm_client.py                      # Groq client with rate-limit backoff
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

All four analysts execute simultaneously using LangGraph's fan-out pattern. Each uses a fast `quick_thinker` LLM and produces a structured `AnalystReport` containing sentiment, confidence score, key findings, and raw data.

| Analyst | Data Source | Key Metrics |
|:--------|:------------|:------------|
| Market | yfinance / CCXT | RSI, MACD, Bollinger Bands, SMA crossovers, volume profile |
| Sentiment | Market mood analysis | Social buzz, fear/greed signals, momentum sentiment |
| News | Headlines and filings | Event impact, catalyst identification, headline sentiment |
| Fundamentals | Company financials | P/E, revenue growth, margins, debt-to-equity, cash flow |

### Phase 2 — Investment Debate

The analyst reports feed into an adversarial debate between a Bull Researcher and a Bear Researcher. The debate runs for a configurable number of rounds. A Research Judge — using a `deep_thinker` LLM — then evaluates both sides and produces a verdict (`bullish`, `bearish`, or `neutral`), a confidence score, and a synthesized investment thesis.

### Phase 3 — Trade Planning

The Trader Agent receives the research thesis and converts it into an actionable trade plan: action (`buy`, `sell`, `hold`, `short`, `cover`), entry price, target price, stop-loss, and position size. It also queries vector memory for similar past trades to avoid repeating prior mistakes.

### Phase 4 — Risk Committee

Three risk analysts debate the proposed trade across two rounds. The Risk Judge (CRO) then makes the final call — approve, modify, or reject — and sets the final position size and stop-loss parameters.

### Adaptive Confidence

Each agent's historical prediction accuracy is tracked via `ConfidenceTracker`. Weights adjust using an EMA-like formula (`weight = 0.5 + accuracy`). Position sizing uses the Kelly Criterion at half-Kelly, capped at 25% of portfolio.

---

## Tech Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| Agent Framework | LangChain + LangGraph | Agent nodes, state management, parallel DAG execution |
| LLM Provider | Groq | Fast inference with rate-limit-resilient wrapper |
| API Server | FastAPI + WebSockets | REST endpoints and real-time streaming |
| Stock Data | yfinance + stockstats | OHLCV, fundamentals, technical indicators, news |
| Crypto Data | CCXT (Binance) | Candles, ticker info, order books |
| Vector Memory | ChromaDB | Semantic search over past trade situations |
| Trade Database | SQLite (aiosqlite) | Trade history, portfolio snapshots, agent accuracy |
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

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Open .env and add your GROQ_API_KEY

python -m uvicorn api.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive docs are available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

### Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the values below.

| Variable | Required | Description |
|:---------|:--------:|:------------|
| `GROQ_API_KEY` | Yes | Free at [console.groq.com](https://console.groq.com) |
| `ALPACA_API_KEY` | No | Paper trading via [Alpaca](https://alpaca.markets) |
| `ALPACA_SECRET_KEY` | No | Alpaca secret key |
| `TELEGRAM_BOT_TOKEN` | No | Telegram alert notifications |
| `DISCORD_WEBHOOK_URL` | No | Discord alert webhook |

---

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|:------:|:---------|:------------|
| POST | `/analyze` | Run the full 13-agent pipeline for a ticker |
| GET | `/portfolio` | Current portfolio state (cash, positions, P&L) |
| GET | `/portfolio/history` | Portfolio value history for charting |
| GET | `/trades` | Trade history with optional ticker filter |
| GET | `/price/{ticker}` | Current price and fundamental data |
| GET | `/indicators/{ticker}` | Technical indicators (RSI, MACD, Bollinger, etc.) |
| GET | `/health` | Health check |

### WebSocket

| Endpoint | Description |
|:---------|:------------|
| `/ws/live` | Real-time broadcast of analysis updates, trade signals, and portfolio changes |

Message types: `analysis_update`, `trade_signal`, `portfolio_update`, `agent_reasoning`

---

## Configuration

Key pipeline parameters in `backend/config.py`:

| Parameter | Default | Description |
|:----------|:-------:|:------------|
| `MAX_DEBATE_ROUNDS` | 2 | Bull/Bear research debate rounds |
| `MAX_RISK_DEBATE_ROUNDS` | 2 | Risk committee debate rounds |
| `ANALYST_TIMEOUT` | 60 | Max seconds per analyst agent |
| `AUTO_TRADE_CONFIDENCE` | 0.85 | Auto-approve trades above this confidence threshold |
| `APPROVAL_QUEUE_TTL` | 300 | Seconds before a pending approval expires |
| `LLM_TEMPERATURE` | 0.7 | Controls output variation across LLM calls |

---

## License

MIT
