"""Resilient, idempotent loading and run observability for Supabase."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlsplit

_BLOCKED_RUNTIME_MARKERS = (
    re.compile(r"\bdummy\b", re.IGNORECASE),
    re.compile(r"\bdemo (?:article|content|data)\b", re.IGNORECASE),
    re.compile(r"\bsample article\b", re.IGNORECASE),
    re.compile(r"\btest article\b", re.IGNORECASE),
    re.compile(r"\bplaceholder\b", re.IGNORECASE),
    re.compile(r"\blorem ipsum\b", re.IGNORECASE),
)
_RESERVED_TEST_HOSTS = {"example.com", "example.org", "example.net"}


@dataclass(frozen=True)
class LoadResult:
    received: int
    loaded: int
    inserted: int
    skipped_duplicates: int
    failed: int
    sources_upserted: int
    categories_upserted: int
    analyses_upserted: int
    dry_run: bool
    embeddings_upserted: int = 0
    errors: tuple[str, ...] = ()


class SupabaseLoader:
    """Small, testable repository for trusted ETL upserts."""

    def __init__(
        self,
        dry_run: bool = True,
        *,
        client: Any | None = None,
    ) -> None:
        self.dry_run = dry_run
        self._client = client

    def load(self, articles: Iterable[dict[str, Any]]) -> LoadResult:
        records = list(articles)
        valid_records: list[dict[str, Any]] = []
        errors: list[str] = []
        for index, record in enumerate(records):
            validation_error = self._validation_error(record)
            if validation_error is None:
                valid_records.append(record)
            else:
                errors.append(f"article[{index}]: {validation_error}")

        if self.dry_run:
            return LoadResult(
                received=len(records),
                loaded=len(valid_records),
                inserted=0,
                skipped_duplicates=0,
                failed=len(errors),
                sources_upserted=0,
                categories_upserted=0,
                analyses_upserted=0,
                dry_run=True,
                errors=tuple(errors),
            )

        client = self._get_client()
        source_ids: dict[str, str] = {}
        category_ids: dict[str, str] = {}
        source_count = 0
        category_count = 0
        inserted = 0
        duplicates = 0
        analysis_count = 0
        embedding_count = 0

        for article in valid_records:
            try:
                source_name = article["source_name"]
                if source_name not in source_ids:
                    source_ids[source_name] = self._upsert_lookup(
                        client,
                        "sources",
                        {
                            "name": source_name,
                            "url": article.get("source_url"),
                            "country": article.get("source_country"),
                        },
                    )
                    source_count += 1

                category_name = article["category"]
                if category_name not in category_ids:
                    category_ids[category_name] = self._upsert_lookup(
                        client,
                        "categories",
                        {
                            "name": category_name,
                            "description": None,
                        },
                    )
                    category_count += 1

                existing_id = self._existing_article_id(
                    client,
                    article["url"],
                    article.get("canonical_url"),
                )
                article_payload = {
                    "title": article["title"],
                    "content": article["content"],
                    "url": article["url"],
                    "canonical_url": article.get("canonical_url"),
                    "image_url": article.get("image_url"),
                    "source_id": source_ids[source_name],
                    "category_id": category_ids[category_name],
                    "published_at": article["published_at"],
                    "status": article["status"],
                    "content_is_snippet": bool(
                        article.get("content_is_snippet", False)
                    ),
                    "extraction_method": article.get("extraction_method")
                    or "source_snippet",
                    "extraction_status": article.get("extraction_status")
                    or (
                        "snippet"
                        if bool(article.get("content_is_snippet", False))
                        else "full_content"
                    ),
                }
                if existing_id is None:
                    response = (
                        client.table("articles")
                        .upsert(article_payload, on_conflict="url")
                        .execute()
                    )
                    article_id = self._response_id(
                        client,
                        response,
                        table="articles",
                        column="url",
                        value=article["url"],
                    )
                else:
                    (
                        client.table("articles")
                        .update(article_payload)
                        .eq("id", existing_id)
                        .execute()
                    )
                    article_id = existing_id
                client.table("article_analysis").upsert(
                    {
                        "article_id": article_id,
                        **article["analysis"],
                    },
                    on_conflict="article_id",
                ).execute()
                if article.get("embedding"):
                    try:
                        self._upsert_embedding(client, article_id, article["embedding"])
                        embedding_count += 1
                    except Exception as error:
                        errors.append(
                            f"{article.get('url', 'unknown article')}: "
                            f"embedding skipped: {self._safe_error(error)}"
                        )
                if existing_id is None:
                    inserted += 1
                else:
                    duplicates += 1
                analysis_count += 1
            except Exception as error:
                errors.append(
                    f"{article.get('url', 'unknown article')}: "
                    f"{self._safe_error(error)}"
                )

        loaded = inserted + duplicates
        return LoadResult(
            received=len(records),
            loaded=loaded,
            inserted=inserted,
            skipped_duplicates=duplicates,
            failed=len(records) - loaded,
            sources_upserted=source_count,
            categories_upserted=category_count,
            analyses_upserted=analysis_count,
            embeddings_upserted=embedding_count,
            dry_run=False,
            errors=tuple(errors[:20]),
        )

    def record_pipeline_run(self, payload: dict[str, Any]) -> None:
        """Persist one backend-only run summary."""
        if self.dry_run:
            return
        client = self._get_client()
        client.table("pipeline_runs").insert(payload).execute()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        from dotenv import find_dotenv, load_dotenv
        from supabase import create_client

        load_dotenv(find_dotenv(usecwd=True))
        url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if url.endswith("/rest/v1"):
            url = url[: -len("/rest/v1")]
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", url),
                ("SUPABASE_SERVICE_ROLE_KEY", service_role_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Live load is missing backend environment variables: "
                + ", ".join(missing)
                + "."
            )

        self._client = create_client(url, service_role_key)
        return self._client

    def _upsert_lookup(
        self,
        client: Any,
        table: str,
        payload: dict[str, Any],
    ) -> str:
        response = (
            client.table(table)
            .upsert(payload, on_conflict="name")
            .execute()
        )
        return self._response_id(
            client,
            response,
            table=table,
            column="name",
            value=payload["name"],
        )

    @staticmethod
    def _existing_article_id(
        client: Any,
        url: str,
        canonical_url: str | None = None,
    ) -> str | None:
        lookup_values = [value for value in (canonical_url, url) if value]
        for value in lookup_values:
            response = (
                client.table("articles")
                .select("id")
                .eq("canonical_url", value)
                .limit(1)
                .execute()
            )
            if response.data:
                return str(response.data[0]["id"])
        response = (
            client.table("articles")
            .select("id")
            .eq("url", url)
            .limit(1)
            .execute()
        )
        if response.data:
            return str(response.data[0]["id"])
        return None

    @staticmethod
    def _response_id(
        client: Any,
        response: Any,
        *,
        table: str,
        column: str,
        value: str,
    ) -> str:
        if response.data:
            return str(response.data[0]["id"])
        lookup = (
            client.table(table)
            .select("id")
            .eq(column, value)
            .limit(1)
            .execute()
        )
        if lookup.data:
            return str(lookup.data[0]["id"])
        raise RuntimeError(
            f"Supabase returned no row for {table}.{column}={value!r}."
        )

    @staticmethod
    def _upsert_embedding(
        client: Any,
        article_id: str,
        embedding: dict[str, Any],
    ) -> None:
        vector = embedding.get("vector")
        if not isinstance(vector, list) or not vector:
            return
        payload = {
            "article_id": article_id,
            "embedding_text": str(embedding.get("text") or ""),
            "embedding": vector,
            "embedding_provider": str(embedding.get("provider") or "unknown"),
            "embedding_dimensions": int(embedding.get("dimensions") or len(vector)),
        }
        client.table("article_embeddings").upsert(
            payload,
            on_conflict="article_id",
        ).execute()

    @staticmethod
    def _validation_error(record: dict[str, Any]) -> str | None:
        required = {
            "title",
            "url",
            "published_at",
            "status",
            "source_name",
            "category",
            "analysis",
        }
        missing = sorted(field for field in required if field not in record)
        if missing:
            return f"missing required fields: {missing}"
        searchable = " ".join(
            str(record.get(field) or "")
            for field in ("title", "content", "source_name")
        )
        if any(pattern.search(searchable) for pattern in _BLOCKED_RUNTIME_MARKERS):
            return "runtime demo/test content is not allowed"
        hostname = urlsplit(str(record.get("url") or "")).hostname
        if hostname in _RESERVED_TEST_HOSTS:
            return "reserved example-domain articles are not allowed"
        analysis = record["analysis"]
        expected_analysis = {
            "summary",
            "sentiment",
            "sentiment_score",
            "topic",
            "keywords",
        }
        if not isinstance(analysis, dict) or not expected_analysis.issubset(analysis):
            return "analysis has an invalid structure"
        if not str(analysis["summary"]).strip():
            return "summary is empty"
        if analysis["sentiment"] not in {"positive", "neutral", "negative"}:
            return "sentiment label is invalid"
        if not str(analysis["topic"]).strip():
            return "topic is empty"
        if not isinstance(analysis["keywords"], list) or not analysis["keywords"]:
            return "keywords must be a non-empty list"
        extraction_status = str(record.get("extraction_status") or "snippet")
        if extraction_status not in {
            "full_content",
            "snippet",
            "failed",
            "blocked",
            "blocked_by_meta_robots",
            "invalid_url",
        }:
            return "extraction_status is invalid"
        return None

    @staticmethod
    def _safe_error(error: BaseException) -> str:
        message = " ".join(str(error).split())
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if service_key:
            message = message.replace(service_key, "[redacted]")
        return message[:500]
