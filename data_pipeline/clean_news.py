"""Clean, normalize, and deduplicate extracted news records."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def strip_html(value: str) -> str:
    """Convert simple HTML content into normalized plain text."""
    without_tags = _HTML_TAG_RE.sub(" ", value)
    return _SPACE_RE.sub(" ", html.unescape(without_tags)).strip()


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
        text = str(value or "").strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            parsed = datetime.now(timezone.utc)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def clean_articles(
    raw_articles: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate and normalize articles, deduplicating by URL and title."""
    cleaned: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for raw in raw_articles:
        title = _SPACE_RE.sub(" ", str(raw.get("title") or "")).strip()
        url = normalize_url(str(raw.get("url") or ""))
        if not title or not url.startswith(("http://", "https://")):
            continue

        title_key = re.sub(r"[^a-z0-9]+", "", title.lower())
        if url in seen_urls or title_key in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(title_key)
        cleaned.append(
            {
                "title": title,
                "content": strip_html(str(raw.get("content") or "")),
                "url": url,
                "image_url": str(raw.get("image_url") or "").strip() or None,
                "source_name": (
                    _SPACE_RE.sub(
                        " ", str(raw.get("source_name") or "Unknown Source")
                    ).strip()
                ),
                "source_url": str(raw.get("source_url") or "").strip() or None,
                "source_country": (
                    str(raw.get("source_country") or "").strip() or None
                ),
                "category": str(raw.get("category") or "World News").strip(),
                "published_at": normalize_timestamp(raw.get("published_at")),
                "status": "published",
            }
        )

    return cleaned
