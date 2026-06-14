"""Command-line entry point for the Phase 4 ETL and NLP pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

try:
    from .clean_news import clean_articles
    from .extract_news import extract_news
    from .load_to_supabase import SupabaseLoader
    from .nlp_analysis import analyze_articles
except ImportError:
    from clean_news import clean_articles
    from extract_news import extract_news
    from load_to_supabase import SupabaseLoader
    from nlp_analysis import analyze_articles


def run_pipeline(
    *,
    limit: int = 10,
    dry_run: bool = True,
    source: str = "auto",
    rss_urls: list[str] | None = None,
) -> dict[str, object]:
    raw_articles = extract_news(
        limit=limit,
        source=source,
        rss_urls=rss_urls,
    )
    clean_records = clean_articles(raw_articles)
    analyzed_records = analyze_articles(clean_records)
    load_result = SupabaseLoader(dry_run=dry_run).load(analyzed_records)

    return {
        "source_mode": source,
        "raw_count": len(raw_articles),
        "clean_count": len(clean_records),
        "analyzed_count": len(analyzed_records),
        "load": asdict(load_result),
        "preview": analyzed_records[:1],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Mandiri News Intelligence Phase 4 pipeline."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of source articles to extract.",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "newsapi", "rss", "dummy"),
        default="auto",
        help="Extraction source. Auto falls back safely when providers fail.",
    )
    parser.add_argument(
        "--rss-url",
        action="append",
        dest="rss_urls",
        help="RSS URL to use. Repeat this flag for multiple feeds.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Write to Supabase. The default is a dry run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optionally write the JSON result to this path.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    result = run_pipeline(
        limit=arguments.limit,
        dry_run=not arguments.live,
        source=arguments.source,
        rss_urls=arguments.rss_urls,
    )
    output = json.dumps(result, indent=2, ensure_ascii=True)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(output + "\n", encoding="utf-8")
    print(output)
