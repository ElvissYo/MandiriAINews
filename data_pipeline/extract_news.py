"""Extract news from real NewsAPI, GDELT, or RSS sources."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable
from urllib.parse import urlsplit
from xml.etree import ElementTree

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
    attempts = 0
    if provider in {"auto", "newsapi"}:
        api_key = os.getenv("NEWS_API_KEY", "").strip()
        if api_key:
            try:
                records, used_attempts = _extract_news_api(
                    http,
                    api_key,
                    requested_limit,
                )
                attempts += used_attempts
                if records:
                    return ExtractionResult(
                        records[:requested_limit],
                        "newsapi",
                        attempts,
                        tuple(errors),
                    )
                errors.append("NewsAPI returned no articles.")
            except Exception as error:
                attempts += int(getattr(error, "attempts", 0))
                errors.append(_safe_error(error, secrets=(api_key,)))
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
            records, used_attempts = _extract_gdelt(
                http,
                requested_limit,
            )
            attempts += used_attempts
            if records:
                return ExtractionResult(
                    records[:requested_limit],
                    "gdelt",
                    attempts,
                    tuple(errors),
                )
            errors.append("GDELT returned no articles.")
        except Exception as error:
            attempts += int(getattr(error, "attempts", 0))
            errors.append(_safe_error(error))
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
                records, used_attempts, rss_errors = _extract_rss(
                    http,
                    configured_urls,
                    requested_limit,
                )
                attempts += used_attempts
                errors.extend(rss_errors)
                if records:
                    return ExtractionResult(
                        records[:requested_limit],
                        "rss",
                        attempts,
                        tuple(errors),
                    )
                errors.append("Configured RSS feeds returned no articles.")
            except Exception as error:
                errors.append(_safe_error(error))
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
    )


def _extract_news_api(
    session: Any,
    api_key: str,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
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
        records.append(
            {
                "title": item.get("title"),
                "content": item.get("content") or item.get("description"),
                "url": url,
                "image_url": item.get("urlToImage"),
                "source_name": source.get("name") or _host_name(url),
                "source_url": _origin(url),
                "source_country": None,
                "category": "World News",
                "published_at": item.get("publishedAt"),
                "content_is_snippet": True,
            }
        )
    return records, attempts


def _extract_gdelt(
    session: Any,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    endpoint = os.getenv("NEWS_GDELT_API_URL", DEFAULT_GDELT_API_URL).strip()
    query = _gdelt_query(
        os.getenv("NEWS_GDELT_QUERY", "Indonesia OR ASEAN")
    )
    timespan = os.getenv("NEWS_GDELT_TIMESPAN", "1d").strip() or "1d"
    response, attempts = _request_with_retry(
        session,
        endpoint,
        params={
            "query": query,
            "mode": "artlist",
            "maxrecords": min(limit, _gdelt_max_records()),
            "format": "json",
            "timespan": timespan,
            "sort": "datedesc",
        },
        headers={"User-Agent": "MandiriNewsPipeline/1.0"},
        timeout=_request_timeout(),
    )
    payload = response.json()
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
            }
        )
    return records, attempts


def _extract_rss(
    session: Any,
    rss_urls: Iterable[str],
    limit: int,
) -> tuple[list[dict[str, Any]], int, list[str]]:
    records: list[dict[str, Any]] = []
    attempts = 0
    errors: list[str] = []
    for feed_url in rss_urls:
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
            errors.append(_safe_error(error))
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
            records.append(
                {
                    "title": _element_text(item.find("title")),
                    "content": (
                        _element_text(item.find("content:encoded", _namespaces()))
                        or _element_text(item.find("description"))
                    ),
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
                    "content_is_snippet": True,
                }
            )
            if len(records) >= limit:
                return records, attempts, errors
    return records, attempts, errors


def _request_with_retry(
    session: Any,
    url: str,
    **kwargs: Any,
) -> tuple[Any, int]:
    attempts = _retry_attempts()
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


def _rss_urls_from_env() -> tuple[str, ...]:
    configured = os.getenv("NEWS_RSS_URLS", "")
    return tuple(url.strip() for url in configured.split(",") if url.strip())


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
