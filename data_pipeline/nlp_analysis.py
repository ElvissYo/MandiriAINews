"""Lightweight Phase 1 NLP baseline.

These deterministic functions prove the data contract without downloading large
models. They are intended to be replaced or evaluated against production NLP
models in Phase 5.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]{2,}")
_STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "from",
    "have",
    "into",
    "its",
    "that",
    "the",
    "their",
    "this",
    "through",
    "toward",
    "with",
}
_POSITIVE_WORDS = {
    "accelerates",
    "benefit",
    "growth",
    "improve",
    "innovation",
    "opportunity",
    "strengthening",
}
_NEGATIVE_WORDS = {
    "crisis",
    "decline",
    "fraud",
    "loss",
    "risk",
    "slowdown",
    "threat",
}
_TOPIC_KEYWORDS = {
    "Business": {"business", "company", "industry", "startup"},
    "Economy": {"economy", "economic", "inflation", "trade"},
    "Technology": {"ai", "digital", "software", "technology"},
    "Politics": {"election", "government", "minister", "policy"},
    "Sports": {"athlete", "game", "league", "match"},
    "Finance": {"bank", "finance", "investment", "market"},
    "Entertainment": {"celebrity", "film", "music", "show"},
    "World News": {"global", "international", "world"},
}


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def summarize(text: str, max_characters: int = 280) -> str:
    """Create a short extractive summary for the skeleton pipeline."""
    normalized = " ".join(text.split())
    if len(normalized) <= max_characters:
        return normalized
    return normalized[: max_characters - 3].rsplit(" ", 1)[0] + "..."


def analyze_sentiment(text: str) -> tuple[str, float]:
    """Return a basic lexicon sentiment label and score."""
    tokens = _tokens(text)
    positive = sum(token in _POSITIVE_WORDS for token in tokens)
    negative = sum(token in _NEGATIVE_WORDS for token in tokens)
    denominator = max(positive + negative, 1)
    score = round((positive - negative) / denominator, 5)
    label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
    return label, score


def classify_topic(text: str, fallback: str = "World News") -> str:
    """Choose the topic with the greatest keyword overlap."""
    token_set = set(_tokens(text))
    scores = {
        topic: len(token_set & keywords)
        for topic, keywords in _TOPIC_KEYWORDS.items()
    }
    topic, score = max(scores.items(), key=lambda item: item[1])
    return topic if score else fallback


def extract_keywords(text: str, limit: int = 6) -> list[str]:
    """Return the most frequent informative tokens."""
    counts = Counter(
        token
        for token in _tokens(text)
        if token not in _STOP_WORDS and not token.isdigit()
    )
    return [token for token, _ in counts.most_common(limit)]


def analyze_articles(
    articles: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach an `analysis` object to each normalized article."""
    analyzed: list[dict[str, Any]] = []
    for article in articles:
        text = f"{article['title']}. {article['content']}"
        sentiment, score = analyze_sentiment(text)
        analyzed.append(
            {
                **article,
                "analysis": {
                    "summary": summarize(article["content"]),
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "topic": classify_topic(
                        text,
                        fallback=article.get("category", "World News"),
                    ),
                    "keywords": extract_keywords(text),
                },
            }
        )
    return analyzed
