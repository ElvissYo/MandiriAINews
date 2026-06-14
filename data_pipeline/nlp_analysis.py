"""MVP NLP analysis with deterministic fallbacks and optional LLM summaries."""

from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any, Callable, Iterable

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]{1,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_STOP_WORDS = {
    "about", "after", "akan", "also", "and", "are", "atau", "bagi", "dalam",
    "dan", "dari", "dengan", "for", "from", "have", "ini", "into", "its",
    "karena", "ke", "lebih", "mereka", "oleh", "pada", "para", "sebagai",
    "that", "the", "their", "this", "through", "toward", "untuk", "yang",
    "with",
}
_POSITIVE_WORDS = {
    "accelerates", "benefit", "better", "gain", "gained", "growth", "improve",
    "improving", "innovation", "opportunity", "positive", "strengthening",
    "strong", "surge", "tumbuh", "meningkat", "kemajuan", "peluang", "untung",
}
_NEGATIVE_WORDS = {
    "crisis", "decline", "drop", "fraud", "loss", "negative", "risk",
    "slowdown", "threat", "turun", "krisis", "kerugian", "risiko", "ancaman",
}
_TOPIC_KEYWORDS = {
    "Business": {"business", "company", "industry", "startup", "perusahaan"},
    "Economy": {
        "economy", "economic", "inflation", "trade", "ekonomi", "inflasi",
        "perdagangan",
    },
    "Technology": {
        "ai", "digital", "software", "technology", "teknologi", "internet",
        "startup",
    },
    "Politics": {
        "election", "government", "minister", "policy", "politik", "pemilu",
        "pemerintah", "kebijakan",
    },
    "Sports": {
        "athlete", "game", "league", "match", "olahraga", "liga", "pertandingan",
    },
    "Finance": {
        "bank", "finance", "investment", "market", "banking", "keuangan",
        "investasi", "pasar",
    },
    "Entertainment": {
        "celebrity", "film", "music", "show", "hiburan", "musik", "selebriti",
    },
    "World News": {
        "global", "international", "world", "dunia", "internasional",
    },
}

SummaryFunction = Callable[[str, str], str]


def summarize(text: str, max_characters: int = 360) -> str:
    """Create a short extractive summary weighted by informative words."""
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    if len(normalized) <= max_characters:
        return normalized

    sentences = [item.strip() for item in _SENTENCE_RE.split(normalized)]
    if len(sentences) == 1:
        return _truncate(normalized, max_characters)

    frequencies = Counter(
        token for token in _tokens(normalized) if token not in _STOP_WORDS
    )
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: (
            sum(frequencies[token] for token in _tokens(item[1])),
            -item[0],
        ),
        reverse=True,
    )
    selected_indexes = sorted(index for index, _ in ranked[:2])
    summary = " ".join(sentences[index] for index in selected_indexes)
    return _truncate(summary, max_characters)


def analyze_sentiment(text: str) -> tuple[str, float]:
    """Return a lexicon sentiment label and normalized score."""
    tokens = _tokens(text)
    positive = sum(token in _POSITIVE_WORDS for token in tokens)
    negative = sum(token in _NEGATIVE_WORDS for token in tokens)
    evidence = positive + negative
    score = round((positive - negative) / max(evidence, 1), 5)
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
    return topic if score else (fallback.strip() or "World News")


def extract_keywords(text: str, limit: int = 6) -> list[str]:
    """Return frequent informative unigrams and useful adjacent phrases."""
    tokens = [
        token
        for token in _tokens(text)
        if token not in _STOP_WORDS and not token.isdigit()
    ]
    unigram_counts = Counter(tokens)
    bigram_counts = Counter(
        f"{left} {right}"
        for left, right in zip(tokens, tokens[1:])
        if left != right
    )
    candidates = [
        *(
            (phrase, count + 0.5)
            for phrase, count in bigram_counts.items()
            if count > 1
        ),
        *((token, float(count)) for token, count in unigram_counts.items()),
    ]
    ranked = sorted(candidates, key=lambda item: (-item[1], item[0]))
    return [keyword for keyword, _ in ranked[: max(limit, 0)]]


def analyze_articles(
    articles: Iterable[dict[str, Any]],
    *,
    summary_function: SummaryFunction | None = None,
) -> list[dict[str, Any]]:
    """Attach a complete `analysis` object to each normalized article."""
    configured_summary = summary_function or _llm_summary_from_environment()
    analyzed: list[dict[str, Any]] = []
    for article in articles:
        title = str(article.get("title") or "")
        content = str(article.get("content") or "")
        text = f"{title}. {content}".strip()
        fallback_summary = summarize(content or title)
        summary = fallback_summary
        if configured_summary is not None:
            try:
                generated = configured_summary(title, content).strip()
                if generated:
                    summary = generated
            except Exception:
                summary = fallback_summary

        sentiment, score = analyze_sentiment(text)
        analyzed.append(
            {
                **article,
                "analysis": {
                    "summary": summary,
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "topic": classify_topic(
                        text,
                        fallback=str(article.get("category") or "World News"),
                    ),
                    "keywords": extract_keywords(text),
                },
            }
        )
    return analyzed


def _llm_summary_from_environment() -> SummaryFunction | None:
    endpoint = os.getenv("LLM_SUMMARY_API_URL", "").strip()
    api_key = os.getenv("LLM_SUMMARY_API_KEY", "").strip()
    model = os.getenv("LLM_SUMMARY_MODEL", "").strip()
    if not endpoint or not api_key or not model:
        return None

    def generate(title: str, content: str) -> str:
        import requests

        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Summarize the news article in two concise, factual "
                            "sentences. Do not add facts not present in the text."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Title: {title}\n\nArticle: {content}",
                    },
                ],
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])

    return generate


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _truncate(value: str, max_characters: int) -> str:
    if len(value) <= max_characters:
        return value
    shortened = value[: max(max_characters - 3, 0)].rsplit(" ", 1)[0]
    return f"{shortened}..."
