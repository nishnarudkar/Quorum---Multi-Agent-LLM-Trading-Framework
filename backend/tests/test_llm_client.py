"""Key rotation and rate-limit retry behaviour of the Groq client wrapper."""

from types import SimpleNamespace

import pytest

import llm_client
from llm_client import KeyRotator, RateLimitedLLM


@pytest.mark.asyncio
async def test_key_rotator_cycles_through_keys():
    rotator = KeyRotator(["a", "b", "c"])
    assert [await rotator.get_next_key() for _ in range(4)] == ["a", "b", "c", "a"]


@pytest.mark.asyncio
async def test_key_rotator_without_keys_returns_empty_string():
    assert await KeyRotator([]).get_next_key() == ""


class FakeChatGroq:
    """Stands in for ChatGroq: fails with a 429 a set number of times, then succeeds."""

    calls: list[str] = []
    failures_left = 0

    def __init__(self, api_key, **_):
        self.api_key = api_key

    async def ainvoke(self, messages, **_):
        FakeChatGroq.calls.append(self.api_key)
        if FakeChatGroq.failures_left > 0:
            FakeChatGroq.failures_left -= 1
            raise RuntimeError("Error code: 429 - rate_limit_exceeded")
        return SimpleNamespace(content="ok")


@pytest.fixture
def fake_groq(monkeypatch):
    FakeChatGroq.calls = []
    FakeChatGroq.failures_left = 0
    monkeypatch.setattr(llm_client, "ChatGroq", FakeChatGroq)
    monkeypatch.setattr(llm_client, "rotator", KeyRotator(["key-1", "key-2"]))
    return FakeChatGroq


@pytest.mark.asyncio
async def test_retries_rate_limits_with_the_next_key(fake_groq):
    fake_groq.failures_left = 1
    llm = RateLimitedLLM("test-model", max_retries=3)
    llm._base_delay = 0

    response = await llm.ainvoke([])

    assert response.content == "ok"
    assert fake_groq.calls == ["key-1", "key-2"]


@pytest.mark.asyncio
async def test_raises_after_exhausting_retries(fake_groq):
    fake_groq.failures_left = 10
    llm = RateLimitedLLM("test-model", max_retries=2)
    llm._base_delay = 0

    with pytest.raises(RuntimeError, match="429"):
        await llm.ainvoke([])
    assert len(fake_groq.calls) == 3


@pytest.mark.asyncio
async def test_non_rate_limit_errors_are_not_retried(fake_groq, monkeypatch):
    async def boom(self, messages, **_):
        FakeChatGroq.calls.append(self.api_key)
        raise ValueError("invalid request")

    monkeypatch.setattr(FakeChatGroq, "ainvoke", boom)
    llm = RateLimitedLLM("test-model", max_retries=3)

    with pytest.raises(ValueError):
        await llm.ainvoke([])
    assert len(fake_groq.calls) == 1
