"""Idempotently load normalized articles and NLP analysis into Supabase."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class LoadResult:
    extracted: int
    loaded: int
    sources_upserted: int
    categories_upserted: int
    articles_upserted: int
    analyses_upserted: int
    dry_run: bool


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
        for record in records:
            self._validate_record(record)
        if self.dry_run:
            return LoadResult(
                extracted=len(records),
                loaded=len(records),
                sources_upserted=0,
                categories_upserted=0,
                articles_upserted=0,
                analyses_upserted=0,
                dry_run=True,
            )

        client = self._get_client()
        source_ids: dict[str, str] = {}
        category_ids: dict[str, str] = {}
        source_count = 0
        category_count = 0
        article_count = 0
        analysis_count = 0

        for article in records:
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

            article_payload = {
                "title": article["title"],
                "content": article["content"],
                "url": article["url"],
                "image_url": article.get("image_url"),
                "source_id": source_ids[source_name],
                "category_id": category_ids[category_name],
                "published_at": article["published_at"],
                "status": article["status"],
            }
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
            article_count += 1

            client.table("article_analysis").upsert(
                {
                    "article_id": article_id,
                    **article["analysis"],
                },
                on_conflict="article_id",
            ).execute()
            analysis_count += 1

        return LoadResult(
            extracted=len(records),
            loaded=article_count,
            sources_upserted=source_count,
            categories_upserted=category_count,
            articles_upserted=article_count,
            analyses_upserted=analysis_count,
            dry_run=False,
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        from dotenv import find_dotenv, load_dotenv
        from supabase import create_client

        load_dotenv(find_dotenv(usecwd=True))
        url = os.getenv("SUPABASE_URL", "").strip()
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not url or not service_role_key:
            raise RuntimeError(
                "Live load requires SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY in the backend environment."
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
    def _validate_record(record: dict[str, Any]) -> None:
        required = {"title", "url", "published_at", "status", "analysis"}
        missing = sorted(field for field in required if field not in record)
        if missing:
            raise ValueError(f"Article is missing required fields: {missing}")
        analysis = record["analysis"]
        expected_analysis = {
            "summary",
            "sentiment",
            "sentiment_score",
            "topic",
            "keywords",
        }
        if not isinstance(analysis, dict) or not expected_analysis.issubset(analysis):
            raise ValueError("Article analysis has an invalid structure.")
