"""Extract news from real NewsAPI, GDELT, or RSS sources."""

from __future__ import annotations

import os
import json
import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Iterable
from urllib.parse import urlsplit
from xml.etree import ElementTree

try:
    from .content_extractor import (
        ContentExtractionResult,
        extract_public_article_content,
        rss_content_result,
    )
except ImportError:
    from content_extractor import (
        ContentExtractionResult,
        extract_public_article_content,
        rss_content_result,
    )

DEFAULT_NEWS_API_URL = "https://newsapi.org/v2/everything"
DEFAULT_GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


class RequestFailure(RuntimeError):
    def __init__(self, message: str, *, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


@dataclass(frozen=True)
class ExtractionResult:
    articles: list[dict[str, Any]]
    provider: str
    attempts: int
    errors: tuple[str, ...]
    diagnostics: tuple[dict[str, Any], ...] = ()


def extract_news(
    limit: int = 10,
    *,
    source: str | None = None,
    rss_urls: Iterable[str] | None = None,
    session: Any | None = None,
) -> list[dict[str, Any]]:
    """Return raw article dictionaries from the configured source.

    `NEWS_SOURCE` accepts `auto`, `newsapi`, `gdelt`, or `rss`. Auto mode tries
    configured real providers in that order and never fabricates articles.
    """
    return extract_news_with_report(
        limit=limit,
        source=source,
        rss_urls=rss_urls,
        session=session,
    ).articles


def extract_news_with_report(
    limit: int = 10,
    *,
    source: str | None = None,
    rss_urls: Iterable[str] | None = None,
    session: Any | None = None,
) -> ExtractionResult:
    """Extract articles and return safe provider diagnostics."""
    _load_environment()
    requested_limit = max(limit, 0)
    if requested_limit == 0:
        return ExtractionResult([], "none", 0, ())

    provider = (source or os.getenv("NEWS_SOURCE", "auto")).strip().lower()
    if provider not in {"auto", "newsapi", "gdelt", "rss"}:
        raise ValueError("NEWS_SOURCE must be auto, newsapi, gdelt, or rss.")

    http = session or _requests_session()
    errors: list[str] = []
    skipped: list[str] = []
    diagnostics: list[dict[str, Any]] = []
    attempts = 0
    if provider in {"auto", "newsapi"}:
        api_key = os.getenv("NEWS_API_KEY", "").strip()
        if api_key:
            try:
                records, used_attempts, source_diagnostics = _extract_news_api(
                    http,
                    api_key,
                    requested_limit,
                    enrich_content=session is None,
                )
                attempts += used_attempts
                diagnostics.extend(source_diagnostics)
                if records:
                    return ExtractionResult(
                        records[:requested_limit],
                        "newsapi",
                        attempts,
                        tuple(errors),
                        tuple(diagnostics),
                    )
                errors.append("NewsAPI returned no articles.")
            except Exception as error:
                attempts += int(getattr(error, "attempts", 0))
                message = _safe_error(error, secrets=(api_key,))
                errors.append(message)
                diagnostics.append(
                    _source_diagnostic(
                        "newsapi",
                        status="failed",
                        failed=1,
                        error_message=message,
                    )
                )
        elif provider == "newsapi":
            errors.append(
                "NewsAPI cannot run because NEWS_API_KEY is not configured."
            )
        else:
            skipped.append(
                "NewsAPI skipped because NEWS_API_KEY is not configured."
            )

    if provider == "gdelt" or (provider == "auto" and _gdelt_enabled()):
        try:
            records, used_attempts, source_diagnostics = _extract_gdelt(
                http,
                requested_limit,
                enrich_content=session is None,
            )
            attempts += used_attempts
            diagnostics.extend(source_diagnostics)
            if records:
                return ExtractionResult(
                    records[:requested_limit],
                    "gdelt",
                    attempts,
                    tuple(errors),
                    tuple(diagnostics),
                )
            errors.append("GDELT returned no articles.")
        except Exception as error:
            attempts += int(getattr(error, "attempts", 0))
            message = _safe_error(error)
            errors.append(message)
            diagnostics.append(
                _source_diagnostic(
                    "gdelt",
                    status="failed",
                    failed=1,
                    error_message=message,
                )
            )
    elif provider == "auto":
        skipped.append(
            "GDELT skipped because NEWS_GDELT_ENABLED is false."
        )

    if provider in {"auto", "rss"}:
        configured_urls = (
            list(rss_urls) if rss_urls is not None else list(_rss_urls_from_env())
        )
        if configured_urls:
            try:
                records, used_attempts, rss_errors, source_diagnostics = _extract_rss(
                    http,
                    configured_urls,
                    requested_limit,
                    enrich_content=session is None,
                )
                attempts += used_attempts
                errors.extend(rss_errors)
                diagnostics.extend(source_diagnostics)
                if records:
                    return ExtractionResult(
                        records[:requested_limit],
                        "rss",
                        attempts,
                        tuple(errors),
                        tuple(diagnostics),
                    )
                errors.append("Configured RSS feeds returned no articles.")
            except Exception as error:
                message = _safe_error(error)
                errors.append(message)
                diagnostics.append(
                    _source_diagnostic(
                        "rss",
                        status="failed",
                        failed=1,
                        error_message=message,
                    )
                )
        else:
            errors.append(
                "RSS cannot run because NEWS_RSS_URLS is not configured."
            )

    return ExtractionResult(
        [],
        provider if provider != "auto" else "no_data",
        attempts,
        tuple(
            [*skipped, *errors]
            or ["No real news providers returned articles."]
        ),
        tuple(diagnostics),
    )


def _extract_news_api(
    session: Any,
    api_key: str,
    limit: int,
    *,
    enrich_content: bool = True,
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    endpoint = os.getenv("NEWS_API_URL", DEFAULT_NEWS_API_URL).strip()
    query = os.getenv("NEWS_API_QUERY", "Indonesia OR ASEAN").strip()
    language = os.getenv("NEWS_API_LANGUAGE", "en").strip()
    response, attempts = _request_with_retry(
        session,
        endpoint,
        params={
            "q": query,
            "language": language,
            "sortBy": "publishedAt",
            "pageSize": min(limit, 100),
            "apiKey": api_key,
        },
        timeout=_request_timeout(),
    )
    payload = response.json()
    records: list[dict[str, Any]] = []
    for item in payload.get("articles", []):
        source = item.get("source") or {}
        url = str(item.get("url") or "")
        content = item.get("content") or item.get("description") or ""
        records.append(
            {
                "title": item.get("title"),
                "content": content,
                "url": url,
                "image_url": item.get("urlToImage"),
                "source_name": source.get("name") or _host_name(url),
                "source_url": _origin(url),
                "source_country": None,
                "category": "World News",
                "published_at": item.get("publishedAt"),
                "content_is_snippet": True,
                "extraction_method": "newsapi_snippet",
                "extraction_status": "snippet",
                "canonical_url": url,
            }
        )
    records = _dedupe_raw_records(
        _enrich_article_content(records, session=session, enabled=enrich_content)
    )
    return records, attempts, [
        _diagnostic_for_records(
            "newsapi",
            records,
            status="success" if records else "no_data",
            extracted=len(records),
        )
    ]


def _extract_gdelt(
    session: Any,
    limit: int,
    *,
    enrich_content: bool = True,
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    endpoint = os.getenv("NEWS_GDELT_API_URL", DEFAULT_GDELT_API_URL).strip()
    query = _gdelt_query(
        os.getenv("NEWS_GDELT_QUERY", "Indonesia OR ASEAN")
    )
    timespan = os.getenv("NEWS_GDELT_TIMESPAN", "1d").strip() or "1d"
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": min(limit, _gdelt_max_records()),
        "format": "json",
        "timespan": timespan,
        "sort": "datedesc",
    }
    cache_key = _cache_key(endpoint, params)
    cached_payload = _gdelt_cache_get(cache_key)
    attempts = 0
    if cached_payload is None:
        cooldown = _gdelt_cooldown_seconds()
        if cooldown > 0:
            time.sleep(cooldown)
        response, attempts = _request_with_retry(
            session,
            endpoint,
            params=params,
            headers={"User-Agent": "MandiriNewsPipeline/1.0"},
            timeout=_request_timeout(),
            attempts=_gdelt_max_retries(),
        )
        payload = response.json()
        _gdelt_cache_set(cache_key, payload)
    else:
        payload = cached_payload
    articles = payload.get("articles", []) if isinstance(payload, dict) else []
    records: list[dict[str, Any]] = []
    for item in articles:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("url_mobile") or "")
        title = item.get("title")
        content = (
            item.get("snippet")
            or item.get("description")
            or item.get("content")
            or title
        )
        source_name = str(item.get("domain") or "").strip()
        records.append(
            {
                "title": title,
                "content": content,
                "url": url,
                "image_url": item.get("socialimage"),
                "source_name": source_name or _host_name(url),
                "source_url": _origin(url),
                "source_country": item.get("sourcecountry"),
                "category": item.get("topic") or "World News",
                "published_at": _gdelt_timestamp(item.get("seendate")),
                "content_is_snippet": True,
                "extraction_method": "gdelt_snippet",
                "extraction_status": "snippet",
                "canonical_url": url,
            }
        )
    records = _dedupe_raw_records(
        _enrich_article_content(records, session=session, enabled=enrich_content)
    )
    return records, attempts, [
        _diagnostic_for_records(
            "gdelt",
            records,
            status="success" if records else "no_data",
            extracted=len(records),
            cache_hit=cached_payload is not None,
        )
    ]


def _extract_rss(
    session: Any,
    rss_urls: Iterable[str],
    limit: int,
    *,
    enrich_content: bool = True,
) -> tuple[list[dict[str, Any]], int, list[str], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    attempts = 0
    errors: list[str] = []
    diagnostics: list[dict[str, Any]] = []
    for feed_url in rss_urls:
        feed_records: list[dict[str, Any]] = []
        try:
            response, used_attempts = _request_with_retry(
                session,
                feed_url,
                headers={"User-Agent": "MandiriNewsPipeline/1.0"},
                timeout=_request_timeout(),
            )
            attempts += used_attempts
            root = ElementTree.fromstring(response.content)
        except Exception as error:
            attempts += int(getattr(error, "attempts", 0))
            message = _safe_error(error)
            errors.append(message)
            diagnostics.append(
                _source_diagnostic(
                    "rss",
                    source_url=feed_url,
                    status="failed",
                    failed=1,
                    error_message=message,
                )
            )
            continue
        channel_title = _element_text(root.find("./channel/title"))
        for item in root.findall("./channel/item"):
            article_url = _element_text(item.find("link"))
            source_element = item.find("source")
            source_name = _element_text(source_element) or channel_title
            source_url = (
                source_element.attrib.get("url")
                if source_element is not None
                else _origin(article_url)
            )
            full_content = _element_text(item.find("content:encoded", _namespaces()))
            description = _element_text(item.find("description"))
            content_result = rss_content_result(
                content=full_content or description,
                description=description,
                canonical_url=article_url,
            )
            feed_records.append(
                {
                    "title": _element_text(item.find("title")),
                    "content": content_result.content,
                    "url": article_url,
                    "image_url": _rss_image_url(item),
                    "source_name": source_name or _host_name(article_url),
                    "source_url": source_url,
                    "source_country": None,
                    "category": _element_text(item.find("category"))
                    or "World News",
                    "published_at": _rss_timestamp(
                        _element_text(item.find("pubDate"))
                    ),
                    "content_is_snippet": content_result.content_is_snippet,
                    "extraction_method": content_result.extraction_method,
                    "extraction_status": content_result.extraction_status,
                    "canonical_url": content_result.canonical_url or article_url,
                }
            )
            if len(records) + len(feed_records) >= limit:
                break
        feed_records = _enrich_article_content(
            feed_records,
            session=session,
            enabled=enrich_content,
        )
        records.extend(feed_records)
        diagnostics.append(
            _diagnostic_for_records(
                "rss",
                feed_records,
                status="success" if feed_records else "no_data",
                source_url=feed_url,
                extracted=len(feed_records),
            )
        )
        records = _dedupe_raw_records(records)
        if len(records) >= limit:
            return records[:limit], attempts, errors, diagnostics
    return _dedupe_raw_records(records), attempts, errors, diagnostics


def _request_with_retry(
    session: Any,
    url: str,
    *,
    attempts: int | None = None,
    **kwargs: Any,
) -> tuple[Any, int]:
    attempts = attempts or _retry_attempts()
    delay = _retry_delay()
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = session.get(url, **kwargs)
            status_code = int(getattr(response, "status_code", 200))
            if status_code in _RETRYABLE_STATUS_CODES and attempt < attempts:
                time.sleep(
                    _retry_wait_seconds(
                        response=response,
                        delay=delay,
                        attempt=attempt,
                    )
                )
                continue
            response.raise_for_status()
            return response, attempt
        except Exception as error:
            last_error = error
            if attempt >= attempts:
                break
            time.sleep(delay * (2 ** (attempt - 1)))
    raise RequestFailure(
        f"Request failed after {attempts} attempts: {_safe_error(last_error)}",
        attempts=attempts,
    )


def _retry_wait_seconds(
    *,
    response: Any,
    delay: float,
    attempt: int,
) -> float:
    status_code = int(getattr(response, "status_code", 0))
    exponential_delay = delay * (2 ** (attempt - 1))
    headers = getattr(response, "headers", {}) or {}
    try:
        retry_after = max(float(headers.get("Retry-After", 0)), 0)
    except (TypeError, ValueError):
        retry_after = 0
    if status_code == 429:
        return max(exponential_delay, retry_after, 5.0)
    return max(exponential_delay, retry_after)


def _enrich_article_content(
    records: list[dict[str, Any]],
    *,
    session: Any,
    enabled: bool,
) -> list[dict[str, Any]]:
    if not enabled or not _content_extraction_enabled():
        return [_ensure_extraction_fields(record) for record in records]

    enriched: list[dict[str, Any]] = []
    max_articles = _full_content_max_articles()
    delay = _content_extraction_delay_seconds()
    for index, record in enumerate(records):
        if index >= max_articles:
            enriched.append(_ensure_extraction_fields(record))
            continue
        url = str(record.get("canonical_url") or record.get("url") or "")
        fallback = str(record.get("content") or "")
        result = extract_public_article_content(
            url,
            fallback,
            session=session,
            timeout=_content_timeout(),
            attempts=_content_attempts(),
            delay_seconds=delay,
        )
        updated = {
            **record,
            "content": result.content or fallback,
            "content_is_snippet": result.content_is_snippet,
            "extraction_method": result.extraction_method,
            "extraction_status": result.extraction_status,
            "canonical_url": result.canonical_url or record.get("canonical_url") or url,
        }
        if result.error:
            updated["extraction_error"] = result.error
        enriched.append(updated)
        if delay > 0 and index < len(records) - 1:
            time.sleep(delay)
    return [_ensure_extraction_fields(record) for record in enriched]


def _ensure_extraction_fields(record: dict[str, Any]) -> dict[str, Any]:
    content_is_snippet = bool(record.get("content_is_snippet", True))
    return {
        **record,
        "extraction_method": str(
            record.get("extraction_method")
            or ("source_snippet" if content_is_snippet else "source_content")
        ),
        "extraction_status": str(
            record.get("extraction_status")
            or ("snippet" if content_is_snippet else "full_content")
        ),
        "canonical_url": record.get("canonical_url") or record.get("url"),
    }


def _dedupe_raw_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for record in records:
        canonical_key = _url_key(str(record.get("canonical_url") or ""))
        url_key = _url_key(str(record.get("url") or ""))
        title_key = _title_key(str(record.get("title") or ""))
        keys = {key for key in (canonical_key, url_key) if key}
        if keys & seen_urls or (title_key and title_key in seen_titles):
            continue
        seen_urls.update(keys)
        if title_key:
            seen_titles.add(title_key)
        deduped.append(record)
    return deduped


def _diagnostic_for_records(
    source_name: str,
    records: list[dict[str, Any]],
    *,
    status: str,
    extracted: int,
    source_url: str | None = None,
    cache_hit: bool = False,
    error_message: str | None = None,
) -> dict[str, Any]:
    full_content = sum(
        record.get("extraction_status") == "full_content" for record in records
    )
    snippet_only = sum(bool(record.get("content_is_snippet", True)) for record in records)
    failed = sum(
        str(record.get("extraction_status") or "").startswith(("failed", "blocked"))
        for record in records
    )
    return _source_diagnostic(
        source_name,
        source_url=source_url,
        status=status,
        extracted=extracted,
        cleaned=0,
        full_content_success=full_content,
        snippet_only=snippet_only,
        duplicate=0,
        failed=failed,
        cache_hit=cache_hit,
        error_message=error_message,
    )


def _source_diagnostic(
    source_name: str,
    *,
    source_url: str | None = None,
    status: str,
    extracted: int = 0,
    cleaned: int = 0,
    full_content_success: int = 0,
    snippet_only: int = 0,
    duplicate: int = 0,
    failed: int = 0,
    cache_hit: bool = False,
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "source_name": source_name,
        "source_url": source_url,
        "extracted_count": extracted,
        "cleaned_count": cleaned,
        "full_content_success_count": full_content_success,
        "snippet_only_count": snippet_only,
        "duplicate_count": duplicate,
        "failed_count": failed,
        "status": status,
        "cache_hit": cache_hit,
        "error_message": error_message,
    }


def _content_extraction_enabled() -> bool:
    return os.getenv("NEWS_FULL_CONTENT_ENABLED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _content_timeout() -> float:
    try:
        return max(float(os.getenv("NEWS_CONTENT_TIMEOUT", "8")), 1.0)
    except ValueError:
        return 8.0


def _content_attempts() -> int:
    try:
        return min(max(int(os.getenv("NEWS_CONTENT_RETRY_ATTEMPTS", "2")), 1), 4)
    except ValueError:
        return 2


def _content_extraction_delay_seconds() -> float:
    try:
        return max(float(os.getenv("NEWS_CONTENT_EXTRACTION_DELAY_SECONDS", "0.5")), 0)
    except ValueError:
        return 0.5


def _full_content_max_articles() -> int:
    try:
        return max(int(os.getenv("NEWS_FULL_CONTENT_MAX_ARTICLES", "10")), 0)
    except ValueError:
        return 10


def _gdelt_cache_get(cache_key: str) -> dict[str, Any] | None:
    ttl_minutes = _gdelt_cache_ttl_minutes()
    if ttl_minutes <= 0:
        return None
    cache = _read_gdelt_cache()
    item = cache.get(cache_key)
    if not isinstance(item, dict):
        return None
    created_at = float(item.get("created_at", 0))
    if time.time() - created_at > ttl_minutes * 60:
        return None
    payload = item.get("payload")
    return payload if isinstance(payload, dict) else None


def _gdelt_cache_set(cache_key: str, payload: Any) -> None:
    ttl_minutes = _gdelt_cache_ttl_minutes()
    if ttl_minutes <= 0 or not isinstance(payload, dict):
        return
    cache = _read_gdelt_cache()
    cache[cache_key] = {"created_at": time.time(), "payload": payload}
    try:
        _gdelt_cache_path().write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass


def _read_gdelt_cache() -> dict[str, Any]:
    path = _gdelt_cache_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _gdelt_cache_path() -> Path:
    configured = os.getenv("NEWS_GDELT_CACHE_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(gettempdir()) / "mandiri_news_gdelt_cache.json"


def _cache_key(endpoint: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"endpoint": endpoint, "params": params}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _url_key(value: str) -> str:
    if not value:
        return ""
    parts = urlsplit(value.strip())
    if not parts.scheme or not parts.netloc:
        return ""
    return f"{parts.netloc.lower().removeprefix('www.')}{parts.path.rstrip('/')}"


def _title_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _rss_image_url(item: ElementTree.Element) -> str | None:
    for tag in ("media:content", "media:thumbnail", "enclosure"):
        element = item.find(tag, _namespaces())
        if element is None:
            continue
        url = element.attrib.get("url", "").strip()
        media_type = element.attrib.get("type", "")
        if url and (tag != "enclosure" or media_type.startswith("image/")):
            return url
    return None


def _rss_timestamp(value: str) -> str:
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return value


def _gdelt_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    for pattern in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            parsed = datetime.strptime(text, pattern).replace(
                tzinfo=timezone.utc
            )
            return parsed.isoformat()
        except ValueError:
            continue
    return text


def _gdelt_query(value: str) -> str:
    query = value.strip() or "Indonesia OR ASEAN"
    if " OR " in query.upper() and not (
        query.startswith("(") and query.endswith(")")
    ):
        return f"({query})"
    return query


def _gdelt_enabled() -> bool:
    return os.getenv("NEWS_GDELT_ENABLED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _gdelt_max_records() -> int:
    try:
        return min(
            max(int(os.getenv("NEWS_GDELT_MAX_RECORDS", "50")), 1),
            250,
        )
    except ValueError:
        return 50


def _gdelt_max_retries() -> int:
    try:
        return min(
            max(
                int(
                    os.getenv(
                        "NEWS_GDELT_MAX_RETRIES",
                        os.getenv("NEWS_RETRY_ATTEMPTS", "3"),
                    )
                ),
                1,
            ),
            6,
        )
    except ValueError:
        return _retry_attempts()


def _gdelt_cooldown_seconds() -> float:
    try:
        return max(float(os.getenv("NEWS_GDELT_COOLDOWN_SECONDS", "0")), 0)
    except ValueError:
        return 0


def _gdelt_cache_ttl_minutes() -> float:
    try:
        return max(float(os.getenv("NEWS_GDELT_CACHE_TTL_MINUTES", "15")), 0)
    except ValueError:
        return 15


def _rss_urls_from_env() -> tuple[str, ...]:
    configured = os.getenv("NEWS_RSS_URLS", "")
    return tuple(
        url.strip()
        for url in re.split(r"[\n,]+", configured)
        if url.strip()
    )


def _request_timeout() -> float:
    try:
        return max(float(os.getenv("NEWS_REQUEST_TIMEOUT", "12")), 1.0)
    except ValueError:
        return 12.0


def _retry_attempts() -> int:
    try:
        return min(max(int(os.getenv("NEWS_RETRY_ATTEMPTS", "3")), 1), 6)
    except ValueError:
        return 3


def _retry_delay() -> float:
    try:
        return max(float(os.getenv("NEWS_RETRY_DELAY_SECONDS", "1")), 0)
    except ValueError:
        return 1.0


def _requests_session() -> Any:
    import requests

    return requests.Session()


def _load_environment() -> None:
    try:
        from dotenv import find_dotenv, load_dotenv

        load_dotenv(find_dotenv(usecwd=True), override=False)
    except ImportError:
        pass


def _element_text(element: ElementTree.Element | None) -> str:
    return (element.text or "").strip() if element is not None else ""


def _namespaces() -> dict[str, str]:
    return {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "media": "http://search.yahoo.com/mrss/",
    }


def _origin(url: str) -> str | None:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


def _host_name(url: str) -> str:
    host = urlsplit(url).netloc.removeprefix("www.")
    return host or "Unknown Source"


def _safe_error(
    error: BaseException | None,
    *,
    secrets: Iterable[str] = (),
) -> str:
    message = str(error or "Unknown extraction error")
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[redacted]")
    return " ".join(message.split())[:500]
