"""Clean, normalize, and deduplicate extracted news records."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
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
_RESERVED_IMAGE_HOSTS = {"example.com", "example.org", "example.net"}
_PLACEHOLDER_IMAGE_HOSTS = {
    "dummyimage.com",
    "fakeimg.pl",
    "placehold.co",
    "placehold.it",
    "placeholder.com",
    "via.placeholder.com",
}
_PLACEHOLDER_IMAGE_MARKERS = (
    "blank-image",
    "blank_image",
    "default-image",
    "default_image",
    "dummy",
    "no-image",
    "no_image",
    "placeholder",
    "sample-image",
    "sample_image",
)


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
    seen_title_texts: list[str] = []

    for raw in raw_articles:
        title = strip_html(str(raw.get("title") or ""))
        url = normalize_url(str(raw.get("url") or ""))
        canonical_url = _nullable_url(raw.get("canonical_url"))
        if canonical_url:
            canonical_url = normalize_url(canonical_url)
        if not title or not _is_http_url(url):
            continue

        title_key = _TITLE_KEY_RE.sub("", title.lower())
        url_keys = {url}
        if canonical_url:
            url_keys.add(canonical_url)
        if (
            not title_key
            or url_keys & seen_urls
            or title_key in seen_titles
            or _is_similar_title(title, seen_title_texts)
        ):
            continue

        seen_urls.update(url_keys)
        seen_titles.add(title_key)
        seen_title_texts.append(title)
        category = _normalize_text(str(raw.get("category") or "World News"))
        cleaned.append(
            {
                "title": title,
                "content": strip_html(str(raw.get("content") or "")),
                "url": url,
                "canonical_url": canonical_url,
                "image_url": _nullable_image_url(raw.get("image_url")),
                "source_name": normalize_source_name(raw.get("source_name")),
                "source_url": _nullable_url(raw.get("source_url")),
                "source_country": _nullable_text(raw.get("source_country")),
                "category": category or "World News",
                "published_at": normalize_timestamp(raw.get("published_at")),
                "status": "published",
                "content_is_snippet": bool(raw.get("content_is_snippet", False)),
                "extraction_method": _nullable_text(
                    raw.get("extraction_method")
                ) or "source_snippet",
                "extraction_status": _nullable_text(
                    raw.get("extraction_status")
                ) or (
                    "snippet"
                    if bool(raw.get("content_is_snippet", False))
                    else "full_content"
                ),
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


def _nullable_image_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith("data:") or "base64," in lowered:
        return None
    if not _is_http_url(text):
        return None
    parts = urlsplit(text)
    hostname = (parts.hostname or "").lower()
    if _is_reserved_image_host(hostname) or _is_placeholder_image_url(
        lowered,
        hostname,
    ):
        return None
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            parts.query,
            "",
        )
    )


def _is_http_url(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def _is_reserved_image_host(hostname: str) -> bool:
    return any(
        hostname == reserved or hostname.endswith(f".{reserved}")
        for reserved in _RESERVED_IMAGE_HOSTS
    )


def _is_placeholder_image_url(lowered_url: str, hostname: str) -> bool:
    if any(
        hostname == placeholder or hostname.endswith(f".{placeholder}")
        for placeholder in _PLACEHOLDER_IMAGE_HOSTS
    ):
        return True
    return any(marker in lowered_url for marker in _PLACEHOLDER_IMAGE_MARKERS)


def _is_similar_title(title: str, existing_titles: list[str]) -> bool:
    normalized = _title_words(title)
    if len(normalized) < 12:
        return False
    for existing in existing_titles:
        existing_normalized = _title_words(existing)
        if len(existing_normalized) < 12:
            continue
        if SequenceMatcher(None, normalized, existing_normalized).ratio() >= 0.92:
            return True
    return False


def _title_words(value: str) -> str:
    return _normalize_text(
        re.sub(r"[^a-z0-9]+", " ", value.lower())
    )
