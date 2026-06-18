import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from data_pipeline.clean_news import clean_articles
from data_pipeline.ai_providers import (
    AiProviders,
    HashingEmbeddingProvider,
    LlmSummaryProvider,
    RuleBasedSentimentProvider,
    RuleBasedSummaryProvider,
    RuleBasedTopicProvider,
)
from data_pipeline.evaluate_nlp import evaluate_articles
from data_pipeline.extract_news import ExtractionResult, extract_news_with_report
from data_pipeline.load_to_supabase import SupabaseLoader
from data_pipeline.main_pipeline import run_pipeline
from data_pipeline.nlp_analysis import analyze_articles, analyze_sentiment
from data_pipeline.rag_qa import answer_question
from data_pipeline.semantic_search import (
    semantic_search_articles,
    semantic_search_supabase,
)


class CleaningTest(unittest.TestCase):
    def test_cleaning_removes_invalid_html_and_duplicates(self) -> None:
        raw = [
            {
                "title": "  <b>Market Update</b> ",
                "content": "<p>Markets gain.</p><script>ignore()</script>",
                "url": "HTTPS://Example.com/story/?utm_source=test#section",
                "source_name": " Example Daily - Google News ",
                "published_at": "2026-06-14T08:30:00+07:00",
                "content_is_snippet": True,
            },
            {
                "title": "Market Update",
                "url": "https://other.example/story",
            },
            {"title": "", "url": "https://example.com/missing-title"},
            {"title": "Missing URL", "url": ""},
        ]

        cleaned = clean_articles(raw)

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["title"], "Market Update")
        self.assertEqual(cleaned[0]["content"], "Markets gain.")
        self.assertEqual(cleaned[0]["url"], "https://example.com/story")
        self.assertEqual(cleaned[0]["source_name"], "Example Daily")
        self.assertEqual(cleaned[0]["status"], "published")
        self.assertTrue(cleaned[0]["content_is_snippet"])
        self.assertEqual(cleaned[0]["published_at"], "2026-06-14T01:30:00+00:00")


class ExtractionTest(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "NEWS_API_KEY": "test-news-key",
            "NEWS_GDELT_ENABLED": "true",
            "NEWS_RETRY_DELAY_SECONDS": "0",
        },
    )
    def test_auto_prefers_newsapi_when_key_exists(self) -> None:
        session = _NewsApiSession()

        result = extract_news_with_report(
            source="auto",
            limit=1,
            session=session,
        )

        self.assertEqual(result.provider, "newsapi")
        self.assertEqual(session.urls, ["https://newsapi.org/v2/everything"])

    @patch.dict(
        os.environ,
        {
            "NEWS_GDELT_QUERY": "Indonesia OR ASEAN",
            "NEWS_GDELT_TIMESPAN": "1d",
            "NEWS_GDELT_MAX_RECORDS": "50",
            "NEWS_RETRY_DELAY_SECONDS": "0",
        },
    )
    def test_gdelt_extracts_normalized_open_data_articles(self) -> None:
        session = _GdeltSession()

        result = extract_news_with_report(
            source="gdelt",
            limit=2,
            session=session,
        )

        self.assertEqual(result.provider, "gdelt")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(result.articles), 2)
        self.assertEqual(
            result.articles[0]["published_at"],
            "2026-06-14T10:15:00+00:00",
        )
        self.assertEqual(result.articles[0]["source_name"], "example.com")
        self.assertEqual(result.articles[0]["content"], "Indonesia market gains")
        self.assertTrue(result.articles[0]["content_is_snippet"])
        self.assertEqual(session.params["query"], "(Indonesia OR ASEAN)")
        self.assertEqual(session.params["timespan"], "1d")
        self.assertEqual(session.params["maxrecords"], 2)

        cleaned = clean_articles(result.articles)
        analyzed = analyze_articles(cleaned)
        self.assertEqual(len(cleaned), 1)
        self.assertTrue(analyzed[0]["analysis"]["summary"])
        self.assertTrue(analyzed[0]["analysis"]["keywords"])

    @patch.dict(
        os.environ,
        {
            "NEWS_API_KEY": "",
            "NEWS_GDELT_ENABLED": "true",
            "NEWS_RETRY_DELAY_SECONDS": "0",
        },
    )
    def test_auto_uses_enabled_gdelt_before_rss(self) -> None:
        session = _GdeltSession()

        result = extract_news_with_report(
            source="auto",
            limit=1,
            rss_urls=["https://rss.example/feed.xml"],
            session=session,
        )

        self.assertEqual(result.provider, "gdelt")
        self.assertEqual(
            session.urls,
            ["https://api.gdeltproject.org/api/v2/doc/doc"],
        )

    @patch("data_pipeline.extract_news.time.sleep")
    @patch.dict(
        os.environ,
        {"NEWS_RETRY_ATTEMPTS": "2", "NEWS_RETRY_DELAY_SECONDS": "0"},
    )
    def test_gdelt_rate_limit_uses_retry_after(
        self,
        sleep_mock,
    ) -> None:
        result = extract_news_with_report(
            source="gdelt",
            limit=1,
            session=_RateLimitedGdeltSession(),
        )

        self.assertEqual(result.provider, "gdelt")
        self.assertEqual(result.attempts, 2)
        sleep_mock.assert_called_once_with(7.0)

    @patch.dict(
        os.environ,
        {"NEWS_RETRY_ATTEMPTS": "3", "NEWS_RETRY_DELAY_SECONDS": "0"},
    )
    def test_rss_retries_transient_failure(self) -> None:
        session = _RetrySession()

        result = extract_news_with_report(
            source="rss",
            limit=1,
            rss_urls=["https://example.com/feed.xml"],
            session=session,
        )

        self.assertEqual(result.provider, "rss")
        self.assertEqual(result.attempts, 2)
        self.assertEqual(len(result.articles), 1)
        self.assertTrue(result.articles[0]["content_is_snippet"])

    @patch.dict(
        os.environ,
        {"NEWS_RETRY_ATTEMPTS": "2", "NEWS_RETRY_DELAY_SECONDS": "0"},
    )
    def test_failed_rss_returns_no_real_articles(self) -> None:
        result = extract_news_with_report(
            source="rss",
            limit=1,
            rss_urls=["https://example.com/feed.xml"],
            session=_AlwaysFailSession(),
        )

        self.assertEqual(result.provider, "rss")
        self.assertEqual(result.articles, [])
        self.assertTrue(result.errors)

    @patch.dict(
        os.environ,
        {
            "NEWS_API_KEY": "",
            "NEWS_GDELT_ENABLED": "false",
            "NEWS_RSS_URLS": "",
        },
        clear=False,
    )
    def test_auto_never_falls_back_to_fabricated_articles(self) -> None:
        result = extract_news_with_report(
            source="auto",
            limit=3,
            session=_AlwaysFailSession(),
        )

        self.assertEqual(result.provider, "no_data")
        self.assertEqual(result.articles, [])
        self.assertTrue(
            any("NewsAPI skipped" in message for message in result.errors)
        )
        self.assertTrue(
            any("GDELT skipped" in message for message in result.errors)
        )
        self.assertTrue(
            any("NEWS_RSS_URLS" in message for message in result.errors)
        )


class NlpTest(unittest.TestCase):
    def test_analysis_has_stable_output_structure(self) -> None:
        article = clean_articles([_raw_article_fixture()])[0]
        analyzed = analyze_articles([article])[0]["analysis"]

        self.assertEqual(
            set(analyzed),
            {"summary", "sentiment", "sentiment_score", "topic", "keywords"},
        )
        self.assertTrue(analyzed["summary"])
        self.assertIn(analyzed["sentiment"], {"positive", "neutral", "negative"})
        self.assertGreaterEqual(analyzed["sentiment_score"], -1)
        self.assertLessEqual(analyzed["sentiment_score"], 1)
        self.assertIsInstance(analyzed["keywords"], list)
        self.assertTrue(analyzed["keywords"])

    def test_sentiment_supports_positive_and_negative_fallbacks(self) -> None:
        self.assertEqual(analyze_sentiment("strong growth and gain")[0], "positive")
        self.assertEqual(analyze_sentiment("crisis loss and risk")[0], "negative")

    def test_summary_provider_failure_uses_rule_based_fallback(self) -> None:
        article = clean_articles([_raw_article_fixture()])[0]

        def failing_summary(_title: str, _content: str) -> str:
            raise RuntimeError("LLM unavailable")

        analyzed = analyze_articles(
            [article],
            summary_function=failing_summary,
        )[0]["analysis"]

        self.assertIn("Regional markets gained", analyzed["summary"])
        self.assertIn(analyzed["sentiment"], {"positive", "neutral", "negative"})

    def test_llm_summary_failure_uses_rule_based_fallback(self) -> None:
        article = clean_articles([_raw_article_fixture()])[0]
        providers = AiProviders(
            summary=LlmSummaryProvider(_FailingChatProvider()),
            sentiment=RuleBasedSentimentProvider(),
            topic=RuleBasedTopicProvider(),
            embedding=HashingEmbeddingProvider(dimensions=16),
            chat=_FailingChatProvider(),
        )

        analyzed = analyze_articles([article], providers=providers)[0]["analysis"]

        self.assertIn("Regional markets gained", analyzed["summary"])
        self.assertIn(analyzed["sentiment"], {"positive", "neutral", "negative"})

    def test_embedding_generation_shape_when_enabled(self) -> None:
        article = clean_articles([_raw_article_fixture()])[0]
        analyzed = analyze_articles(
            [article],
            providers=_hash_ai_providers(dimensions=16),
        )[0]

        self.assertIn("embedding", analyzed)
        self.assertEqual(analyzed["embedding"]["dimensions"], 16)
        self.assertEqual(len(analyzed["embedding"]["vector"]), 16)
        self.assertEqual(analyzed["embedding"]["provider"], "hash")

    def test_semantic_search_falls_back_to_keyword(self) -> None:
        article = analyze_articles(clean_articles([_raw_article_fixture()]))[0]

        results = semantic_search_articles(
            "banking policy",
            [article],
            embedding_provider=_FailingEmbeddingProvider(),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], article["title"])

    def test_supabase_semantic_search_filters_by_embedding_provider(self) -> None:
        client = _RpcClient()

        results = semantic_search_supabase(
            client,
            "banking policy",
            embedding_provider=HashingEmbeddingProvider(dimensions=16),
            limit=3,
        )

        self.assertEqual(results, ["article-1"])
        self.assertEqual(client.rpc_name, "match_articles_by_embedding")
        self.assertEqual(client.rpc_params["match_count"], 3)
        self.assertEqual(client.rpc_params["query_provider"], "hash")
        self.assertTrue(client.rpc_params["query_embedding"].startswith("["))

    def test_rag_answer_uses_retrieved_article_context(self) -> None:
        article = analyze_articles(clean_articles([_raw_article_fixture()]))[0]

        result = answer_question(
            "What happened with markets?",
            [article],
            retriever=lambda _question, records, _limit: list(records),
        )

        self.assertFalse(result["used_llm"])
        self.assertEqual(result["retrieved_count"], 1)
        self.assertEqual(result["sources"][0]["title"], article["title"])
        self.assertIn(article["analysis"]["summary"], result["answer"])

    def test_evaluation_reports_valid_and_invalid_outputs(self) -> None:
        analyzed = analyze_articles(clean_articles([_raw_article_fixture()]))
        self.assertEqual(evaluate_articles(analyzed)["status"], "passed")

        analyzed[0]["analysis"]["keywords"] = []
        result = evaluate_articles(analyzed)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_checks"], 1)


class LoaderTest(unittest.TestCase):
    def test_live_loader_counts_inserts_and_duplicates(self) -> None:
        client = _FakeClient()
        article = _analyzed_article_fixture()

        first = SupabaseLoader(dry_run=False, client=client).load(article)
        second = SupabaseLoader(dry_run=False, client=client).load(article)

        self.assertEqual(first.inserted, 1)
        self.assertEqual(first.skipped_duplicates, 0)
        self.assertEqual(second.inserted, 0)
        self.assertEqual(second.skipped_duplicates, 1)
        self.assertEqual(len(client.rows["sources"]), 1)
        self.assertEqual(len(client.rows["categories"]), 1)
        self.assertEqual(len(client.rows["articles"]), 1)
        self.assertEqual(len(client.rows["article_analysis"]), 1)

    def test_loader_skips_invalid_record_without_stopping(self) -> None:
        client = _FakeClient()
        valid = _analyzed_article_fixture()[0]

        result = SupabaseLoader(dry_run=False, client=client).load(
            [{"title": "invalid"}, valid]
        )

        self.assertEqual(result.loaded, 1)
        self.assertEqual(result.failed, 1)
        self.assertTrue(result.errors)

    def test_loader_rejects_obvious_runtime_demo_content(self) -> None:
        client = _FakeClient()
        blocked = _analyzed_article_fixture()[0]
        blocked["title"] = "Sample article for placeholder content"

        result = SupabaseLoader(dry_run=False, client=client).load([blocked])

        self.assertEqual(result.loaded, 0)
        self.assertEqual(result.failed, 1)
        self.assertEqual(client.rows["articles"], [])

    def test_loader_stores_embedding_when_present(self) -> None:
        client = _FakeClient()
        article = analyze_articles(
            clean_articles([_raw_article_fixture()]),
            providers=_hash_ai_providers(dimensions=384),
        )

        result = SupabaseLoader(dry_run=False, client=client).load(article)

        self.assertEqual(result.loaded, 1)
        self.assertEqual(result.embeddings_upserted, 1)
        self.assertEqual(len(client.rows["article_embeddings"]), 1)

    def test_pipeline_run_observability_is_backend_only_loader_write(self) -> None:
        client = _FakeClient()
        loader = SupabaseLoader(dry_run=False, client=client)

        loader.record_pipeline_run(
            {
                "started_at": "2026-06-14T00:00:00+00:00",
                "completed_at": "2026-06-14T00:00:01+00:00",
                "source": "rss",
                "extracted": 0,
                "cleaned": 0,
                "inserted": 0,
                "skipped_duplicates": 0,
                "failed": 0,
                "status": "no_data",
                "error_message": "No real news articles were extracted.",
            }
        )

        self.assertEqual(len(client.rows["pipeline_runs"]), 1)


class PipelineNoDataTest(unittest.TestCase):
    @patch(
        "data_pipeline.main_pipeline.extract_news_with_report",
        return_value=ExtractionResult(
            articles=[],
            provider="no_data",
            attempts=3,
            errors=("GDELT and RSS returned no articles.",),
        ),
    )
    def test_zero_real_articles_skips_nlp_load_and_logs_no_data(
        self,
        _extract_mock,
    ) -> None:
        loader = _RecordingLoader()

        result = run_pipeline(
            source="auto",
            limit=10,
            dry_run=False,
            loader=loader,
        )

        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["analyzed_count"], 0)
        self.assertEqual(result["load"]["loaded"], 0)
        self.assertEqual(loader.load_calls, 0)
        self.assertEqual(loader.run_payloads[0]["status"], "no_data")

    @patch(
        "data_pipeline.main_pipeline.extract_news_with_report",
        return_value=ExtractionResult(
            articles=[],
            provider="no_data",
            attempts=0,
            errors=("No configured real source returned data.",),
        ),
    )
    def test_no_data_status_survives_observability_failure(
        self,
        _extract_mock,
    ) -> None:
        result = run_pipeline(
            source="auto",
            dry_run=False,
            loader=_FailingObservabilityLoader(),
        )

        self.assertEqual(result["status"], "no_data")
        self.assertFalse(result["observability_recorded"])

    def test_seed_file_contains_reference_data_only(self) -> None:
        seed_path = (
            Path(__file__).resolve().parents[2] / "database" / "seed_data.sql"
        )
        sql = seed_path.read_text(encoding="utf-8")

        self.assertIsNone(
            re.search(r"insert\s+into\s+public\.articles", sql, re.IGNORECASE)
        )
        self.assertIsNone(
            re.search(
                r"insert\s+into\s+public\.article_analysis",
                sql,
                re.IGNORECASE,
            )
        )
        self.assertNotIn("Mandiri Intelligence Demo", sql)

    def test_semantic_rpc_qualifies_pgvector_operator_schema(self) -> None:
        schema_path = (
            Path(__file__).resolve().parents[2] / "database" / "schema.sql"
        )
        sql = schema_path.read_text(encoding="utf-8")

        self.assertIn(
            "drop function if exists "
            "public.match_articles_by_embedding(text, integer);",
            sql,
        )
        self.assertIn(
            "drop function if exists "
            "public.match_articles_by_embedding(text, integer, text);",
            sql,
        )
        self.assertIn("from pg_catalog.pg_type", sql)
        self.assertIn("from pg_catalog.pg_operator op", sql)
        self.assertIn("op.oprleft = vector_type_oid", sql)
        self.assertIn("op.oprright = vector_type_oid", sql)
        self.assertIn("operator(%s.<=>)", sql.lower())
        self.assertIn("e.embedding_provider = $3", sql)


def _raw_article_fixture() -> dict:
    return {
        "title": "Regional markets gain after policy update",
        "content": (
            "Regional markets gained while investors reviewed a new banking "
            "policy and improving trade expectations."
        ),
        "url": "https://newsroom.id/regional-markets",
        "image_url": None,
        "source_name": "Newsroom Indonesia",
        "source_url": "https://newsroom.id",
        "source_country": "Indonesia",
        "category": "Finance",
        "published_at": "2026-06-14T10:00:00Z",
        "content_is_snippet": True,
    }


def _analyzed_article_fixture() -> list[dict]:
    return analyze_articles(clean_articles([_raw_article_fixture()]))


def _hash_ai_providers(dimensions: int) -> AiProviders:
    return AiProviders(
        summary=RuleBasedSummaryProvider(),
        sentiment=RuleBasedSentimentProvider(),
        topic=RuleBasedTopicProvider(),
        embedding=HashingEmbeddingProvider(dimensions=dimensions),
    )


class _FailingEmbeddingProvider:
    name = "failing"

    def embed(self, _text: str):
        raise RuntimeError("embedding unavailable")


class _FailingChatProvider:
    name = "failing-chat"

    def complete(self, _messages, *, temperature=0.2):
        raise RuntimeError("LLM unavailable")


class _RpcClient:
    def __init__(self) -> None:
        self.rpc_name = None
        self.rpc_params = None

    def rpc(self, name, params):
        self.rpc_name = name
        self.rpc_params = dict(params)
        return _RpcQuery()


class _RpcQuery:
    def execute(self):
        return _Response([{"article_id": "article-1", "similarity": 0.9}])


class _Response:
    def __init__(self, data, *, status_code=200, content=b"", headers=None):
        self.data = data
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.data


class _GdeltSession:
    def __init__(self) -> None:
        self.urls = []
        self.params = {}

    def get(self, url, **kwargs):
        self.urls.append(url)
        self.params = kwargs.get("params", {})
        return _Response(
            {
                "articles": [
                    {
                        "url": "https://example.com/market?utm_source=gdelt",
                        "title": "Indonesia market gains",
                        "seendate": "20260614T101500Z",
                        "socialimage": "https://example.com/market.jpg",
                        "domain": "example.com",
                        "sourcecountry": "Indonesia",
                    },
                    {
                        "url": "https://other.example/market",
                        "title": "Indonesia market gains",
                        "seendate": "20260614T100000Z",
                        "domain": "other.example",
                    },
                ]
            }
        )


class _RateLimitedGdeltSession(_GdeltSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def get(self, url, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return _Response(
                {},
                status_code=429,
                headers={"Retry-After": "7"},
            )
        return super().get(url, **kwargs)


class _NewsApiSession:
    def __init__(self) -> None:
        self.urls = []

    def get(self, url, **_kwargs):
        self.urls.append(url)
        return _Response(
            {
                "articles": [
                    {
                        "title": "NewsAPI priority article",
                        "description": "NewsAPI remains first when configured.",
                        "url": "https://news.example/priority",
                        "source": {"name": "News Example"},
                        "publishedAt": "2026-06-14T10:00:00Z",
                    }
                ]
            }
        )


class _RetrySession:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, _url, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            return _Response([], status_code=503)
        return _Response(
            [],
            content=(
                b"<rss><channel><title>Example Feed</title><item>"
                b"<title>Market gains</title>"
                b"<link>https://example.com/market</link>"
                b"<description>Markets improved today.</description>"
                b"<pubDate>Sun, 14 Jun 2026 10:00:00 GMT</pubDate>"
                b"</item></channel></rss>"
            ),
        )


class _AlwaysFailSession:
    def get(self, _url, **_kwargs):
        return _Response([], status_code=503)


class _RecordingLoader:
    def __init__(self) -> None:
        self.load_calls = 0
        self.run_payloads = []

    def load(self, _articles):
        self.load_calls += 1
        raise AssertionError("No-data runs must not call article loading.")

    def record_pipeline_run(self, payload):
        self.run_payloads.append(dict(payload))


class _FailingObservabilityLoader(_RecordingLoader):
    def record_pipeline_run(self, payload):
        raise RuntimeError("pipeline_runs is unavailable")


class _FakeClient:
    def __init__(self) -> None:
        self.rows = {
            "sources": [],
            "categories": [],
            "articles": [],
            "article_analysis": [],
            "article_embeddings": [],
            "pipeline_runs": [],
        }

    def table(self, name: str):
        return _FakeQuery(self, name)


class _FakeQuery:
    def __init__(self, client: _FakeClient, table: str) -> None:
        self.client = client
        self.table_name = table
        self.payload = None
        self.conflict = None
        self.filters = []
        self.is_select = False
        self.is_insert = False

    def upsert(self, payload, on_conflict: str):
        self.payload = dict(payload)
        self.conflict = on_conflict
        return self

    def insert(self, payload):
        self.payload = dict(payload)
        self.is_insert = True
        return self

    def select(self, _columns: str):
        self.is_select = True
        return self

    def eq(self, column: str, value):
        self.filters.append((column, value))
        return self

    def limit(self, _value: int):
        return self

    def execute(self):
        rows = self.client.rows[self.table_name]
        if self.is_select:
            matches = [
                row
                for row in rows
                if all(row.get(column) == value for column, value in self.filters)
            ]
            return _Response(matches)
        if self.is_insert:
            inserted = {
                "id": f"{self.table_name}-{len(rows) + 1}",
                **self.payload,
            }
            rows.append(inserted)
            return _Response([dict(inserted)])

        conflict_columns = [item.strip() for item in self.conflict.split(",")]
        existing = next(
            (
                row
                for row in rows
                if all(
                    row.get(column) == self.payload.get(column)
                    for column in conflict_columns
                )
            ),
            None,
        )
        if existing is None:
            existing = {
                "id": f"{self.table_name}-{len(rows) + 1}",
                **self.payload,
            }
            rows.append(existing)
        else:
            existing.update(self.payload)
        return _Response([dict(existing)])


if __name__ == "__main__":
    unittest.main()
