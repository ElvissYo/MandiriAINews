"""AI provider abstractions with deterministic local fallbacks."""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Protocol

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
TOPIC_KEYWORDS = {
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
TOPICS = tuple(TOPIC_KEYWORDS)


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float


@dataclass(frozen=True)
class TopicResult:
    topic: str
    score: float = 0


@dataclass(frozen=True)
class EmbeddingResult:
    text: str
    vector: list[float]
    provider: str

    @property
    def dimensions(self) -> int:
        return len(self.vector)


class SummaryProvider(Protocol):
    name: str

    def summarize(self, title: str, content: str) -> str:
        ...


class SentimentProvider(Protocol):
    name: str

    def analyze(self, text: str) -> SentimentResult:
        ...


class TopicProvider(Protocol):
    name: str

    def classify(self, text: str, fallback: str = "World News") -> TopicResult:
        ...


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, text: str) -> EmbeddingResult | None:
        ...


class ChatProvider(Protocol):
    name: str

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> str:
        ...


@dataclass(frozen=True)
class AiProviders:
    summary: SummaryProvider
    sentiment: SentimentProvider
    topic: TopicProvider
    embedding: EmbeddingProvider
    chat: ChatProvider | None = None


class RuleBasedSummaryProvider:
    name = "rule-based"

    def summarize(self, title: str, content: str) -> str:
        return summarize_text(content or title)


class OpenAiCompatibleChatProvider:
    name = "openai-compatible"

    def __init__(self, endpoint: str, api_key: str, model: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> str:
        import requests

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": temperature,
                "messages": messages,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])


class LlmSummaryProvider:
    name = "llm-summary"

    def __init__(
        self,
        chat_provider: ChatProvider,
        fallback: SummaryProvider | None = None,
    ) -> None:
        self._chat_provider = chat_provider
        self._fallback = fallback or RuleBasedSummaryProvider()

    def summarize(self, title: str, content: str) -> str:
        fallback = self._fallback.summarize(title, content)
        try:
            generated = self._chat_provider.complete(
                [
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
                temperature=0.2,
            ).strip()
        except Exception:
            return fallback
        return generated or fallback


class RuleBasedSentimentProvider:
    name = "rule-based"

    def analyze(self, text: str) -> SentimentResult:
        tokens = tokenize(text)
        positive = sum(token in _POSITIVE_WORDS for token in tokens)
        negative = sum(token in _NEGATIVE_WORDS for token in tokens)
        evidence = positive + negative
        score = round((positive - negative) / max(evidence, 1), 5)
        label = (
            "positive"
            if score > 0.15
            else "negative"
            if score < -0.15
            else "neutral"
        )
        return SentimentResult(label=label, score=score)


class TransformerSentimentProvider:
    name = "transformer"

    def __init__(self, model_name: str | None = None) -> None:
        from transformers import pipeline

        self._pipeline = pipeline(
            "sentiment-analysis",
            model=model_name or os.getenv("AI_SENTIMENT_MODEL") or None,
        )

    def analyze(self, text: str) -> SentimentResult:
        if not text.strip():
            return SentimentResult(label="neutral", score=0)
        result = self._pipeline(text[:4000])[0]
        raw_label = str(result.get("label", "")).lower()
        confidence = float(result.get("score", 0))
        if "neg" in raw_label or raw_label in {"1 star", "2 stars"}:
            label = "negative"
            score = -confidence
        elif "pos" in raw_label or raw_label in {"4 stars", "5 stars"}:
            label = "positive"
            score = confidence
        else:
            label = "neutral"
            score = 0
        return SentimentResult(label=label, score=round(score, 5))


class RuleBasedTopicProvider:
    name = "rule-based"

    def classify(self, text: str, fallback: str = "World News") -> TopicResult:
        token_set = set(tokenize(text))
        scores = {
            topic: len(token_set & keywords)
            for topic, keywords in TOPIC_KEYWORDS.items()
        }
        topic, score = max(scores.items(), key=lambda item: item[1])
        selected = topic if score else _valid_topic(fallback)
        return TopicResult(topic=selected, score=float(score))


class ZeroShotTopicProvider:
    name = "transformer-zero-shot"

    def __init__(self, model_name: str | None = None) -> None:
        from transformers import pipeline

        self._pipeline = pipeline(
            "zero-shot-classification",
            model=model_name or os.getenv("AI_TOPIC_MODEL") or None,
        )

    def classify(self, text: str, fallback: str = "World News") -> TopicResult:
        if not text.strip():
            return TopicResult(topic=_valid_topic(fallback), score=0)
        result = self._pipeline(text[:4000], candidate_labels=list(TOPICS))
        labels = result.get("labels") or []
        scores = result.get("scores") or []
        if labels:
            return TopicResult(
                topic=_valid_topic(str(labels[0])),
                score=round(float(scores[0]), 5) if scores else 0,
            )
        return TopicResult(topic=_valid_topic(fallback), score=0)


class NullEmbeddingProvider:
    name = "none"

    def embed(self, text: str) -> EmbeddingResult | None:
        return None


class HashingEmbeddingProvider:
    """Small no-key embedding provider for local fallback and tests."""

    name = "hash"

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = max(dimensions, 8)

    def embed(self, text: str) -> EmbeddingResult | None:
        normalized = " ".join(text.split())
        tokens = tokenize(normalized)
        if not normalized or not tokens:
            return None
        vector = [0.0] * self.dimensions
        for token in tokens:
            hashed = _fnv1a_32(token)
            index = hashed % self.dimensions
            sign = 1.0 if (hashed & 0x80000000) == 0 else -1.0
            vector[index] += sign
        return EmbeddingResult(
            text=normalized,
            vector=normalize_vector(vector, self.dimensions),
            provider=self.name,
        )


class SentenceTransformerEmbeddingProvider:
    name = "sentence-transformers"

    def __init__(
        self,
        model_name: str | None = None,
        *,
        dimensions: int = 384,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.dimensions = dimensions
        self._model_name = (
            model_name
            or os.getenv("AI_EMBEDDING_MODEL")
            or "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._model = SentenceTransformer(self._model_name)

    def embed(self, text: str) -> EmbeddingResult | None:
        normalized = " ".join(text.split())
        if not normalized:
            return None
        vector = self._model.encode(normalized, normalize_embeddings=True)
        return EmbeddingResult(
            text=normalized,
            vector=normalize_vector([float(value) for value in vector], self.dimensions),
            provider=self.name,
        )


class FunctionSummaryProvider:
    name = "function"

    def __init__(self, callback: Any) -> None:
        self._callback = callback

    def summarize(self, title: str, content: str) -> str:
        return str(self._callback(title, content))


def build_ai_providers_from_environment() -> AiProviders:
    chat = _build_chat_provider()
    summary: SummaryProvider = (
        LlmSummaryProvider(chat) if chat is not None else RuleBasedSummaryProvider()
    )
    return AiProviders(
        summary=summary,
        sentiment=_build_sentiment_provider(),
        topic=_build_topic_provider(),
        embedding=_build_embedding_provider(),
        chat=chat,
    )


def summarize_text(text: str, max_characters: int = 360) -> str:
    """Create a short extractive summary weighted by informative words."""
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    if len(normalized) <= max_characters:
        return normalized

    sentences = [item.strip() for item in _SENTENCE_RE.split(normalized)]
    if len(sentences) == 1:
        return truncate(normalized, max_characters)

    frequencies = Counter(
        token for token in tokenize(normalized) if token not in _STOP_WORDS
    )
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: (
            sum(frequencies[token] for token in tokenize(item[1])),
            -item[0],
        ),
        reverse=True,
    )
    selected_indexes = sorted(index for index, _ in ranked[:2])
    summary = " ".join(sentences[index] for index in selected_indexes)
    return truncate(summary, max_characters)


def extract_keywords(text: str, limit: int = 6) -> list[str]:
    """Return frequent informative unigrams and useful adjacent phrases."""
    tokens = [
        token
        for token in tokenize(text)
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


def build_embedding_text(
    title: str,
    summary: str,
    content: str,
    *,
    content_characters: int = 1200,
) -> str:
    snippet = " ".join(content.split())[:content_characters]
    return " ".join(part for part in (title.strip(), summary.strip(), snippet) if part)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0
    return numerator / (left_norm * right_norm)


def normalize_vector(values: list[float], dimensions: int) -> list[float]:
    vector = values[:dimensions]
    if len(vector) < dimensions:
        vector.extend([0.0] * (dimensions - len(vector)))
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return [0.0] * dimensions
    return [round(value / norm, 8) for value in vector]


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def truncate(value: str, max_characters: int) -> str:
    if len(value) <= max_characters:
        return value
    shortened = value[: max(max_characters - 3, 0)].rsplit(" ", 1)[0]
    return f"{shortened}..."


def _build_chat_provider() -> ChatProvider | None:
    endpoint = os.getenv("LLM_SUMMARY_API_URL", "").strip()
    api_key = os.getenv("LLM_SUMMARY_API_KEY", "").strip()
    model = os.getenv("LLM_SUMMARY_MODEL", "").strip()
    if not endpoint or not api_key or not model:
        return None
    return OpenAiCompatibleChatProvider(endpoint, api_key, model)


def _build_sentiment_provider() -> SentimentProvider:
    mode = os.getenv("AI_SENTIMENT_PROVIDER", "").strip().lower()
    transformers_enabled = _truthy(os.getenv("AI_ENABLE_TRANSFORMERS", ""))
    if mode in {"transformer", "transformers"} or transformers_enabled:
        try:
            return TransformerSentimentProvider()
        except Exception:
            return RuleBasedSentimentProvider()
    return RuleBasedSentimentProvider()


def _build_topic_provider() -> TopicProvider:
    mode = os.getenv("AI_TOPIC_PROVIDER", "").strip().lower()
    transformers_enabled = _truthy(os.getenv("AI_ENABLE_TRANSFORMERS", ""))
    if mode in {"transformer", "zero-shot", "zero_shot"} or transformers_enabled:
        try:
            return ZeroShotTopicProvider()
        except Exception:
            return RuleBasedTopicProvider()
    return RuleBasedTopicProvider()


def _build_embedding_provider() -> EmbeddingProvider:
    mode = os.getenv("AI_EMBEDDING_PROVIDER", "none").strip().lower()
    dimensions = _int_env("AI_EMBEDDING_DIMENSIONS", 384)
    if mode in {"sentence-transformers", "sentence_transformers", "transformer"}:
        try:
            return SentenceTransformerEmbeddingProvider(dimensions=dimensions)
        except Exception:
            return NullEmbeddingProvider()
    if mode == "hash":
        return HashingEmbeddingProvider(dimensions=dimensions)
    if mode == "auto":
        try:
            return SentenceTransformerEmbeddingProvider(dimensions=dimensions)
        except Exception:
            return HashingEmbeddingProvider(dimensions=dimensions)
    return NullEmbeddingProvider()


def _valid_topic(value: str) -> str:
    normalized = value.strip()
    return normalized if normalized in TOPIC_KEYWORDS else "World News"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, fallback: int) -> int:
    try:
        return int(os.getenv(name, str(fallback)))
    except ValueError:
        return fallback


def _fnv1a_32(text: str) -> int:
    value = 2166136261
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return value
