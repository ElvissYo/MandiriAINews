import unittest

from data_pipeline.clean_news import clean_articles
from data_pipeline.extract_news import extract_news
from data_pipeline.nlp_analysis import analyze_articles


class PipelineSkeletonTest(unittest.TestCase):
    def test_dummy_flow_produces_analysis(self) -> None:
        raw = extract_news()
        cleaned = clean_articles(raw)
        analyzed = analyze_articles(cleaned)

        self.assertGreater(len(analyzed), 0)
        self.assertIn("analysis", analyzed[0])
        self.assertIn(
            analyzed[0]["analysis"]["sentiment"],
            {"positive", "neutral", "negative"},
        )


if __name__ == "__main__":
    unittest.main()
