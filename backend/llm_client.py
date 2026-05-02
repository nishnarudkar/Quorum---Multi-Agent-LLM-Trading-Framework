"""
Quorum — Groq LLM Client
Creates ChatGroq instances with rate-limit-resilient wrapper and per-call timeout.
"""

import asyncio
import random
import logging
from langchain_groq import ChatGroq
from config import (
    GROQ_API_KEY,
    DEEP_THINK_MODEL,
    QUICK_THINK_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT,
    LLM_CONCURRENCY,
)

logger = logging.getLogger("quorum.llm")

# Global semaphore — limits concurrent LLM calls to prevent burst 429s
_llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY)


class RateLimitedLLM:
    """Wrapper around ChatGroq with rate-limit backoff, per-call timeout, and empty-response guard.

    Features:
    - Catches 429 / RateLimitError and retries with exponential backoff + jitter
    - Per-call timeout via asyncio.wait_for (prevents indefinite hangs)
    - Validates that the LLM returned non-empty content
    - Global semaphore limits concurrent API calls
    """

    def __init__(self, llm: ChatGroq, max_retries: int = 5, base_delay: float = 5.0):
        self._llm = llm
        self._max_retries = max_retries
        self._base_delay = base_delay

    async def ainvoke(self, messages, **kwargs):
        """Rate-limit-aware async invoke with exponential backoff and timeout."""
        last_error = None

        for attempt in range(self._max_retries + 1):
            async with _llm_semaphore:
                try:
                    response = await asyncio.wait_for(
                        self._llm.ainvoke(messages, **kwargs),
                        timeout=LLM_TIMEOUT,
                    )

                    # Guard against empty responses
                    if not response or not getattr(response, "content", "").strip():
                        raise ValueError("LLM returned an empty response")

                    return response

                except asyncio.TimeoutError:
                    logger.error(
                        f"LLM call timed out after {LLM_TIMEOUT}s "
                        f"(attempt {attempt + 1}/{self._max_retries})"
                    )
                    last_error = TimeoutError(f"LLM call exceeded {LLM_TIMEOUT}s timeout")
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._base_delay)
                    continue

                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = any(kw in error_str for kw in (
                        "rate_limit", "rate limit", "429",
                        "too many requests", "resource_exhausted",
                        "tokens per minute", "requests per minute",
                    ))

                    if not is_rate_limit:
                        raise  # Non-rate-limit errors bubble up immediately

                    last_error = e

                    if attempt < self._max_retries:
                        delay = self._base_delay * (2 ** attempt) + random.uniform(0, 2)
                        logger.warning(
                            f"Rate limit hit (attempt {attempt + 1}/{self._max_retries}), "
                            f"retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Rate limit exceeded after {self._max_retries} retries: {e}"
                        )

        raise last_error

    def invoke(self, messages, **kwargs):
        """Synchronous invoke — falls through to underlying LLM."""
        return self._llm.invoke(messages, **kwargs)

    def __getattr__(self, name):
        return getattr(self._llm, name)


def create_deep_thinker() -> RateLimitedLLM:
    """Deep-thinking LLM for complex reasoning, debates, and final decisions."""
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=DEEP_THINK_MODEL,
        temperature=LLM_TEMPERATURE,
        max_retries=LLM_MAX_RETRIES,
    )
    return RateLimitedLLM(llm)


def create_quick_thinker() -> RateLimitedLLM:
    """Fast LLM for analyst data processing."""
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=QUICK_THINK_MODEL,
        temperature=LLM_TEMPERATURE,
        max_retries=LLM_MAX_RETRIES,
    )
    return RateLimitedLLM(llm)
