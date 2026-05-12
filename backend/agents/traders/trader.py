"""
Quorum — Trader Agent
Synthesizes research thesis into a concrete trade plan with validated outputs.
"""

import math
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import TradeSignal, TradeAction, AssetType
from utils.json_parser import safe_parse_json
from config import MAX_POSITION_SIZE, MIN_POSITION_SIZE

logger = logging.getLogger("quorum.trader")


TRADER_SYSTEM = """You are a senior Trader at an algorithmic trading firm.
You receive an investment thesis from the research team and must create a concrete trade plan.

Your trade plan must include:
- ACTION: buy, sell, hold, short, or cover
- CONFIDENCE: 0.0 to 1.0 (how confident you are in this trade)
- ENTRY STRATEGY: target entry price (use current price as reference)
- EXIT STRATEGY: target price (profit target) and stop-loss price
- POSITION SIZE: suggested portfolio allocation as a decimal (e.g. 0.10 = 10%, max 0.25)
- REASONING: why this specific trade setup makes sense

Rules:
- For BUY trades: stop_loss MUST be below entry_price
- For SHORT trades: stop_loss MUST be above entry_price
- For HOLD: entry_price, target_price, stop_loss can be null
- position_size_pct must be between 0.01 and 0.25

Respond ONLY in valid JSON:
{
    "action": "buy",
    "confidence": 0.75,
    "entry_price": 150.00,
    "target_price": 170.00,
    "stop_loss": 140.00,
    "position_size_pct": 0.10,
    "reasoning": "..."
}
"""


def _safe_price(value) -> float | None:
    """Return a valid positive price or None."""
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v) or v <= 0:
            return None
        return round(v, 6)
    except (TypeError, ValueError):
        return None


def _safe_confidence(value) -> float:
    """Clamp confidence to [0.0, 1.0]."""
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return 0.5


def _safe_position_size(value) -> float:
    """Clamp position size to configured bounds."""
    try:
        return max(MIN_POSITION_SIZE, min(float(value), MAX_POSITION_SIZE))
    except (TypeError, ValueError):
        return MIN_POSITION_SIZE


def _validate_prices(action: str, entry: float | None, target: float | None, stop: float | None):
    """Log a warning if price logic is inconsistent."""
    if entry is None:
        return
    if action == "buy" and stop is not None and stop >= entry:
        logger.warning(
            f"Trader: stop_loss ({stop}) >= entry ({entry}) for BUY — may be LLM error"
        )
    if action == "short" and stop is not None and stop <= entry:
        logger.warning(
            f"Trader: stop_loss ({stop}) <= entry ({entry}) for SHORT — may be LLM error"
        )


def create_trader(llm, memory=None):
    """Factory for trader node."""

    async def trader_node(state: dict) -> dict:
        ticker = state["ticker"]
        asset_type = state.get("asset_type", "stock")
        logger.info(f"Trader started for {ticker}")

        debate = state.get("investment_debate") or {}
        if hasattr(debate, "model_dump"):
            debate_data = debate.model_dump()
        elif isinstance(debate, dict):
            debate_data = debate
        else:
            debate_data = {}

        thesis = debate_data.get("investment_thesis") or "No thesis available."
        verdict = debate_data.get("judge_verdict") or "neutral"
        judge_confidence = debate_data.get("judge_confidence") or 0.5

        # Get current price from market report
        market_report = state.get("market_report")
        current_price = None
        if market_report:
            rd = market_report if isinstance(market_report, dict) else market_report.model_dump()
            current_price = rd.get("raw_data", {}).get("current_price")

        # Vector memory context
        memory_context = ""
        if memory:
            try:
                memories = memory.get_memories(f"{ticker} {verdict} trading", n_matches=2)
                if memories:
                    memory_context = "\nPAST SIMILAR TRADES:\n"
                    for m in memories:
                        memory_context += f"- {m['recommendation'][:200]}\n"
            except Exception as e:
                logger.warning(f"Memory lookup failed: {e}")

        prompt = f"""
TICKER: {ticker}
ASSET TYPE: {asset_type}
CURRENT PRICE: ${current_price or 'Unknown'}

RESEARCH VERDICT: {verdict} (confidence: {judge_confidence:.0%})
INVESTMENT THESIS:
{thesis}
{memory_context}

Create your trade plan. Use the current price as your entry reference.
"""
        messages = [SystemMessage(content=TRADER_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            logger.warning(f"Trader: LLM returned unparseable JSON for {ticker}, defaulting to hold")
            result = {
                "action": "hold",
                "confidence": 0.4,
                "reasoning": result["raw_response"][:500],
            }

        # Validate and sanitize all numeric fields
        action_str = str(result.get("action", "hold")).lower().strip()
        try:
            action = TradeAction(action_str)
        except ValueError:
            logger.warning(f"Trader: invalid action '{action_str}', defaulting to hold")
            action = TradeAction.HOLD

        confidence = _safe_confidence(result.get("confidence", 0.5))
        entry_price = _safe_price(result.get("entry_price"))
        target_price = _safe_price(result.get("target_price"))
        stop_loss = _safe_price(result.get("stop_loss"))
        position_size_pct = _safe_position_size(result.get("position_size_pct", MIN_POSITION_SIZE))

        _validate_prices(action_str, entry_price, target_price, stop_loss)

        try:
            asset_type_enum = AssetType(asset_type)
        except ValueError:
            asset_type_enum = AssetType.STOCK

        trade_signal = TradeSignal(
            ticker=ticker,
            asset_type=asset_type_enum,
            action=action,
            confidence=confidence,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            position_size_pct=position_size_pct,
            reasoning=str(result.get("reasoning", ""))[:1000],
        )

        logger.info(
            f"Trader done — {trade_signal.action.value} "
            f"(conf: {trade_signal.confidence:.0%}, size: {trade_signal.position_size_pct:.1%})"
        )
        return {"trade_signal": trade_signal.dict()}

    return trader_node
