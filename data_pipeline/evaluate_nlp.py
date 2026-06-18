"""Evaluate the stable structural contract of MVP NLP outputs."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Iterable

try:
    from .clean_news import clean_articles
    from .extract_news import extract_news
    from .nlp_analysis import analyze_articles
except ImportError:
    from clean_news import clean_articles
    from extract_news import extract_news
    from nlp_analysis import analyze_articles


def evaluate_articles(
    articles: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    records = list(articles)
    failures: list[str] = []
    for index, article in enumerate(records):
        analysis = article.get("analysis")
        if not isinstance(analysis, dict):
            failures.append(f"article[{index}] analysis is missing")
            continue
        if not str(analysis.get("summary") or "").strip():
            failures.append(f"article[{index}] summary is empty")
        if analysis.get("sentiment") not in {
            "positive",
            "neutral",
            "negative",
        }:
            failures.append(f"article[{index}] sentiment is invalid")
        if not str(analysis.get("topic") or "").strip():
            failures.append(f"article[{index}] topic is empty")
        keywords = analysis.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            failures.append(f"article[{index}] keywords are empty")

    return {
        "status": "passed" if records and not failures else "failed",
        "evaluated": len(records),
        "failed_checks": len(failures),
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate MVP NLP outputs.")
    parser.add_argument(
        "--source",
        choices=("rss", "gdelt", "newsapi", "auto"),
        default="auto",
    )
    parser.add_argument("--limit", type=int, default=3)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    raw = extract_news(limit=arguments.limit, source=arguments.source)
    result = evaluate_articles(analyze_articles(clean_articles(raw)))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result["status"] != "passed":
        sys.exit(1)
