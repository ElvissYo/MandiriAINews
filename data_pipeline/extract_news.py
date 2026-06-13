"""Extract news records from external providers.

Phase 1 returns deterministic dummy data. Replace `extract_news` with an API or
RSS adapter in Phase 4 while preserving the returned field contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def extract_news(limit: int = 10) -> list[dict[str, Any]]:
    """Return raw article dictionaries from the configured source."""
    now = datetime.now(timezone.utc).isoformat()
    dummy_articles = [
        {
            "title": "Indonesia accelerates its digital economy roadmap",
            "content": (
                "<p>Indonesia is strengthening digital infrastructure and "
                "financial inclusion through coordinated public and private "
                "initiatives.</p>"
            ),
            "url": "https://example.com/digital-economy?utm_source=phase1",
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
    ]
    return dummy_articles[: max(limit, 0)]
