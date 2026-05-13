"""
Quorum — Sentiment Normalization
Maps arbitrary LLM sentiment strings to valid Sentiment enum values.
LLMs occasionally return words like 'cautious', 'positive', 'mixed', etc.
This module maps them to the nearest valid value instead of crashing.
"""

from models.schemas import Sentiment

# Words the LLM might return → nearest valid Sentiment value
_SENTIMENT_MAP: dict[str, Sentiment] = {
    # Valid values (pass-through)
    "very_bullish": Sentiment.VERY_BULLISH,
    "bullish": Sentiment.BULLISH,
    "neutral": Sentiment.NEUTRAL,
    "bearish": Sentiment.BEARISH,
    "very_bearish": Sentiment.VERY_BEARISH,

    # Common LLM synonyms — bullish side
    "positive": Sentiment.BULLISH,
    "optimistic": Sentiment.BULLISH,
    "favorable": Sentiment.BULLISH,
    "constructive": Sentiment.BULLISH,
    "upbeat": Sentiment.BULLISH,
    "strong": Sentiment.BULLISH,
    "buy": Sentiment.BULLISH,
    "overweight": Sentiment.BULLISH,
    "outperform": Sentiment.BULLISH,
    "accumulate": Sentiment.BULLISH,
    "very positive": Sentiment.VERY_BULLISH,
    "strongly bullish": Sentiment.VERY_BULLISH,
    "highly bullish": Sentiment.VERY_BULLISH,
    "extremely bullish": Sentiment.VERY_BULLISH,

    # Common LLM synonyms — bearish side
    "negative": Sentiment.BEARISH,
    "pessimistic": Sentiment.BEARISH,
    "unfavorable": Sentiment.BEARISH,
    "cautious": Sentiment.BEARISH,
    "cautiously bearish": Sentiment.BEARISH,
    "cautiously negative": Sentiment.BEARISH,
    "weak": Sentiment.BEARISH,
    "sell": Sentiment.BEARISH,
    "underweight": Sentiment.BEARISH,
    "underperform": Sentiment.BEARISH,
    "reduce": Sentiment.BEARISH,
    "very negative": Sentiment.VERY_BEARISH,
    "strongly bearish": Sentiment.VERY_BEARISH,
    "highly bearish": Sentiment.VERY_BEARISH,
    "extremely bearish": Sentiment.VERY_BEARISH,

    # Common LLM synonyms — neutral side
    "mixed": Sentiment.NEUTRAL,
    "balanced": Sentiment.NEUTRAL,
    "hold": Sentiment.NEUTRAL,
    "market perform": Sentiment.NEUTRAL,
    "in-line": Sentiment.NEUTRAL,
    "stable": Sentiment.NEUTRAL,
    "flat": Sentiment.NEUTRAL,
    "sideways": Sentiment.NEUTRAL,
    "uncertain": Sentiment.NEUTRAL,
    "cautiously optimistic": Sentiment.NEUTRAL,
    "cautiously bullish": Sentiment.NEUTRAL,
    "moderately bullish": Sentiment.BULLISH,
    "moderately bearish": Sentiment.BEARISH,
    "slightly bullish": Sentiment.BULLISH,
    "slightly bearish": Sentiment.BEARISH,
    "mildly bullish": Sentiment.BULLISH,
    "mildly bearish": Sentiment.BEARISH,
}


def normalize_sentiment(raw: str, fallback: Sentiment = Sentiment.NEUTRAL) -> Sentiment:
    """
    Convert an arbitrary LLM sentiment string to a valid Sentiment enum value.

    Strategy:
    1. Exact match in the map (case-insensitive)
    2. Substring match — if 'bullish' appears anywhere, use BULLISH etc.
    3. Fall back to the provided default (neutral)

    Args:
        raw: The raw string from the LLM response
        fallback: Returned when no match is found. Default: Sentiment.NEUTRAL

    Returns:
        A valid Sentiment enum value — never raises.
    """
    if not raw:
        return fallback

    cleaned = str(raw).strip().lower().replace("-", "_").replace(" ", "_")

    # 1. Exact match
    if cleaned in _SENTIMENT_MAP:
        return _SENTIMENT_MAP[cleaned]

    # Also try with spaces instead of underscores
    spaced = cleaned.replace("_", " ")
    if spaced in _SENTIMENT_MAP:
        return _SENTIMENT_MAP[spaced]

    # 2. Substring match — order matters (very_ before plain)
    if "very_bullish" in cleaned or "very bullish" in cleaned:
        return Sentiment.VERY_BULLISH
    if "very_bearish" in cleaned or "very bearish" in cleaned:
        return Sentiment.VERY_BEARISH
    if "bullish" in cleaned:
        return Sentiment.BULLISH
    if "bearish" in cleaned:
        return Sentiment.BEARISH
    if "neutral" in cleaned or "mixed" in cleaned or "balanced" in cleaned:
        return Sentiment.NEUTRAL

    # 3. Fallback
    return fallback
