"""Retrieval-augmented Q&A over stored real articles."""

from __future__ import annotations

from typing import Any, Callable, Iterable

try:
    from .ai_providers import AiProviders, build_ai_providers_from_environment
    from .semantic_search import semantic_search_articles
except ImportError:
    from ai_providers import AiProviders, build_ai_providers_from_environment
    from semantic_search import semantic_search_articles

Retriever = Callable[[str, Iterable[dict[str, Any]], int], list[dict[str, Any]]]


def answer_question(
    question: str,
    articles: Iterable[dict[str, Any]],
    *,
    providers: AiProviders | None = None,
    retriever: Retriever | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Answer using only retrieved article context and always return sources."""
    normalized = question.strip()
    if not normalized:
        return {
            "answer": "Ask a question about the stored news articles.",
            "sources": [],
            "used_llm": False,
            "retrieved_count": 0,
        }

    records = list(articles)
    retrieve = retriever or _default_retriever
    retrieved = retrieve(normalized, records, max(limit, 1))
    sources = [_source_payload(article) for article in retrieved]
    if not retrieved:
        return {
            "answer": "No stored articles matched the question.",
            "sources": [],
            "used_llm": False,
            "retrieved_count": 0,
        }

    ai = providers or build_ai_providers_from_environment()
    context = _context_from_articles(retrieved)
    if ai.chat is not None:
        try:
            generated = ai.chat.complete(
                [
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the supplied article context. "
                            "If the context is insufficient, say so. Do not "
                            "add facts that are not in the context. Mention "
                            "source titles when relevant."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {normalized}\n\n"
                            f"Article context:\n{context}"
                        ),
                    },
                ],
                temperature=0.1,
            ).strip()
            if generated:
                return {
                    "answer": generated,
                    "sources": sources,
                    "used_llm": True,
                    "retrieved_count": len(retrieved),
                }
        except Exception:
            pass

    return {
        "answer": _extractive_answer(retrieved),
        "sources": sources,
        "used_llm": False,
        "retrieved_count": len(retrieved),
    }


def _default_retriever(
    question: str,
    articles: Iterable[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    return semantic_search_articles(question, articles, limit=limit)


def _context_from_articles(articles: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for index, article in enumerate(articles, start=1):
        analysis = article.get("analysis")
        if not isinstance(analysis, dict):
            analysis = {}
        parts.append(
            "\n".join(
                (
                    f"[{index}] Title: {article.get('title') or 'Untitled'}",
                    f"Topic: {analysis.get('topic') or article.get('category') or 'Unknown'}",
                    f"Summary: {analysis.get('summary') or article.get('content') or ''}",
                    f"URL: {article.get('url') or ''}",
                )
            )
        )
    return "\n\n".join(parts)


def _extractive_answer(articles: list[dict[str, Any]]) -> str:
    bullets: list[str] = []
    for article in articles[:5]:
        analysis = article.get("analysis")
        if not isinstance(analysis, dict):
            analysis = {}
        title = str(article.get("title") or "Untitled article")
        summary = str(analysis.get("summary") or article.get("content") or "").strip()
        if summary:
            bullets.append(f"{title}: {summary}")
        else:
            bullets.append(title)
    return "Based on the retrieved articles: " + " ".join(bullets)


def _source_payload(article: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(article.get("id") or ""),
        "title": str(article.get("title") or "Untitled article"),
        "url": str(article.get("url") or ""),
    }
