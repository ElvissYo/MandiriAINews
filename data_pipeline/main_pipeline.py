"""Command-line entry point for the Phase 1 ETL skeleton."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

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


def run_pipeline(*, limit: int = 10, dry_run: bool = True) -> dict[str, object]:
    raw_articles = extract_news(limit=limit)
    clean_records = clean_articles(raw_articles)
    analyzed_records = analyze_articles(clean_records)
    load_result = SupabaseLoader(dry_run=dry_run).load(analyzed_records)

    return {
        "raw_count": len(raw_articles),
        "clean_count": len(clean_records),
        "load": asdict(load_result),
        "preview": analyzed_records[:1],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Mandiri News Intelligence ETL skeleton."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of source articles to extract.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Write to Supabase. The default is a safe dry run.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    result = run_pipeline(limit=arguments.limit, dry_run=not arguments.live)
    print(json.dumps(result, indent=2, ensure_ascii=True))
