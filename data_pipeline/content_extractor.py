"""Conservative public article content extraction helpers.

The extractor only uses content available in the publisher's public HTML. It
does not bypass paywalls, login walls, robots meta restrictions, or script-only
rendering. Failures return the supplied snippet so ingestion can continue.
"""

from __future__ import annotations

import html
import os
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

USER_AGENT = "MandiriNewsPipeline/1.0 (+public news ingestion)"
_BLOCKING_MARKERS = (
    re.compile(r"\bsubscribe (?:to|for) (?:continue|read)\b", re.IGNORECASE),
    re.compile(r"\bsign in to (?:continue|read)\b", re.IGNORECASE),
    re.compile(r"\blog in to (?:continue|read)\b", re.IGNORECASE),
    re.compile(r"\bpaywall\b", re.IGNORECASE),
    re.compile(r"\bberlangganan\b", re.IGNORECASE),
    re.compile(r"\bmasuk untuk membaca\b", re.IGNORECASE),
)
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ContentExtractionResult:
    content: str
    content_is_snippet: bool
    extraction_method: str
    extraction_status: str
    canonical_url: str | None = None
    error: str | None = None


class _ArticleHtmlParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.canonical_url: str | None = None
        self.meta: dict[str, str] = {}
        self.robots = ""
        self.article_parts: list[str] = []
        self.paragraph_parts: list[str] = []
        self._ignored_depth = 0
        self._article_depth = 0
        self._paragraph_depth = 0
        self._current_link_rel = ""

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attrs_map = {key.lower(): value or "" for key, value in attrs}
        lower_tag = tag.lower()
        if lower_tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
            return
        if lower_tag in {"nav", "header", "footer", "aside", "form"}:
            self._ignored_depth += 1
            return

        if lower_tag == "link":
            rel = attrs_map.get("rel", "").lower()
            href = attrs_map.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonical_url = urljoin(self.base_url, href)
            self._current_link_rel = rel
            return

        if lower_tag == "meta":
            key = (
                attrs_map.get("property")
                or attrs_map.get("name")
                or attrs_map.get("itemprop")
            ).strip().lower()
            content = attrs_map.get("content", "").strip()
            if key and content:
                self.meta[key] = html.unescape(content)
                if key == "robots":
                    self.robots = content.lower()
            return

        class_id = " ".join(
            (attrs_map.get("class", ""), attrs_map.get("id", ""))
        ).lower()
        if any(marker in class_id for marker in ("paywall", "subscribe")):
            self._ignored_depth += 1
            return

        if lower_tag == "article" or "article" in class_id:
            self._article_depth += 1
        if lower_tag == "p":
            self._paragraph_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lower_tag = tag.lower()
        if lower_tag in {
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
        } and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if lower_tag == "article" and self._article_depth:
            self._article_depth -= 1
        if lower_tag == "p" and self._paragraph_depth:
            self._paragraph_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = _normalize_text(data)
        if not text:
            return
        if self._article_depth:
            self.article_parts.append(text)
        if self._paragraph_depth:
            self.paragraph_parts.append(text)


def extract_public_article_content(
    url: str,
    fallback_content: str,
    *,
    session: Any | None = None,
    timeout: float | None = None,
    attempts: int = 2,
    delay_seconds: float = 0.5,
) -> ContentExtractionResult:
    """Fetch and parse a public article page, returning snippet fallback safely."""
    normalized_url = url.strip()
    fallback = _normalize_text(fallback_content)
    if not _is_http_url(normalized_url):
        return _fallback(
            fallback,
            method="source_snippet",
            status="invalid_url",
            error="Article URL is not HTTP(S).",
        )

    http = session or _requests_session()
    headers = {"User-Agent": os.getenv("NEWS_USER_AGENT", USER_AGENT)}
    request_timeout = timeout if timeout is not None else _timeout()
    last_error: str | None = None
    max_attempts = max(attempts, 1)
    for attempt in range(1, max_attempts + 1):
        try:
            response = http.get(
                normalized_url,
                headers=headers,
                timeout=request_timeout,
                allow_redirects=True,
            )
            status_code = int(getattr(response, "status_code", 200))
            if status_code in {401, 403, 451}:
                return _fallback(
                    fallback,
                    method="source_snippet",
                    status="blocked",
                    error=f"HTTP {status_code}",
                )
            if status_code in {408, 425, 429, 500, 502, 503, 504}:
                if attempt < max_attempts:
                    time.sleep(_retry_wait(response, delay_seconds, attempt))
                    continue
            response.raise_for_status()
            body = _response_text(response)
            return extract_from_html(
                body,
                normalized_url,
                fallback_content=fallback,
            )
        except Exception as error:
            last_error = _safe_error(error)
            if attempt < max_attempts:
                time.sleep(delay_seconds * (2 ** (attempt - 1)))

    return _fallback(
        fallback,
        method="source_snippet",
        status="failed",
        error=last_error,
    )


def extract_from_html(
    document: str,
    url: str,
    *,
    fallback_content: str = "",
) -> ContentExtractionResult:
    """Parse already-fetched public HTML for canonical URL and article text."""
    fallback = _normalize_text(fallback_content)
    parser = _ArticleHtmlParser(url)
    parser.feed(document or "")
    canonical_url = _valid_url(parser.canonical_url)
    text_for_restrictions = " ".join(
        [
            parser.meta.get("description", ""),
            parser.meta.get("og:description", ""),
            _normalize_text(document[:5000]),
        ]
    )

    if "nosnippet" in parser.robots:
        return _fallback(
            fallback,
            method="source_snippet",
            status="blocked_by_meta_robots",
            canonical_url=canonical_url,
        )
    if any(pattern.search(text_for_restrictions) for pattern in _BLOCKING_MARKERS):
        return _fallback(
            fallback,
            method="source_snippet",
            status="blocked",
            canonical_url=canonical_url,
        )

    article_text = _normalize_text(" ".join(parser.article_parts))
    paragraph_text = _normalize_text(" ".join(parser.paragraph_parts))
    candidate = article_text if len(article_text) >= len(paragraph_text) else paragraph_text
    if _looks_like_full_content(candidate, fallback):
        return ContentExtractionResult(
            content=candidate,
            content_is_snippet=False,
            extraction_method="article_body",
            extraction_status="full_content",
            canonical_url=canonical_url,
        )

    meta_description = _best_meta_description(parser.meta)
    if meta_description and len(meta_description) > len(fallback):
        return ContentExtractionResult(
            content=meta_description,
            content_is_snippet=True,
            extraction_method="meta_description",
            extraction_status="snippet",
            canonical_url=canonical_url,
        )

    return _fallback(
        fallback,
        method="source_snippet",
        status="snippet",
        canonical_url=canonical_url,
    )


def rss_content_result(
    *,
    content: str,
    description: str = "",
    canonical_url: str | None = None,
) -> ContentExtractionResult:
    """Classify RSS-provided content without fetching the article page."""
    normalized_content = _normalize_text(content)
    normalized_description = _normalize_text(description)
    if _looks_like_full_content(normalized_content, normalized_description):
        return ContentExtractionResult(
            content=normalized_content,
            content_is_snippet=False,
            extraction_method="rss_full_content",
            extraction_status="full_content",
            canonical_url=_valid_url(canonical_url),
        )
    fallback = normalized_content or normalized_description
    return ContentExtractionResult(
        content=fallback,
        content_is_snippet=True,
        extraction_method="rss_snippet",
        extraction_status="snippet",
        canonical_url=_valid_url(canonical_url),
    )


def _looks_like_full_content(candidate: str, fallback: str) -> bool:
    text = _normalize_text(candidate)
    if len(text) < _min_full_content_characters():
        return False
    if len(text.split()) < 80:
        return False
    normalized_fallback = _normalize_text(fallback)
    if normalized_fallback and len(text) < max(len(normalized_fallback) * 2, 500):
        return False
    return True


def _best_meta_description(meta: dict[str, str]) -> str:
    for key in ("article:description", "og:description", "description"):
        value = _normalize_text(meta.get(key, ""))
        if value:
            return value
    return ""


def _fallback(
    content: str,
    *,
    method: str,
    status: str,
    canonical_url: str | None = None,
    error: str | None = None,
) -> ContentExtractionResult:
    return ContentExtractionResult(
        content=_normalize_text(content),
        content_is_snippet=True,
        extraction_method=method,
        extraction_status=status,
        canonical_url=_valid_url(canonical_url),
        error=error,
    )


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text:
        return text
    content = getattr(response, "content", b"")
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return str(content or "")


def _retry_wait(response: Any, delay: float, attempt: int) -> float:
    headers = getattr(response, "headers", {}) or {}
    try:
        retry_after = max(float(headers.get("Retry-After", 0)), 0)
    except (TypeError, ValueError):
        retry_after = 0
    return max(retry_after, delay * (2 ** (attempt - 1)))


def _timeout() -> float:
    try:
        return max(float(os.getenv("NEWS_CONTENT_TIMEOUT", "8")), 1.0)
    except ValueError:
        return 8.0


def _min_full_content_characters() -> int:
    try:
        return max(int(os.getenv("NEWS_FULL_CONTENT_MIN_CHARACTERS", "500")), 200)
    except ValueError:
        return 500


def _requests_session() -> Any:
    import requests

    return requests.Session()


def _normalize_text(value: str) -> str:
    return _SPACE_RE.sub(" ", html.unescape(value or "")).strip()


def _valid_url(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    return text if _is_http_url(text) else None


def _is_http_url(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def _safe_error(error: BaseException) -> str:
    return _normalize_text(str(error))[:300]
