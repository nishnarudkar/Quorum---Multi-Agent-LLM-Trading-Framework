"""
Quorum — Alert System
Sends trade signals and analysis results to Telegram and Discord.
Fires automatically after every completed analysis.
"""

import logging
import math
from typing import Optional

import httpx

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    DISCORD_WEBHOOK_URL,
)

logger = logging.getLogger("quorum.alerts")

TELEGRAM_API = "https://api.telegram.org"


# ─── Telegram ─────────────────────────────────────────────────

async def send_telegram(message: str) -> bool:
    """Send a plain-text message to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")
        return False


# ─── Discord ──────────────────────────────────────────────────

async def send_discord(message: str) -> bool:
    """Send a message to the configured Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                DISCORD_WEBHOOK_URL,
                json={"content": message},
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.warning(f"Discord alert failed: {e}")
        return False


# ─── Alert Formatters ─────────────────────────────────────────

def _safe(value, fmt=None, fallback="N/A"):
    """Format a value safely, returning fallback if None/NaN."""
    if value is None:
        return fallback
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return fallback
    if fmt:
        return fmt.format(value)
    return str(value)


def format_analysis_alert(result: dict) -> str:
    """
    Build a human-readable alert message from a completed pipeline result.

    Example output:
        Quorum Alert — AAPL

        Action:     BUY
        Confidence: 65%
        Entry:      $213.40
        Target:     $235.00
        Stop-Loss:  $198.00
        Size:       8.0% of portfolio
        Approved:   YES

        Verdict: Bullish — Strong technical momentum...
    """
    ticker = result.get("ticker", "Unknown")
    asset_type = result.get("asset_type", "stock")
    approved = result.get("trade_approved", False)

    signal = result.get("trade_signal") or {}
    if hasattr(signal, "model_dump"):
        signal = signal.model_dump()

    action = signal.get("action", "hold")
    if hasattr(action, "value"):
        action = action.value

    confidence = signal.get("confidence")
    entry = signal.get("entry_price")
    target = signal.get("target_price")
    stop = signal.get("stop_loss")
    size = signal.get("position_size_pct")
    reasoning = signal.get("reasoning", "")

    # Research verdict
    debate = result.get("investment_debate") or {}
    if hasattr(debate, "model_dump"):
        debate = debate.model_dump()
    verdict = debate.get("judge_verdict", "")
    thesis = debate.get("investment_thesis", "")

    # Action emoji
    action_emoji = {
        "buy": "BUY",
        "sell": "SELL",
        "hold": "HOLD",
        "short": "SHORT",
        "cover": "COVER",
    }.get(str(action).lower(), str(action).upper())

    conf_str = f"{confidence:.0%}" if confidence is not None else "N/A"
    entry_str = f"${entry:,.2f}" if entry else "N/A"
    target_str = f"${target:,.2f}" if target else "N/A"
    stop_str = f"${stop:,.2f}" if stop else "N/A"
    size_str = f"{size:.1%}" if size is not None else "N/A"
    approved_str = "YES" if approved else "NO"

    # Truncate thesis for readability
    thesis_short = (thesis[:200] + "...") if len(thesis) > 200 else thesis

    lines = [
        f"<b>Quorum Alert — {ticker} ({asset_type.upper()})</b>",
        "",
        f"Action:      {action_emoji}",
        f"Confidence:  {conf_str}",
        f"Entry:       {entry_str}",
        f"Target:      {target_str}",
        f"Stop-Loss:   {stop_str}",
        f"Size:        {size_str} of portfolio",
        f"Approved:    {approved_str}",
    ]

    if verdict:
        lines.append("")
        lines.append(f"Verdict: {verdict.capitalize()}")

    if thesis_short:
        lines.append(thesis_short)

    return "\n".join(lines)


def format_error_alert(ticker: str, error: str) -> str:
    """Format an error alert message."""
    return (
        f"<b>Quorum Error — {ticker}</b>\n\n"
        f"Analysis failed:\n{error[:300]}"
    )


def format_approval_required_alert(ticker: str, signal: dict) -> str:
    """Format a human-approval-required alert."""
    action = signal.get("action", "unknown")
    if hasattr(action, "value"):
        action = action.value
    confidence = signal.get("confidence", 0)
    entry = signal.get("entry_price")

    return (
        f"<b>Quorum — Approval Required: {ticker}</b>\n\n"
        f"Action:     {str(action).upper()}\n"
        f"Confidence: {confidence:.0%}\n"
        f"Entry:      {'${:,.2f}'.format(entry) if entry else 'N/A'}\n\n"
        f"Confidence below auto-approve threshold.\n"
        f"Use the dashboard or API to approve/reject."
    )


# ─── Main Alert Dispatcher ────────────────────────────────────

async def send_analysis_alert(result: dict):
    """
    Send a completed analysis alert to all configured channels.
    Called automatically from the API after every successful analysis.
    """
    if not TELEGRAM_BOT_TOKEN and not DISCORD_WEBHOOK_URL:
        return  # No channels configured — skip silently

    message = format_analysis_alert(result)

    sent_telegram = await send_telegram(message)
    sent_discord = await send_discord(
        # Discord doesn't support HTML — strip tags
        message.replace("<b>", "**").replace("</b>", "**")
    )

    if sent_telegram or sent_discord:
        ticker = result.get("ticker", "?")
        channels = []
        if sent_telegram:
            channels.append("Telegram")
        if sent_discord:
            channels.append("Discord")
        logger.info(f"Alert sent for {ticker} via {', '.join(channels)}")


async def send_error_alert(ticker: str, error: str):
    """Send an error alert to all configured channels."""
    if not TELEGRAM_BOT_TOKEN and not DISCORD_WEBHOOK_URL:
        return
    message = format_error_alert(ticker, error)
    await send_telegram(message)
    await send_discord(message.replace("<b>", "**").replace("</b>", "**"))


async def send_approval_required_alert(ticker: str, signal: dict):
    """Notify that a trade is waiting for human approval."""
    if not TELEGRAM_BOT_TOKEN and not DISCORD_WEBHOOK_URL:
        return
    message = format_approval_required_alert(ticker, signal)
    await send_telegram(message)
    await send_discord(message.replace("<b>", "**").replace("</b>", "**"))
