# Data Pipeline

## Scope

The Phase 4 pipeline performs:

```text
extract -> clean -> deduplicate -> NLP analysis -> Supabase upsert
```

It intentionally avoids RAG, vector search, model training, orchestration
platforms, and a production backend. Every NLP task has a deterministic local
fallback so the flow remains testable without paid API credentials.

## Environment Setup

Create a backend-only environment file at the repository root:

```powershell
Copy-Item .env.example .env
```

Required only for a live Supabase load:

```dotenv
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

Optional extraction settings:

```dotenv
NEWS_SOURCE=auto
NEWS_API_KEY=your-news-provider-key
NEWS_RSS_URLS=https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id
```

`NEWS_SOURCE=auto` tries NewsAPI when `NEWS_API_KEY` exists, then RSS, then
local dummy records. Use `dummy` for a fully deterministic offline run.

Optional LLM summary settings:

```dotenv
LLM_SUMMARY_API_URL=https://provider.example/v1/chat/completions
LLM_SUMMARY_API_KEY=your-private-api-key
LLM_SUMMARY_MODEL=provider-model-name
```

The endpoint must accept an OpenAI-compatible chat-completions request. If any
setting is absent or the request fails, extractive summarization is used.

## Install

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r data_pipeline/requirements.txt
```

## Run

Deterministic dry-run:

```powershell
python data_pipeline/main_pipeline.py --source dummy --limit 3
```

RSS dry-run:

```powershell
python data_pipeline/main_pipeline.py --source rss --limit 10
```

NewsAPI dry-run:

```powershell
python data_pipeline/main_pipeline.py --source newsapi --limit 10
```

Live Supabase load:

```powershell
python data_pipeline/main_pipeline.py --source auto --limit 20 --live
```

The default is always dry-run. Supabase writes occur only with `--live`.

## Cleaning Contract

The cleaning stage:

- rejects missing titles and invalid/missing HTTP URLs;
- removes HTML, scripts, styles, and excess whitespace;
- removes common tracking query parameters and URL fragments;
- converts timestamps to UTC ISO-8601;
- normalizes source names;
- applies `published` status;
- removes duplicates by canonical URL or normalized title.

## NLP Output

Each analyzed article contains:

```json
{
  "analysis": {
    "summary": "Indonesia is strengthening digital infrastructure...",
    "sentiment": "positive",
    "sentiment_score": 1.0,
    "topic": "Economy",
    "keywords": ["digital", "economy", "infrastructure"]
  }
}
```

Summary uses the configured LLM endpoint when available, otherwise an
extractive sentence scorer. Sentiment is a small Indonesian/English lexicon,
topic classification uses keyword overlap, and keywords use frequency-based
unigrams plus repeated bigrams.

## Idempotent Loading

The loader uses existing unique constraints:

| Table | Conflict key |
| --- | --- |
| `sources` | `name` |
| `categories` | `name` |
| `articles` | `url` |
| `article_analysis` | `article_id` |

Running the same input repeatedly updates rows rather than creating duplicates.

## Tests

```powershell
python -m unittest discover -s data_pipeline/tests -v
```

Tests cover validation, HTML cleanup, duplicate removal, timestamp
normalization, NLP structure, sentiment fallback, and idempotent fake-client
upserts.

## Security

- Root `.env` is ignored by Git.
- `SUPABASE_SERVICE_ROLE_KEY`, NewsAPI keys, and LLM keys are backend-only.
- `mobile_app/.env` contains only `SUPABASE_URL` and
  `SUPABASE_ANON_KEY`.
- The pipeline never includes secret values in its JSON output.
- Do not place the service-role key in Dart, Flutter assets, APKs, logs, or
  screenshots.
