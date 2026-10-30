"""HTTP API tests with a fake pipeline (no LLM, market-data, or broker calls)."""

import asyncio

import pytest
from fastapi.testclient import TestClient

import api.main as main


class FakePipeline:
    """Returns a canned result, or raises the configured error."""

    def __init__(self, error: Exception | None = None, delay: float = 0.0):
        self.error = error
        self.delay = delay
        self.calls = []

    async def analyze(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return {
            "ticker": kwargs["ticker"],
            "asset_type": kwargs["asset_type"],
            "trade_signal": {"action": "hold", "confidence": 0.6},
            "trade_approved": False,
            "final_decision": "hold",
        }


@pytest.fixture
def client(monkeypatch):
    """A client without the app lifespan, so no DB, price stream, or scanner starts."""
    monkeypatch.setattr(main, "trade_db", None)
    monkeypatch.setattr(main, "pipeline", FakePipeline())
    monkeypatch.setattr(main, "analysis_jobs", {})
    return TestClient(main.app)


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert body["pipeline_ready"] is True


def test_analyze_returns_serialized_state(client):
    res = client.post("/analyze", json={"ticker": " aapl ", "asset_type": "stock"})
    assert res.status_code == 200
    body = res.json()
    assert body["ticker"] == "AAPL"
    assert body["trade_signal"]["action"] == "hold"
    assert main.pipeline.calls[0]["ticker"] == "AAPL"


@pytest.mark.parametrize("payload", [
    {"ticker": "", "asset_type": "stock"},
    {"ticker": "AAPL", "asset_type": "bonds"},
    {"ticker": "AAPL", "selected_analysts": ["astrology"]},
])
def test_analyze_rejects_invalid_requests(client, payload):
    assert client.post("/analyze", json=payload).status_code == 422


def test_analyze_without_pipeline_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(main, "pipeline", None)
    assert client.post("/analyze", json={"ticker": "AAPL"}).status_code == 503


@pytest.mark.parametrize("error, status", [
    (TimeoutError("took too long"), 504),
    (RuntimeError("Error code: 429 rate_limit_exceeded"), 429),
    (RuntimeError("something broke"), 500),
])
def test_analyze_maps_pipeline_errors(client, monkeypatch, error, status):
    monkeypatch.setattr(main, "pipeline", FakePipeline(error=error))
    assert client.post("/analyze", json={"ticker": "AAPL"}).status_code == status


def test_background_analysis_completes(client):
    res = client.post("/analyses", json={"ticker": "BTC/USD", "asset_type": "crypto"})
    assert res.status_code == 202
    job = res.json()
    assert job["status"] == "running"

    # TestClient runs the app on its own event loop; poll until the task finishes
    for _ in range(50):
        status = client.get(f"/analyses/{job['analysis_id']}").json()
        if status["status"] != "running":
            break
    assert status["status"] == "completed"
    assert status["result"]["ticker"] == "BTC/USD"


def test_background_analysis_records_failures(client, monkeypatch):
    monkeypatch.setattr(main, "pipeline", FakePipeline(error=RuntimeError("boom")))
    job = client.post("/analyses", json={"ticker": "AAPL"}).json()

    for _ in range(50):
        status = client.get(f"/analyses/{job['analysis_id']}").json()
        if status["status"] != "running":
            break
    assert status["status"] == "failed"
    assert "boom" in status["error"]


def test_unknown_analysis_is_404(client):
    assert client.get("/analyses/does-not-exist").status_code == 404


def test_serialize_state_handles_nan_enums_and_models():
    from models.schemas import InvestmentDebateState, TradeAction

    state = {
        "price": float("nan"),
        "action": TradeAction.BUY,
        "debate": InvestmentDebateState(round_count=1),
        "nested": [{"x": float("inf")}],
    }
    out = main._serialize_state(state)
    assert out["price"] is None
    assert out["action"] == "buy"
    assert out["debate"]["round_count"] == 1
    assert out["nested"] == [{"x": None}]
