"""
Quorum — Risk Debate Agents (Aggressive, Conservative, Neutral)
Three risk analysts debate the proposed trade; CRO Judge delivers the final verdict.
Position size bounds are enforced after LLM output.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import DebateMessage, RiskDebateState
import logging
from utils.json_parser import safe_parse_json
from config import MAX_POSITION_SIZE, MIN_POSITION_SIZE
from utils.serialization import sanitize_for_serialization

logger = logging.getLogger("quorum.risk")


AGGRESSIVE_SYSTEM = """You are an AGGRESSIVE Risk Analyst at a trading firm.
You believe in taking calculated risks for higher returns.
You favor larger position sizes and tighter stop-losses to maximize reward-to-risk ratios.

Respond in valid JSON only:
{
    "argument": "Your risk assessment and recommendation (1-2 paragraphs)",
    "recommended_position_pct": 0.15,
    "recommended_stop_loss_pct": 0.03,
    "risk_rating": "acceptable"
}
"""

CONSERVATIVE_SYSTEM = """You are a CONSERVATIVE Risk Analyst at a trading firm.
You prioritize capital preservation above all else.
You favor smaller positions, wider stop-losses, and often recommend reducing exposure.

Respond in valid JSON only:
{
    "argument": "Your risk assessment and recommendation (1-2 paragraphs)",
    "recommended_position_pct": 0.05,
    "recommended_stop_loss_pct": 0.08,
    "risk_rating": "high_risk"
}
"""

NEUTRAL_SYSTEM = """You are a NEUTRAL Risk Analyst at a trading firm.
You balance risk and reward objectively, considering both aggressive and conservative viewpoints.

Respond in valid JSON only:
{
    "argument": "Your balanced risk assessment (1-2 paragraphs)",
    "recommended_position_pct": 0.10,
    "recommended_stop_loss_pct": 0.05,
    "risk_rating": "moderate"
}
"""

RISK_JUDGE_SYSTEM = """You are the Chief Risk Officer (CRO). You have reviewed a risk debate
between aggressive, conservative, and neutral risk analysts about a proposed trade.

Your job:
1. Approve or reject the trade based on the evidence
2. Set the final position size as a fraction of portfolio (e.g. 0.08 = 8%)
3. Set risk parameters

Respond in valid JSON only:
{
    "approved": true,
    "verdict": "Approved with reduced position size",
    "final_position_pct": 0.08,
    "final_stop_loss_pct": 0.05,
    "max_portfolio_risk_pct": 0.02,
    "reasoning": "Detailed explanation of the risk decision"
}
"""


def _clamp_position(value: float) -> float:
    """Clamp position size to configured bounds."""
    try:
        v = float(value)
        return max(MIN_POSITION_SIZE, min(v, MAX_POSITION_SIZE))
    except (TypeError, ValueError):
        return MIN_POSITION_SIZE


def _format_trade_context(state: dict) -> str:
    """Format trade signal for risk analysts."""
    signal = state.get("trade_signal")
    if not signal:
        return "No trade signal available."
    s = signal if isinstance(signal, dict) else signal.model_dump()
    action = s.get("action")
    if hasattr(action, "value"):
        action = action.value
    return (
        f"PROPOSED TRADE:\n"
        f"  Ticker:        {s.get('ticker')}\n"
        f"  Action:        {action}\n"
        f"  Confidence:    {s.get('confidence', 0):.0%}\n"
        f"  Entry:         ${s.get('entry_price', 'N/A')}\n"
        f"  Target:        ${s.get('target_price', 'N/A')}\n"
        f"  Stop Loss:     ${s.get('stop_loss', 'N/A')}\n"
        f"  Proposed Size: {float(s.get('position_size_pct', 0)) * 100:.1f}%\n"
        f"  Reasoning:     {str(s.get('reasoning', ''))[:400]}"
    )


def create_aggressive_debater(llm):
    async def node(state: dict) -> dict:
        logger.info("Aggressive Risk Analyst started")
        context = _format_trade_context(state)
        debate = state.get("risk_debate") or RiskDebateState()
        if isinstance(debate, dict):
            debate = RiskDebateState(**debate)

        previous = ""
        if debate.conservative_arguments:
            previous = f"\nConservative's view:\n{debate.conservative_arguments[-1].content}"

        prompt = f"{context}\n{previous}\n\nProvide your AGGRESSIVE risk assessment."
        messages = [SystemMessage(content=AGGRESSIVE_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"argument": result["raw_response"], "risk_rating": "unknown"}

        msg = DebateMessage(speaker="aggressive", content=result.get("argument", response.content))
        debate.aggressive_arguments.append(msg)
        debate.round_count = len(debate.aggressive_arguments)

        logger.info(f"Aggressive done — risk_rating: {result.get('risk_rating', 'N/A')}")
        return {"risk_debate": sanitize_for_serialization(debate.dict())}

    return node


def create_conservative_debater(llm):
    async def node(state: dict) -> dict:
        logger.info("Conservative Risk Analyst started")
        context = _format_trade_context(state)
        debate = state.get("risk_debate") or RiskDebateState()
        if isinstance(debate, dict):
            debate = RiskDebateState(**debate)

        previous = ""
        if debate.aggressive_arguments:
            previous = f"\nAggressive's view:\n{debate.aggressive_arguments[-1].content}"

        prompt = f"{context}\n{previous}\n\nProvide your CONSERVATIVE risk assessment."
        messages = [SystemMessage(content=CONSERVATIVE_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"argument": result["raw_response"], "risk_rating": "unknown"}

        msg = DebateMessage(speaker="conservative", content=result.get("argument", response.content))
        debate.conservative_arguments.append(msg)

        logger.info(f"Conservative done — risk_rating: {result.get('risk_rating', 'N/A')}")
        return {"risk_debate": sanitize_for_serialization(debate.dict())}

    return node


def create_neutral_debater(llm):
    async def node(state: dict) -> dict:
        logger.info("Neutral Risk Analyst started")
        context = _format_trade_context(state)
        debate = state.get("risk_debate") or RiskDebateState()
        if isinstance(debate, dict):
            debate = RiskDebateState(**debate)

        previous = ""
        if debate.aggressive_arguments:
            previous += f"\nAggressive's view:\n{debate.aggressive_arguments[-1].content}"
        if debate.conservative_arguments:
            previous += f"\nConservative's view:\n{debate.conservative_arguments[-1].content}"

        prompt = f"{context}\n{previous}\n\nProvide your NEUTRAL balanced risk assessment."
        messages = [SystemMessage(content=NEUTRAL_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"argument": result["raw_response"], "risk_rating": "unknown"}

        msg = DebateMessage(speaker="neutral", content=result.get("argument", response.content))
        debate.neutral_arguments.append(msg)

        logger.info(f"Neutral done — risk_rating: {result.get('risk_rating', 'N/A')}")
        return {"risk_debate": sanitize_for_serialization(debate.dict())}

    return node


def create_risk_judge(llm, memory=None):
    async def node(state: dict) -> dict:
        logger.info("Risk Judge (CRO) deliberating...")
        context = _format_trade_context(state)
        debate = state.get("risk_debate") or RiskDebateState()
        if isinstance(debate, dict):
            debate = RiskDebateState(**debate)

        # Build debate transcript
        max_rounds = max(
            len(debate.aggressive_arguments),
            len(debate.conservative_arguments),
            len(debate.neutral_arguments),
        )
        transcript = ""
        for i in range(max_rounds):
            transcript += f"\n--- ROUND {i + 1} ---"
            if i < len(debate.aggressive_arguments):
                transcript += f"\nAGGRESSIVE: {debate.aggressive_arguments[i].content}"
            if i < len(debate.conservative_arguments):
                transcript += f"\nCONSERVATIVE: {debate.conservative_arguments[i].content}"
            if i < len(debate.neutral_arguments):
                transcript += f"\nNEUTRAL: {debate.neutral_arguments[i].content}"

        prompt = f"{context}\n\nRISK DEBATE TRANSCRIPT:\n{transcript}\n\nDeliver your final risk judgment."
        messages = [SystemMessage(content=RISK_JUDGE_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {
                "approved": False,
                "verdict": result["raw_response"][:500],
                "final_position_pct": MIN_POSITION_SIZE,
                "reasoning": result["raw_response"],
            }

        approved = bool(result.get("approved", False))

        # Enforce position size bounds — never trust raw LLM numbers
        raw_size = result.get("final_position_pct", MIN_POSITION_SIZE)
        final_position_pct = _clamp_position(raw_size)

        debate.judge_verdict = result.get("verdict", "")
        debate.recommended_position_size = final_position_pct

        # Update trade signal with risk-adjusted position size
        trade_signal = state.get("trade_signal")
        if trade_signal is not None:
            if hasattr(trade_signal, "model_copy"):
                trade_signal = trade_signal.model_copy(
                    update={"position_size_pct": final_position_pct}
                )
            elif isinstance(trade_signal, dict):
                trade_signal = {**trade_signal, "position_size_pct": final_position_pct}

        final_decision = (
            f"TRADE {'APPROVED' if approved else 'REJECTED'} | "
            f"Size: {final_position_pct:.1%} | "
            f"Max Risk: {result.get('max_portfolio_risk_pct', 0.02):.1%} | "
            f"{result.get('reasoning', '')[:300]}"
        )

        logger.info(
            f"Risk Judge verdict: {'APPROVED' if approved else 'REJECTED'} "
            f"— position: {final_position_pct:.1%}"
        )

        return {
            "risk_debate": sanitize_for_serialization(debate.dict()),
            "trade_signal": sanitize_for_serialization(trade_signal if isinstance(trade_signal, dict) else trade_signal.dict()),
            "final_decision": final_decision,
            "trade_approved": approved,
        }

    return node
