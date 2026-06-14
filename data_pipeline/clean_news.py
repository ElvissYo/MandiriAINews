"""Clean, normalize, and deduplicate extracted news records."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SPACE_RE = re.compile(r"\s+")
_TITLE_KEY_RE = re.compile(r"[^a-z0-9]+")
_TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def strip_html(value: str) -> str:
    """Convert HTML content into normalized plain text."""
    parser = _TextExtractor()
    parser.feed(value)
    return _normalize_text(html.unescape(" ".join(parser.parts)))


def normalize_url(value: str) -> str:
    """Remove fragments and common tracking parameters from a URL."""
    parts = urlsplit(value.strip())
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMETERS
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            urlencode(query),
            "",
        )
    )


def normalize_timestamp(value: Any) -> str:
    """Return an ISO-8601 UTC timestamp."""
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        parsed = _parse_timestamp(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def normalize_source_name(value: Any) -> str:
    """Normalize whitespace and common feed suffixes in source names."""
    name = strip_html(str(value or ""))
    name = re.sub(r"\s+-\s+Google News$", "", name, flags=re.IGNORECASE)
    return name or "Unknown Source"


def clean_articles(
    raw_articles: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate and normalize articles, deduplicating by URL and title."""
    cleaned: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for raw in raw_articles:
        title = strip_html(str(raw.get("title") or ""))
        url = normalize_url(str(raw.get("url") or ""))
        if not title or not _is_http_url(url):
            continue

        title_key = _TITLE_KEY_RE.sub("", title.lower())
        if not title_key or url in seen_urls or title_key in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(title_key)
        category = _normalize_text(str(raw.get("category") or "World News"))
        cleaned.append(
            {
                "title": title,
                "content": strip_html(str(raw.get("content") or "")),
                "url": url,
                "image_url": _nullable_url(raw.get("image_url")),
                "source_name": normalize_source_name(raw.get("source_name")),
                "source_url": _nullable_url(raw.get("source_url")),
                "source_country": _nullable_text(raw.get("source_country")),
                "category": category or "World News",
                "published_at": normalize_timestamp(raw.get("published_at")),
                "status": "published",
            }
        )

    return cleaned


def _parse_timestamp(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc)


def _normalize_text(value: str) -> str:
    return _SPACE_RE.sub(" ", value).strip()


def _nullable_text(value: Any) -> str | None:
    text = _normalize_text(str(value or ""))
    return text or None


def _nullable_url(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if _is_http_url(text) else None


def _is_http_url(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)
