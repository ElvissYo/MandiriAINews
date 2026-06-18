"""Semantic retrieval helpers with keyword fallback."""

from __future__ import annotations

from typing import Any, Iterable

try:
    from .ai_providers import (
        EmbeddingProvider,
        build_ai_providers_from_environment,
        cosine_similarity,
        tokenize,
        vector_literal,
    )
except ImportError:
    from ai_providers import (
        EmbeddingProvider,
        build_ai_providers_from_environment,
        cosine_similarity,
        tokenize,
        vector_literal,
    )


def semantic_search_articles(
    query: str,
    articles: Iterable[dict[str, Any]],
    *,
    embedding_provider: EmbeddingProvider | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank in-memory article records by embeddings, falling back to keywords."""
    records = list(articles)
    normalized = query.strip()
    if not normalized:
        return records[: max(limit, 0)]

    provider = embedding_provider or build_ai_providers_from_environment().embedding
    try:
        query_embedding = provider.embed(normalized)
    except Exception:
        query_embedding = None
    if query_embedding is None:
        return keyword_search_articles(normalized, records, limit=limit)

    ranked: list[tuple[float, dict[str, Any]]] = []
    for article in records:
        vector = _article_vector(article)
        if vector is None:
            continue
        score = cosine_similarity(query_embedding.vector, vector)
        if score > 0:
            ranked.append((score, article))

    if not ranked:
        return keyword_search_articles(normalized, records, limit=limit)
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [article for _, article in ranked[: max(limit, 0)]]


def keyword_search_articles(
    query: str,
    articles: Iterable[dict[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Simple backend-compatible fallback used when vector search is absent."""
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return list(articles)[: max(limit, 0)]

    ranked: list[tuple[int, dict[str, Any]]] = []
    for article in articles:
        haystack = _searchable_text(article)
        haystack_tokens = set(tokenize(haystack))
        overlap = len(query_tokens & haystack_tokens)
        phrase_bonus = 3 if query.lower() in haystack.lower() else 0
        score = overlap + phrase_bonus
        if score > 0:
            ranked.append((score, article))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [article for _, article in ranked[: max(limit, 0)]]


def semantic_search_supabase(
    client: Any,
    query: str,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    limit: int = 10,
) -> list[str]:
    """Return article IDs from the optional pgvector RPC, or an empty list."""
    normalized = query.strip()
    if not normalized:
        return []
    provider = embedding_provider or build_ai_providers_from_environment().embedding
    try:
        embedding = provider.embed(normalized)
        if embedding is None:
            return []
        response = client.rpc(
            "match_articles_by_embedding",
            {
                "query_embedding": vector_literal(embedding.vector),
                "match_count": limit,
                "query_provider": embedding.provider,
            },
        ).execute()
    except Exception:
        return []
    return [
        str(row["article_id"])
        for row in (response.data or [])
        if isinstance(row, dict) and row.get("article_id")
    ]


def _article_vector(article: dict[str, Any]) -> list[float] | None:
    embedding = article.get("embedding")
    if not isinstance(embedding, dict):
        return None
    vector = embedding.get("vector")
    if not isinstance(vector, list) or not vector:
        return None
    try:
        return [float(value) for value in vector]
    except (TypeError, ValueError):
        return None


def _searchable_text(article: dict[str, Any]) -> str:
    analysis = article.get("analysis")
    if not isinstance(analysis, dict):
        analysis = {}
    keywords = analysis.get("keywords")
    return " ".join(
        str(part or "")
        for part in (
            article.get("title"),
            article.get("content"),
            analysis.get("summary"),
            analysis.get("topic"),
            " ".join(keywords if isinstance(keywords, list) else []),
        )
    )
