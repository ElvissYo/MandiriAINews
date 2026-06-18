"""Command-line entry point for the stabilized ETL and NLP pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .clean_news import clean_articles
    from .extract_news import extract_news_with_report
    from .load_to_supabase import LoadResult, SupabaseLoader
    from .nlp_analysis import analyze_articles
except ImportError:
    from clean_news import clean_articles
    from extract_news import extract_news_with_report
    from load_to_supabase import LoadResult, SupabaseLoader
    from nlp_analysis import analyze_articles


def run_pipeline(
    *,
    limit: int = 10,
    dry_run: bool = True,
    source: str = "auto",
    rss_urls: list[str] | None = None,
    loader: SupabaseLoader | None = None,
) -> dict[str, object]:
    started_at = datetime.now(timezone.utc)
    pipeline_loader = loader or SupabaseLoader(dry_run=dry_run)
    extraction_errors: list[str] = []
    extraction = None
    clean_records: list[dict[str, Any]] = []
    analyzed_records: list[dict[str, Any]] = []

    try:
        extraction = extract_news_with_report(
            limit=limit,
            source=source,
            rss_urls=rss_urls,
        )
        extraction_errors.extend(extraction.errors)
        if not extraction.articles:
            status = "no_data"
            error_messages = [
                *extraction_errors,
                "No real news articles were extracted; NLP and Supabase "
                "article loading were skipped.",
            ]
            load_result = _empty_load_result(dry_run=dry_run)
        else:
            clean_records = clean_articles(extraction.articles)
            if not clean_records:
                status = "no_data"
                error_messages = [
                    *extraction_errors,
                    "Real providers returned records, but none passed cleaning; "
                    "NLP and Supabase article loading were skipped.",
                ]
                load_result = _empty_load_result(dry_run=dry_run)
            else:
                analyzed_records = analyze_articles(clean_records)
                load_result = pipeline_loader.load(analyzed_records)
                status = _status_for(
                    loaded=load_result.loaded,
                    failed=load_result.failed,
                    warnings=len(extraction_errors),
                )
                error_messages = [*extraction_errors, *load_result.errors]
    except Exception as error:
        failed_count = max(len(analyzed_records), 1)
        load_result = LoadResult(
            received=len(analyzed_records),
            loaded=0,
            inserted=0,
            skipped_duplicates=0,
            failed=failed_count,
            sources_upserted=0,
            categories_upserted=0,
            analyses_upserted=0,
            dry_run=dry_run,
            errors=(_safe_error(error),),
        )
        status = "failed"
        error_messages = list(load_result.errors)

    completed_at = datetime.now(timezone.utc)
    raw_count = len(extraction.articles) if extraction else 0
    clean_count = len(clean_records)
    duplicate_count = max(raw_count - clean_count, 0)
    result: dict[str, Any] = {
        "status": status,
        "requested_source": source,
        "resolved_source": extraction.provider if extraction else "unavailable",
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round(
            (completed_at - started_at).total_seconds(),
            3,
        ),
        "raw_count": raw_count,
        "clean_count": clean_count,
        "cleaning_duplicates_or_invalid": duplicate_count,
        "analyzed_count": len(analyzed_records),
        "extraction_attempts": extraction.attempts if extraction else 0,
        "load": asdict(load_result),
        "errors": error_messages[:20],
        "preview": analyzed_records[:1],
    }

    if not dry_run:
        run_payload = {
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "source": result["resolved_source"],
            "extracted": raw_count,
            "cleaned": clean_count,
            "inserted": load_result.inserted,
            "skipped_duplicates": (
                duplicate_count + load_result.skipped_duplicates
            ),
            "failed": load_result.failed,
            "status": status,
            "error_message": _joined_errors(error_messages),
        }
        try:
            pipeline_loader.record_pipeline_run(run_payload)
            result["observability_recorded"] = True
        except Exception as error:
            result["observability_recorded"] = False
            result["observability_error"] = _safe_error(error)
            if result["status"] == "success":
                result["status"] = "partial"

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Mandiri News Intelligence Phase 5 pipeline."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of source articles to extract.",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "newsapi", "gdelt", "rss"),
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


def _status_for(*, loaded: int, failed: int, warnings: int) -> str:
    if loaded == 0 and failed > 0:
        return "failed"
    if failed > 0 or warnings > 0:
        return "partial"
    return "success"


def _empty_load_result(*, dry_run: bool) -> LoadResult:
    return LoadResult(
        received=0,
        loaded=0,
        inserted=0,
        skipped_duplicates=0,
        failed=0,
        sources_upserted=0,
        categories_upserted=0,
        analyses_upserted=0,
        dry_run=dry_run,
    )


def _safe_error(error: BaseException) -> str:
    message = " ".join(str(error).split())
    for variable in (
        "SUPABASE_SERVICE_ROLE_KEY",
        "NEWS_API_KEY",
        "LLM_SUMMARY_API_KEY",
    ):
        secret = os.getenv(variable, "").strip()
        if secret:
            message = message.replace(secret, "[redacted]")
    return message[:500]


def _joined_errors(errors: list[str]) -> str | None:
    if not errors:
        return None
    return " | ".join(errors)[:2000]


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
    if result["status"] in {"partial", "failed", "no_data"}:
        sys.exit(1)
