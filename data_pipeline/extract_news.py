"""Extract news from NewsAPI or public RSS feeds with an offline fallback."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable
from urllib.parse import urlsplit
from xml.etree import ElementTree

DEFAULT_RSS_URLS = (
    "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id",
)
DEFAULT_NEWS_API_URL = "https://newsapi.org/v2/everything"


def extract_news(
    limit: int = 10,
    *,
    source: str | None = None,
    rss_urls: Iterable[str] | None = None,
    session: Any | None = None,
) -> list[dict[str, Any]]:
    """Return raw article dictionaries from the configured source.

    `NEWS_SOURCE` accepts `auto`, `newsapi`, `rss`, or `dummy`. Auto mode tries
    NewsAPI when a key exists, then RSS, and finally deterministic dummy data.
    """
    requested_limit = max(limit, 0)
    if requested_limit == 0:
        return []

    provider = (source or os.getenv("NEWS_SOURCE", "auto")).strip().lower()
    if provider not in {"auto", "newsapi", "rss", "dummy"}:
        raise ValueError("NEWS_SOURCE must be auto, newsapi, rss, or dummy.")
    if provider == "dummy":
        return _dummy_articles(requested_limit)

    http = session or _requests_session()
    if provider in {"auto", "newsapi"}:
        api_key = os.getenv("NEWS_API_KEY", "").strip()
        if api_key:
            try:
                records = _extract_news_api(http, api_key, requested_limit)
                if records:
                    return records[:requested_limit]
            except Exception:
                if provider == "newsapi":
                    return _dummy_articles(requested_limit)

    if provider in {"auto", "rss"}:
        configured_urls = list(rss_urls or _rss_urls_from_env())
        try:
            records = _extract_rss(http, configured_urls, requested_limit)
            if records:
                return records[:requested_limit]
        except Exception:
            pass

    return _dummy_articles(requested_limit)


def _extract_news_api(
    session: Any,
    api_key: str,
    limit: int,
) -> list[dict[str, Any]]:
    endpoint = os.getenv("NEWS_API_URL", DEFAULT_NEWS_API_URL).strip()
    query = os.getenv("NEWS_API_QUERY", "Indonesia OR ASEAN").strip()
    language = os.getenv("NEWS_API_LANGUAGE", "en").strip()
    response = session.get(
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
    response.raise_for_status()
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
            }
        )
    return records


def _extract_rss(
    session: Any,
    rss_urls: Iterable[str],
    limit: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for feed_url in rss_urls:
        response = session.get(
            feed_url,
            headers={"User-Agent": "MandiriNewsPipeline/1.0"},
            timeout=_request_timeout(),
        )
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
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
                }
            )
            if len(records) >= limit:
                return records
    return records


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


def _rss_urls_from_env() -> tuple[str, ...]:
    configured = os.getenv("NEWS_RSS_URLS", "")
    urls = tuple(url.strip() for url in configured.split(",") if url.strip())
    return urls or DEFAULT_RSS_URLS


def _request_timeout() -> float:
    try:
        return max(float(os.getenv("NEWS_REQUEST_TIMEOUT", "12")), 1.0)
    except ValueError:
        return 12.0


def _requests_session() -> Any:
    import requests

    return requests.Session()


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


def _dummy_articles(limit: int) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    records = [
        {
            "title": "Indonesia accelerates its digital economy roadmap",
            "content": (
                "<p>Indonesia is strengthening digital infrastructure and "
                "financial inclusion through coordinated public and private "
                "initiatives.</p>"
            ),
            "url": "https://example.com/digital-economy?utm_source=fallback",
            "image_url": (
                "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d"
            ),
            "source_name": "Mandiri Intelligence Demo",
            "source_url": "https://example.com",
            "source_country": "Indonesia",
            "category": "Economy",
            "published_at": now,
        },
        {
            "title": "AI adoption reshapes the regional technology sector",
            "content": (
                "<p>Technology companies are moving from experiments toward "
                "governed AI systems with measurable business value.</p>"
            ),
            "url": "https://example.com/ai-adoption",
            "image_url": (
                "https://images.unsplash.com/photo-1677442136019-21780ecad995"
            ),
            "source_name": "Mandiri Intelligence Demo",
            "source_url": "https://example.com",
            "source_country": "Indonesia",
            "category": "Technology",
            "published_at": now,
        },
        {
            "title": "Regional markets gain as investors assess new policy",
            "content": (
                "<p>Asian markets gained while investors reviewed new banking "
                "policy and improving trade expectations.</p>"
            ),
            "url": "https://example.com/regional-markets",
            "image_url": None,
            "source_name": "Mandiri Intelligence Demo",
            "source_url": "https://example.com",
            "source_country": "Indonesia",
            "category": "Finance",
            "published_at": now,
        },
    ]
    return records[:limit]
