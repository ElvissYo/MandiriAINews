import unittest

from data_pipeline.clean_news import clean_articles
from data_pipeline.extract_news import extract_news
from data_pipeline.load_to_supabase import SupabaseLoader
from data_pipeline.nlp_analysis import analyze_articles, analyze_sentiment


class CleaningTest(unittest.TestCase):
    def test_cleaning_removes_invalid_html_and_duplicates(self) -> None:
        raw = [
            {
                "title": "  <b>Market Update</b> ",
                "content": "<p>Markets gain.</p><script>ignore()</script>",
                "url": "HTTPS://Example.com/story/?utm_source=test#section",
                "source_name": " Example Daily - Google News ",
                "published_at": "2026-06-14T08:30:00+07:00",
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
        self.assertEqual(cleaned[0]["published_at"], "2026-06-14T01:30:00+00:00")


class NlpTest(unittest.TestCase):
    def test_analysis_has_stable_output_structure(self) -> None:
        article = clean_articles(extract_news(source="dummy", limit=1))[0]
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

    def test_sentiment_supports_positive_and_negative_fallbacks(self) -> None:
        self.assertEqual(analyze_sentiment("strong growth and gain")[0], "positive")
        self.assertEqual(analyze_sentiment("crisis loss and risk")[0], "negative")


class LoaderTest(unittest.TestCase):
    def test_live_loader_upserts_each_table_idempotently(self) -> None:
        client = _FakeClient()
        article = analyze_articles(
            clean_articles(extract_news(source="dummy", limit=1))
        )

        first = SupabaseLoader(dry_run=False, client=client).load(article)
        second = SupabaseLoader(dry_run=False, client=client).load(article)

        self.assertEqual(first.loaded, 1)
        self.assertEqual(second.loaded, 1)
        self.assertEqual(len(client.rows["sources"]), 1)
        self.assertEqual(len(client.rows["categories"]), 1)
        self.assertEqual(len(client.rows["articles"]), 1)
        self.assertEqual(len(client.rows["article_analysis"]), 1)


class _Response:
    def __init__(self, data):
        self.data = data


class _FakeClient:
    def __init__(self) -> None:
        self.rows = {
            "sources": [],
            "categories": [],
            "articles": [],
            "article_analysis": [],
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

    def upsert(self, payload, on_conflict: str):
        self.payload = dict(payload)
        self.conflict = on_conflict
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
