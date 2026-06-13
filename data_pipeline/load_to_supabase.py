"""Load normalized and analyzed articles into Supabase."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class LoadResult:
    extracted: int
    loaded: int
    dry_run: bool


class SupabaseLoader:
    """Thin repository for Phase 1 article upserts."""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run
        self._client: Any | None = None

    def load(self, articles: Iterable[dict[str, Any]]) -> LoadResult:
        records = list(articles)
        if self.dry_run:
            return LoadResult(
                extracted=len(records),
                loaded=len(records),
                dry_run=True,
            )

        client = self._get_client()
        loaded = 0
        for article in records:
            source_id = self._upsert_lookup(
                client,
                "sources",
                {
                    "name": article["source_name"],
                    "url": article.get("source_url"),
                    "country": article.get("source_country"),
                },
            )
            category_id = self._upsert_lookup(
                client,
                "categories",
                {
                    "name": article["category"],
                    "description": None,
                },
            )
            article_payload = {
                "title": article["title"],
                "content": article["content"],
                "url": article["url"],
                "image_url": article.get("image_url"),
                "source_id": source_id,
                "category_id": category_id,
                "published_at": article["published_at"],
                "status": article["status"],
            }
            response = (
                client.table("articles")
                .upsert(article_payload, on_conflict="url")
                .execute()
            )
            article_id = self._response_id(
                response,
                table="articles",
                column="url",
                value=article["url"],
            )
            client.table("article_analysis").upsert(
                {
                    "article_id": article_id,
                    **article["analysis"],
                },
                on_conflict="article_id",
            ).execute()
            loaded += 1

        return LoadResult(
            extracted=len(records),
            loaded=loaded,
            dry_run=False,
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        from dotenv import load_dotenv
        from supabase import create_client

        load_dotenv()
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
            response,
            table=table,
            column="name",
            value=payload["name"],
        )

    @staticmethod
    def _response_id(
        response: Any,
        *,
        table: str,
        column: str,
        value: str,
    ) -> str:
        if response.data:
            return str(response.data[0]["id"])
        raise RuntimeError(
            f"Supabase returned no row for {table}.{column}={value!r}."
        )
