"""
Quorum — Locus Checkout
Creates and manages USDC payment sessions for analysis requests.
Clients pay $5 USDC per analysis via Locus Checkout before the pipeline runs.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx

from locus.founder_agent import founder_agent, LOCUS_BETA_API

logger = logging.getLogger("quorum.locus.checkout")

# In-memory session store — maps session_id → session data
# In production this would be persisted to the DB
_sessions: dict[str, dict] = {}

ANALYSIS_PRICE_USDC = 5.00
SESSION_TTL_MINUTES = 30


class CheckoutSession:
    """Represents a pending or completed payment session."""

    def __init__(
        self,
        session_id: str,
        ticker: str,
        asset_type: str,
        price_usdc: float,
        locus_session_id: Optional[str] = None,
        checkout_url: Optional[str] = None,
    ):
        self.session_id = session_id
        self.ticker = ticker
        self.asset_type = asset_type
        self.price_usdc = price_usdc
        self.locus_session_id = locus_session_id
        self.checkout_url = checkout_url
        self.status = "pending"          # pending | paid | expired | fulfilled
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=SESSION_TTL_MINUTES)
        self.paid_at: Optional[datetime] = None
        self.analysis_id: Optional[str] = None
        self.tx_hash: Optional[str] = None

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "ticker": self.ticker,
            "asset_type": self.asset_type,
            "price_usdc": self.price_usdc,
            "locus_session_id": self.locus_session_id,
            "checkout_url": self.checkout_url,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "analysis_id": self.analysis_id,
            "tx_hash": self.tx_hash,
        }


async def create_checkout_session(
    ticker: str,
    asset_type: str = "stock",
    selected_analysts: Optional[list] = None,
) -> dict:
    """
    Create a Locus Checkout session for a paid analysis request.

    Returns session data including the checkout URL the client uses to pay.
    If Locus is not configured, returns a mock session for development.
    """
    session_id = str(uuid.uuid4())

    if not founder_agent.is_ready:
        # Development fallback — mock session so the flow can be tested without Locus
        logger.warning("Locus not configured — creating mock checkout session")
        session = CheckoutSession(
            session_id=session_id,
            ticker=ticker.upper(),
            asset_type=asset_type,
            price_usdc=ANALYSIS_PRICE_USDC,
            locus_session_id=f"mock_{session_id[:8]}",
            checkout_url=f"/locus/mock-pay/{session_id}",
        )
        _sessions[session_id] = session
        return {**session.to_dict(), "mock": True}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LOCUS_BETA_API}/checkout/sessions",
                headers={"Authorization": f"Bearer {founder_agent.api_key}"},
                json={
                    "amount": str(ANALYSIS_PRICE_USDC),
                    "currency": "USDC",
                    "description": f"Quorum Analysis: {ticker.upper()} ({asset_type})",
                    "metadata": {
                        "ticker": ticker.upper(),
                        "asset_type": asset_type,
                        "session_id": session_id,
                        "analysts": ",".join(selected_analysts or []),
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Handle both flat and wrapped (data: {}) response structures
        if "data" in data and isinstance(data["data"], dict):
            locus_data = data["data"]
        else:
            locus_data = data

        locus_session_id = locus_data.get("id") or locus_data.get("sessionId")
        checkout_url = locus_data.get("url") or locus_data.get("checkoutUrl")

        if not checkout_url:
            logger.error(f"Locus API response missing checkout URL: {data}")
            raise ValueError("Locus API did not return a checkout URL")

        session = CheckoutSession(
            session_id=session_id,
            ticker=ticker.upper(),
            asset_type=asset_type,
            price_usdc=ANALYSIS_PRICE_USDC,
            locus_session_id=locus_session_id,
            checkout_url=checkout_url,
        )
        _sessions[session_id] = session

        logger.info(
            f"Checkout session created — {ticker} | "
            f"session: {session_id[:8]} | locus: {locus_session_id}"
        )
        return session.to_dict()

    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        # Fallback to mock so the demo still works
        session = CheckoutSession(
            session_id=session_id,
            ticker=ticker.upper(),
            asset_type=asset_type,
            price_usdc=ANALYSIS_PRICE_USDC,
            locus_session_id=f"fallback_{session_id[:8]}",
            checkout_url=f"/locus/mock-pay/{session_id}",
        )
        _sessions[session_id] = session
        return {**session.to_dict(), "mock": True, "locus_error": str(e)}


async def confirm_payment(session_id: str) -> dict:
    """
    Check whether a checkout session has been paid.
    Polls the Locus API for payment status.
    """
    session = _sessions.get(session_id)
    if not session:
        return {"paid": False, "error": "Session not found"}

    if session.is_expired() and session.status == "pending":
        session.status = "expired"
        return {"paid": False, "status": "expired"}

    if session.status in ("paid", "fulfilled"):
        return {"paid": True, "status": session.status, **session.to_dict()}

    # Mock sessions are auto-confirmed for development
    if session.locus_session_id and session.locus_session_id.startswith(("mock_", "fallback_")):
        if session.status == "pending":
            session.status = "paid"
        session.paid_at = datetime.utcnow()
        logger.info(f"Mock session {session_id[:8]} auto-confirmed")
        return {"paid": True, "status": "paid", **session.to_dict()}

    # Check real Locus session status
    if not founder_agent.is_ready:
        return {"paid": False, "error": "Locus not configured"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{LOCUS_BETA_API}/checkout/sessions/{session.locus_session_id}",
                headers={"Authorization": f"Bearer {founder_agent.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        locus_status = data.get("status", "").lower()
        if locus_status in ("paid", "complete", "completed", "success"):
            session.status = "paid"
            session.paid_at = datetime.utcnow()
            session.tx_hash = data.get("txHash") or data.get("transactionHash")
            logger.info(
                f"Payment confirmed — session: {session_id[:8]} | "
                f"tx: {session.tx_hash}"
            )
            return {"paid": True, "status": "paid", **session.to_dict()}

        return {"paid": False, "status": locus_status, **session.to_dict()}

    except Exception as e:
        logger.error(f"Payment confirmation error for {session_id}: {e}")
        return {"paid": False, "error": str(e)}


async def pay_checkout_session(session_id: str) -> dict:
    """
    Agent-to-agent payment: pay a Locus checkout session directly from the agent wallet.
    Used when Quorum acts as a buyer (e.g., paying for wrapped API calls).
    """
    session = _sessions.get(session_id)
    if not session:
        return {"success": False, "error": "Session not found"}

    if not founder_agent.is_ready:
        return {"success": False, "error": "Locus not configured"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LOCUS_BETA_API}/checkout/agent/pay/{session.locus_session_id}",
                headers={"Authorization": f"Bearer {founder_agent.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        session.status = "paid"
        session.paid_at = datetime.utcnow()
        session.tx_hash = data.get("txHash")
        return {"success": True, **data}

    except Exception as e:
        logger.error(f"Agent payment failed for {session_id}: {e}")
        return {"success": False, "error": str(e)}


def get_session(session_id: str) -> Optional[dict]:
    """Get session data by ID."""
    session = _sessions.get(session_id)
    return session.to_dict() if session else None


def mark_fulfilled(session_id: str, analysis_id: str):
    """Mark a session as fulfilled after analysis is delivered."""
    session = _sessions.get(session_id)
    if session:
        session.status = "fulfilled"
        session.analysis_id = analysis_id
        logger.info(f"Session {session_id[:8]} fulfilled — analysis: {analysis_id[:8]}")


def mock_confirm(session_id: str) -> bool:
    """
    Manually confirm a mock/dev session as paid.
    Used by the /locus/mock-pay endpoint for demo purposes.
    """
    session = _sessions.get(session_id)
    if session and session.status == "pending":
        session.status = "paid"
        session.paid_at = datetime.utcnow()
        return True
    return False


def get_revenue_summary() -> dict:
    """Calculate total revenue from all fulfilled sessions."""
    all_sessions = list(_sessions.values())
    paid = [s for s in all_sessions if s.status in ("paid", "fulfilled")]
    fulfilled = [s for s in all_sessions if s.status == "fulfilled"]

    return {
        "total_sessions": len(all_sessions),
        "paid_sessions": len(paid),
        "fulfilled_sessions": len(fulfilled),
        "pending_sessions": len([s for s in all_sessions if s.status == "pending"]),
        "total_revenue_usdc": round(sum(s.price_usdc for s in paid), 2),
        "fulfilled_revenue_usdc": round(sum(s.price_usdc for s in fulfilled), 2),
        "price_per_analysis_usdc": ANALYSIS_PRICE_USDC,
    }
