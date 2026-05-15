"""
Quorum — Groq LLM Client
Creates ChatGroq instances with rate-limit-resilient wrapper and key rotation.
"""

import asyncio
import random
import logging
from typing import List
from langchain_groq import ChatGroq
from config import (
    GROQ_API_KEYS,
    DEEP_THINK_MODEL,
    QUICK_THINK_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT,
    LLM_CONCURRENCY,
)

logger = logging.getLogger("quorum.llm")

# Global semaphore — limits concurrent LLM calls across all keys
_llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY * max(1, len(GROQ_API_KEYS)))


class KeyRotator:
    """Manages a pool of API keys to distribute load and mitigate rate limits."""
    
    def __init__(self, keys: List[str]):
        self.keys = keys
        self._index = 0
        self._lock = asyncio.Lock()

    async def get_next_key(self) -> str:
        async with self._lock:
            if not self.keys:
                return ""
            key = self.keys[self._index]
            self._index = (self._index + 1) % len(self.keys)
            return key


# Global rotator
rotator = KeyRotator(GROQ_API_KEYS)


class RateLimitedLLM:
    """Wrapper around ChatGroq with key rotation, rate-limit backoff, and timeout.
    
    If a 429 is hit, it will swap the API key and retry.
    """

    def __init__(self, model_name: str, temperature: float = 0.7, max_retries: int = 5):
        self.model_name = model_name
        self.temperature = temperature
        self._max_retries = max_retries
        self._base_delay = 3.0

    async def ainvoke(self, messages, **kwargs):
        """Async invoke with automatic key rotation on rate limit."""
        last_error = None

        for attempt in range(self._max_retries + 1):
            # Get a fresh key for this attempt
            api_key = await rotator.get_next_key()
            
            async with _llm_semaphore:
                try:
                    # Re-initialize the LLM with the current key
                    llm = ChatGroq(
                        api_key=api_key,
                        model=self.model_name,
                        temperature=self.temperature,
                        max_retries=0, # We handle retries ourselves
                    )

                    response = await asyncio.wait_for(
                        llm.ainvoke(messages, **kwargs),
                        timeout=LLM_TIMEOUT,
                    )

                    if not response or not getattr(response, "content", "").strip():
                        raise ValueError("LLM returned an empty response")

                    return response

                except asyncio.TimeoutError:
                    logger.error(f"LLM call timed out ({self.model_name})")
                    last_error = TimeoutError(f"LLM timeout ({LLM_TIMEOUT}s)")
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._base_delay)
                    continue

                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = any(kw in error_str for kw in (
                        "rate_limit", "429", "too many requests", "resource_exhausted",
                        "tokens per minute", "requests per minute",
                    ))

                    if not is_rate_limit:
                        raise

                    last_error = e

                    if attempt < self._max_retries:
                        # On rate limit, wait a bit then swap to next key in next loop
                        delay = self._base_delay + random.uniform(0, 1)
                        logger.warning(
                            f"Rate limit hit for key {api_key[:8]}... (attempt {attempt + 1}), "
                            f"swapping key and retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Rate limit exceeded after {self._max_retries} retries")

        raise last_error

    def invoke(self, messages, **kwargs):
        # Synchronous fallback (uses first key)
        llm = ChatGroq(api_key=GROQ_API_KEYS[0], model=self.model_name)
        return llm.invoke(messages, **kwargs)


def create_deep_thinker() -> RateLimitedLLM:
    return RateLimitedLLM(DEEP_THINK_MODEL, temperature=LLM_TEMPERATURE)


def create_quick_thinker() -> RateLimitedLLM:
    return RateLimitedLLM(QUICK_THINK_MODEL, temperature=LLM_TEMPERATURE)
