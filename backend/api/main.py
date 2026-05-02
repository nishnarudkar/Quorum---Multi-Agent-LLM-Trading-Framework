"""
Quorum — FastAPI Server
REST API + WebSocket for the trading agents pipeline.
"""

import asyncio
import json
import math
import traceback
import logging
import uuid
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from config import CORS_ORIGINS, API_HOST, API_PORT, INITIAL_CAPITAL
from graph.pipeline import TradingPipeline
from memory.trade_db import TradeDB
from data.stock_provider import StockProvider
from data.crypto_provider import CryptoProvider
from data.ticker_search import search_tickers
from utils.event_bus import event_bus
from locus.founder_agent import founder_agent
from locus.checkout import (
    create_checkout_session,
    confirm_payment,
    get_session,
    mark_fulfilled,
    mock_confirm,
    get_revenue_summary,
)

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-22s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("quorum.api")


# ─── Request Models ───────────────────────────────────────────

VALID_ANALYSTS = {"market", "sentiment", "news", "fundamentals"}
VALID_ASSET_TYPES = {"stock", "crypto"}


class AnalyzeRequest(BaseModel):
    ticker: str
    asset_type: str = "stock"
    trade_date: Optional[str] = None
    selected_analysts: Optional[list[str]] = None

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not v or len(v) > 20:
            raise ValueError("Ticker must be 1–20 characters")
        return v

    @field_validator("asset_type")
    @classmethod
    def validate_asset_type(cls, v: str) -> str:
        if v not in VALID_ASSET_TYPES:
            raise ValueError(f"asset_type must be one of {VALID_ASSET_TYPES}")
        return v

    @field_validator("selected_analysts")
    @classmethod
    def validate_analysts(cls, v):
        if v is None:
            return v
        invalid = set(v) - VALID_ANALYSTS
        if invalid:
            raise ValueError(f"Unknown analysts: {invalid}. Valid: {VALID_ANALYSTS}")
        return v


class TradeApprovalRequest(BaseModel):
    approval: str = "approve"

    @field_validator("approval")
    @classmethod
    def validate_approval(cls, v: str) -> str:
        if v.lower() not in ("approve", "reject"):
            raise ValueError("approval must be 'approve' or 'reject'")
        return v.lower()


class CheckoutRequest(BaseModel):
    ticker: str
    asset_type: str = "stock"
    selected_analysts: Optional[list[str]] = None

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not v or len(v) > 20:
            raise ValueError("Ticker must be 1–20 characters")
        return v

    @field_validator("asset_type")
    @classmethod
    def validate_asset_type(cls, v: str) -> str:
        if v not in VALID_ASSET_TYPES:
            raise ValueError(f"asset_type must be one of {VALID_ASSET_TYPES}")
        return v


# ─── Global State ─────────────────────────────────────────────

pipeline: Optional[TradingPipeline] = None
trade_db: Optional[TradeDB] = None
stock_provider = StockProvider()
crypto_provider = CryptoProvider()
active_connections: list[WebSocket] = []


# ─── Lifespan ─────────────────────────────────────────────────

async def broadcast_subscriber(message: dict):
    await broadcast(message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline, trade_db

    trade_db = TradeDB()
    await trade_db.initialize()

    pipeline = TradingPipeline()
    await pipeline.initialize()

    # Initialize LocusFounder agent (wallet + credentials)
    await founder_agent.initialize()

    event_bus.subscribe(broadcast_subscriber)
    logger.info("Quorum API started")

    yield

    event_bus.unsubscribe(broadcast_subscriber)
    await founder_agent.close()
    logger.info("Quorum API shutting down")


# ─── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="Quorum API",
    description="Multi-Agent LLM Trading Framework",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── WebSocket ────────────────────────────────────────────────

async def broadcast(message: dict):
    """Broadcast to all connected WebSocket clients, pruning dead connections."""
    if not active_connections:
        return
    text = json.dumps(message, default=str)
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_text(text)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_connections:
            active_connections.remove(ws)


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket connected ({len(active_connections)} total)")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected ({len(active_connections)} remaining)")


# ─── Core Endpoints ───────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "Quorum API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "pipeline_ready": pipeline is not None,
        "db_ready": trade_db is not None,
        "locus_ready": founder_agent.is_ready,
        "locus_wallet": founder_agent.wallet_address,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/search")
async def search_ticker(
    q: str = Query(min_length=1, max_length=20),
    asset_type: str = Query(default="all"),
    limit: int = Query(default=8, le=20),
):
    """Ticker auto-suggest search."""
    return search_tickers(q, asset_type=asset_type, limit=limit)


# ─── Analysis ─────────────────────────────────────────────────

@app.post("/analyze")
async def analyze_ticker(request: AnalyzeRequest):
    """Run the full 13-agent pipeline for a ticker."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    analysis_id = str(uuid.uuid4())

    logger.info(f"Analysis started — {request.ticker} ({request.asset_type}) [{analysis_id[:8]}]")

    await broadcast({
        "type": "analysis_start",
        "analysis_id": analysis_id,
        "data": {"ticker": request.ticker, "asset_type": request.asset_type},
    })

    try:
        import time
        start_time = time.time()

        async def log_callback(agent: str, stage: str, message: str, details: str = ""):
            await broadcast({
                "type": "analysis_log",
                "analysis_id": analysis_id,
                "data": {
                    "agent": agent,
                    "stage": stage,
                    "message": message,
                    "details": (details or "")[:500],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            })

        result = await pipeline.analyze(
            ticker=request.ticker,
            asset_type=request.asset_type,
            trade_date=request.trade_date or datetime.utcnow().strftime("%Y-%m-%d"),
            log_callback=log_callback,
            selected_analysts=request.selected_analysts,
            analysis_id=analysis_id,
        )

        elapsed = time.time() - start_time
        trade_signal = result.get("trade_signal")
        approved = result.get("trade_approved", False)

        if trade_signal:
            s = trade_signal if isinstance(trade_signal, dict) else trade_signal.model_dump()
            logger.info(
                f"Analysis complete — {request.ticker} in {elapsed:.1f}s | "
                f"action={s.get('action')} conf={s.get('confidence')} "
                f"approved={'YES' if approved else 'NO'}"
            )

        serialized = _serialize_state(result)

        if trade_db:
            await trade_db.save_analysis_log(
                request.ticker,
                request.asset_type,
                request.trade_date or datetime.utcnow().strftime("%Y-%m-%d"),
                serialized,
            )

            # If trade was approved, record it in trade history
            if approved and trade_signal:
                s = trade_signal if isinstance(trade_signal, dict) else trade_signal.model_dump()
                action = s.get("action")
                if hasattr(action, "value"):
                    action = action.value
                if action and action != "hold":
                    await trade_db.insert_trade(
                        ticker=request.ticker,
                        asset_type=request.asset_type,
                        action=str(action),
                        quantity=0.0,  # Quantity requires execution layer
                        price=float(s.get("entry_price") or 0),
                        confidence=float(s.get("confidence") or 0),
                        reasoning=str(s.get("reasoning") or "")[:1000],
                        approval_status="approved",
                    )

        await broadcast({"type": "analysis_complete", "data": serialized})
        return serialized

    except TimeoutError as e:
        msg = str(e)
        logger.error(f"Pipeline timeout for {request.ticker}: {msg}")
        await broadcast({"type": "analysis_error", "data": {"error": msg}})
        raise HTTPException(status_code=504, detail=msg)

    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = any(kw in error_str for kw in (
            "rate_limit", "rate limit", "429", "too many requests", "resource_exhausted"
        ))

        if is_rate_limit:
            msg = (
                "Groq API rate limit reached. The system retried automatically but the limit "
                "persists. Please wait 1–2 minutes before trying again."
            )
            logger.warning(f"Rate limit for {request.ticker}: {e}")
            await broadcast({"type": "analysis_error", "data": {"error": msg, "retry_after": 60}})
            raise HTTPException(status_code=429, detail=msg)

        traceback.print_exc()
        msg = f"Analysis failed: {e}"
        logger.error(msg)
        await broadcast({"type": "analysis_error", "data": {"error": msg}})
        raise HTTPException(status_code=500, detail=msg)


# ─── Portfolio ────────────────────────────────────────────────

@app.get("/portfolio")
async def get_portfolio():
    """Get current portfolio state."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return await trade_db.get_current_portfolio()


@app.get("/portfolio/history")
async def get_portfolio_history(limit: int = Query(default=100, le=500)):
    """Get portfolio value history for charting."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return await trade_db.get_portfolio_history(limit=limit)


# ─── Trades ───────────────────────────────────────────────────

@app.get("/trades")
async def get_trades(
    ticker: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    """Get trade history."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return await trade_db.get_trades(ticker=ticker, limit=limit)


@app.get("/trades/performance")
async def get_performance():
    """Get aggregate performance metrics."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return await trade_db.get_performance_metrics()


# ─── Price & Indicators ───────────────────────────────────────

@app.get("/price/{ticker}")
async def get_price(ticker: str, asset_type: str = "stock"):
    """Get current price and fundamental data."""
    ticker = ticker.strip().upper()
    if asset_type == "crypto":
        return {
            "ticker": ticker,
            "price": crypto_provider.get_current_price(ticker),
            "info": crypto_provider.get_ticker_info(ticker),
        }
    return {
        "ticker": ticker,
        "price": stock_provider.get_current_price(ticker),
        "fundamentals": stock_provider.get_fundamentals(ticker),
    }


@app.get("/price/{ticker}/chart")
async def get_price_chart(ticker: str, asset_type: str = "stock"):
    """Get OHLCV data for candlestick charts."""
    ticker = ticker.strip().upper()
    try:
        if asset_type == "crypto":
            df = crypto_provider.get_price_data(ticker)
            col_map = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
        else:
            df = stock_provider.get_price_data(ticker)
            col_map = {"Open": "Open", "High": "High", "Low": "Low", "Close": "Close", "Volume": "Volume"}

        if df.empty:
            return []

        records = []
        for date, row in df.iterrows():
            o = row.get("Open") or row.get("open")
            h = row.get("High") or row.get("high")
            lo = row.get("Low") or row.get("low")
            c = row.get("Close") or row.get("close")
            v = row.get("Volume") or row.get("volume")
            if any(x is None for x in [o, h, lo, c]):
                continue
            records.append({
                "time": date.strftime("%Y-%m-%d"),
                "open": round(float(o), 4),
                "high": round(float(h), 4),
                "low": round(float(lo), 4),
                "close": round(float(c), 4),
                "volume": int(v) if v is not None else None,
            })
        return records
    except Exception as e:
        logger.error(f"Chart data error for {ticker}: {e}")
        return []


@app.get("/indicators/{ticker}")
async def get_indicators(ticker: str, asset_type: str = "stock"):
    """Get technical indicators."""
    ticker = ticker.strip().upper()
    if asset_type == "crypto":
        return crypto_provider.get_technical_indicators(ticker)
    return stock_provider.get_technical_indicators(ticker)


# ─── Analysis History ─────────────────────────────────────────

@app.get("/analysis/history")
async def get_analysis_history(
    ticker: Optional[str] = None,
    limit: int = Query(default=20, le=100),
):
    """Get past analysis summaries."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        return await trade_db.get_analysis_logs(ticker=ticker, limit=limit)
    except Exception as e:
        logger.error(f"Analysis history error: {e}")
        return []


# ─── HITL Trade Approval ──────────────────────────────────────

@app.post("/trades/{thread_id}/approve")
async def approve_trade(thread_id: str, request: TradeApprovalRequest):
    """Approve or reject a paused trade (HITL)."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    state = await pipeline.get_state(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No analysis found for thread {thread_id}")
    if state.get("status") != "interrupted":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis is not waiting for approval (status: {state.get('status')})",
        )

    logger.info(f"Trade approval for {thread_id}: {request.approval}")

    try:
        from langgraph.types import Command
        config = {"configurable": {"thread_id": thread_id}}
        result = await pipeline.graph.ainvoke(Command(resume=request.approval), config=config)
        serialized = _serialize_state(result)

        event_type = "trade_approved" if request.approval == "approve" else "trade_rejected"
        await broadcast({"type": event_type, "data": {"thread_id": thread_id, **serialized}})

        return {"status": "ok", "thread_id": thread_id, "decision": request.approval, **serialized}

    except Exception as e:
        logger.error(f"Error resuming thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume: {e}")


@app.get("/analysis/{thread_id}/state")
async def get_analysis_state(thread_id: str):
    """Get the current state of an analysis pipeline thread."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    state = await pipeline.get_state(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No analysis found for thread {thread_id}")
    return _serialize_state(state)


# ─── Agent Accuracy ───────────────────────────────────────────

@app.get("/agents/accuracy")
async def get_agent_accuracy():
    """Get historical accuracy stats for all agents."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return await trade_db.get_agent_accuracy()


# ─── Locus / LocusFounder Endpoints ──────────────────────────

@app.get("/locus/business")
async def get_business_info():
    """Public storefront — describes Quorum's services and pricing."""
    return founder_agent.get_business_info()


@app.get("/locus/wallet")
async def get_wallet():
    """Get the agent's Locus wallet balance and address."""
    return await founder_agent.get_balance()


@app.get("/locus/revenue")
async def get_revenue():
    """Get revenue summary across all checkout sessions."""
    return get_revenue_summary()


@app.post("/locus/checkout")
async def create_checkout(request: CheckoutRequest):
    """
    Create a $5 USDC checkout session for a paid analysis.

    Returns a checkout URL the client uses to pay.
    Once payment is confirmed, call /locus/checkout/{session_id}/status
    to poll for confirmation, then /analyze will run automatically.
    """
    session = await create_checkout_session(
        ticker=request.ticker,
        asset_type=request.asset_type,
        selected_analysts=request.selected_analysts,
    )
    return session


@app.get("/locus/checkout/{session_id}")
async def get_checkout_session(session_id: str):
    """Get the current state of a checkout session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/locus/checkout/{session_id}/status")
async def poll_payment_status(session_id: str):
    """
    Poll payment status for a checkout session.
    Returns paid=true once the USDC payment is confirmed.
    If paid, automatically triggers the analysis pipeline.
    """
    result = await confirm_payment(session_id)

    # Auto-trigger analysis once payment is confirmed
    if result.get("paid") and result.get("status") != "fulfilled":
        session = get_session(session_id)
        if session and pipeline:
            ticker = session["ticker"]
            asset_type = session["asset_type"]
            analysis_id = str(uuid.uuid4())

            logger.info(
                f"Payment confirmed for {ticker} — triggering analysis "
                f"[session: {session_id[:8]}]"
            )

            # Run analysis in background so the poll response returns immediately
            asyncio.create_task(
                _run_paid_analysis(
                    session_id=session_id,
                    ticker=ticker,
                    asset_type=asset_type,
                    analysis_id=analysis_id,
                )
            )
            result["analysis_triggered"] = True
            result["analysis_id"] = analysis_id

    return result


async def _run_paid_analysis(
    session_id: str,
    ticker: str,
    asset_type: str,
    analysis_id: str,
):
    """Background task: run the full pipeline after payment is confirmed."""
    try:
        await broadcast({
            "type": "analysis_start",
            "analysis_id": analysis_id,
            "data": {
                "ticker": ticker,
                "asset_type": asset_type,
                "paid": True,
                "session_id": session_id,
            },
        })

        result = await pipeline.analyze(
            ticker=ticker,
            asset_type=asset_type,
            trade_date=datetime.utcnow().strftime("%Y-%m-%d"),
            analysis_id=analysis_id,
        )

        serialized = _serialize_state(result)

        if trade_db:
            await trade_db.save_analysis_log(
                ticker, asset_type,
                datetime.utcnow().strftime("%Y-%m-%d"),
                {**serialized, "session_id": session_id},
            )

        mark_fulfilled(session_id, analysis_id)

        await broadcast({
            "type": "analysis_complete",
            "analysis_id": analysis_id,
            "session_id": session_id,
            "data": serialized,
        })

        logger.info(
            f"Paid analysis complete — {ticker} | session: {session_id[:8]} | "
            f"analysis: {analysis_id[:8]}"
        )

    except Exception as e:
        logger.error(f"Paid analysis failed for session {session_id}: {e}")
        await broadcast({
            "type": "analysis_error",
            "analysis_id": analysis_id,
            "session_id": session_id,
            "data": {"error": str(e)},
        })


@app.post("/locus/mock-pay/{session_id}")
async def mock_pay(session_id: str):
    """
    Development endpoint: simulate a USDC payment for a checkout session.
    Only works for mock/dev sessions. Do not use in production.
    """
    confirmed = mock_confirm(session_id)
    if not confirmed:
        raise HTTPException(
            status_code=400,
            detail="Session not found, already paid, or not a mock session",
        )
    return {
        "success": True,
        "message": "Mock payment confirmed",
        "session_id": session_id,
        "next": f"/locus/checkout/{session_id}/status",
    }


# ─── Helpers ──────────────────────────────────────────────────

def _serialize_state(state: dict) -> dict:
    """Serialize pipeline state for JSON, handling Pydantic models, enums, NaN/Inf."""
    import enum

    def _sanitize(obj):
        if obj is None:
            return None
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, float):
            return None if (math.isnan(obj) or math.isinf(obj)) else obj
        if isinstance(obj, int):
            return obj
        if isinstance(obj, str):
            return obj
        if isinstance(obj, enum.Enum):
            return obj.value
        if hasattr(obj, "model_dump"):
            return _sanitize(obj.model_dump())
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_sanitize(v) for v in obj]
        return str(obj)

    return {k: _sanitize(v) for k, v in state.items()}


# ─── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)
