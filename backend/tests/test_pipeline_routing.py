"""Routing and human-in-the-loop logic of the LangGraph pipeline (no LLM calls)."""

import pytest

import graph.pipeline as pipeline_module
from graph.pipeline import (
    human_approval_node,
    route_to_analysts,
    should_continue_debate,
    should_continue_risk,
)
from models.schemas import InvestmentDebateState


def _targets(sends):
    return sorted(send.node for send in sends)


def test_routes_to_all_default_analysts():
    assert _targets(route_to_analysts({"selected_analysts": None})) == [
        "fundamentals_analyst", "market_analyst", "news_analyst", "sentiment_analyst",
    ]


def test_routes_only_to_selected_analysts():
    sends = route_to_analysts({"selected_analysts": ["market", "news"]})
    assert _targets(sends) == ["market_analyst", "news_analyst"]


def test_invalid_analyst_selection_falls_back_to_defaults():
    sends = route_to_analysts({"selected_analysts": ["astrology"]})
    assert len(sends) == 4


def test_debate_continues_until_max_rounds(monkeypatch):
    monkeypatch.setattr(pipeline_module, "MAX_DEBATE_ROUNDS", 2)
    assert should_continue_debate({"investment_debate": {"round_count": 1}}) == "bull_researcher"
    assert should_continue_debate({"investment_debate": {"round_count": 2}}) == "research_judge"


def test_debate_routing_accepts_pydantic_state(monkeypatch):
    monkeypatch.setattr(pipeline_module, "MAX_DEBATE_ROUNDS", 2)
    state = {"investment_debate": InvestmentDebateState(round_count=2)}
    assert should_continue_debate(state) == "research_judge"


def test_risk_debate_routing(monkeypatch):
    monkeypatch.setattr(pipeline_module, "MAX_RISK_DEBATE_ROUNDS", 1)
    assert should_continue_risk({"risk_debate": {"round_count": 0}}) == "aggressive_analyst"
    assert should_continue_risk({"risk_debate": {"round_count": 1}}) == "risk_judge"
    assert should_continue_risk({"risk_debate": None}) == "risk_judge"


@pytest.mark.asyncio
async def test_hitl_auto_approves_high_confidence(monkeypatch):
    monkeypatch.setattr(pipeline_module, "ENABLE_HITL", True)
    monkeypatch.setattr(pipeline_module, "AUTO_TRADE_CONFIDENCE", 0.85)
    result = await human_approval_node({"trade_signal": {"action": "buy", "confidence": 0.9}})
    assert result == {"trade_approved": True, "final_decision": "auto_approved_high_confidence"}


@pytest.mark.asyncio
async def test_hitl_rejects_missing_signal(monkeypatch):
    monkeypatch.setattr(pipeline_module, "ENABLE_HITL", True)
    result = await human_approval_node({"trade_signal": None})
    assert result["trade_approved"] is False


@pytest.mark.asyncio
async def test_hitl_interrupts_low_confidence_and_applies_decision(monkeypatch):
    monkeypatch.setattr(pipeline_module, "ENABLE_HITL", True)
    monkeypatch.setattr(pipeline_module, "AUTO_TRADE_CONFIDENCE", 0.85)
    captured = {}

    def fake_interrupt(payload):
        captured.update(payload)
        return "reject"

    monkeypatch.setattr(pipeline_module, "interrupt", fake_interrupt)
    result = await human_approval_node({"trade_signal": {"action": "buy", "confidence": 0.5}})

    assert captured["type"] == "trade_approval_required"
    assert result == {"trade_approved": False, "final_decision": "human_rejected"}


@pytest.mark.asyncio
async def test_hitl_disabled_auto_approves(monkeypatch):
    monkeypatch.setattr(pipeline_module, "ENABLE_HITL", False)
    result = await human_approval_node({"trade_signal": {"confidence": 0.1}})
    assert result["trade_approved"] is True
