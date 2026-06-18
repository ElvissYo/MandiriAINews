"""NLP analysis orchestration with provider-backed optional AI upgrades."""

from __future__ import annotations

from typing import Any, Callable, Iterable

try:
    from .ai_providers import (
        AiProviders,
        FunctionSummaryProvider,
        RuleBasedSentimentProvider,
        RuleBasedTopicProvider,
        build_ai_providers_from_environment,
        build_embedding_text,
        extract_keywords as _extract_keywords,
        summarize_text,
    )
except ImportError:
    from ai_providers import (
        AiProviders,
        FunctionSummaryProvider,
        RuleBasedSentimentProvider,
        RuleBasedTopicProvider,
        build_ai_providers_from_environment,
        build_embedding_text,
        extract_keywords as _extract_keywords,
        summarize_text,
    )

SummaryFunction = Callable[[str, str], str]


def summarize(text: str, max_characters: int = 360) -> str:
    """Create a short extractive summary weighted by informative words."""
    return summarize_text(text, max_characters=max_characters)


def analyze_sentiment(text: str) -> tuple[str, float]:
    """Return the deterministic fallback sentiment label and score."""
    result = RuleBasedSentimentProvider().analyze(text)
    return result.label, result.score


def classify_topic(text: str, fallback: str = "World News") -> str:
    """Choose a fallback topic from the supported app categories."""
    return RuleBasedTopicProvider().classify(text, fallback=fallback).topic


def extract_keywords(text: str, limit: int = 6) -> list[str]:
    """Return frequent informative unigrams and useful adjacent phrases."""
    return _extract_keywords(text, limit=limit)


def analyze_articles(
    articles: Iterable[dict[str, Any]],
    *,
    summary_function: SummaryFunction | None = None,
    providers: AiProviders | None = None,
) -> list[dict[str, Any]]:
    """Attach a complete `analysis` object and optional embedding metadata."""
    ai = providers or build_ai_providers_from_environment()
    summary_provider = (
        FunctionSummaryProvider(summary_function)
        if summary_function is not None
        else ai.summary
    )
    fallback_sentiment = RuleBasedSentimentProvider()
    fallback_topic = RuleBasedTopicProvider()
    analyzed: list[dict[str, Any]] = []

    for article in articles:
        title = str(article.get("title") or "")
        content = str(article.get("content") or "")
        text = f"{title}. {content}".strip()
        fallback_summary = summarize(content or title)
        summary = fallback_summary
        try:
            generated = summary_provider.summarize(title, content).strip()
            if generated:
                summary = generated
        except Exception:
            summary = fallback_summary

        try:
            sentiment_result = ai.sentiment.analyze(text)
        except Exception:
            sentiment_result = fallback_sentiment.analyze(text)

        try:
            topic_result = ai.topic.classify(
                text,
                fallback=str(article.get("category") or "World News"),
            )
        except Exception:
            topic_result = fallback_topic.classify(
                text,
                fallback=str(article.get("category") or "World News"),
            )

        enriched: dict[str, Any] = {
            **article,
            "analysis": {
                "summary": summary,
                "sentiment": sentiment_result.label,
                "sentiment_score": sentiment_result.score,
                "topic": topic_result.topic,
                "keywords": extract_keywords(text),
            },
        }

        embedding_text = build_embedding_text(title, summary, content)
        try:
            embedding = ai.embedding.embed(embedding_text)
        except Exception:
            embedding = None
        if embedding is not None:
            enriched["embedding"] = {
                "text": embedding.text,
                "vector": embedding.vector,
                "provider": embedding.provider,
                "dimensions": embedding.dimensions,
            }

        analyzed.append(enriched)
    return analyzed
