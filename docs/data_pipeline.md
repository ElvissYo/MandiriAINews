# Data Pipeline

## Scope

The Advanced Phase 6A pipeline performs:

```text
extract with retry -> clean/deduplicate -> NLP analysis/evaluation
  -> optional embeddings -> Supabase upsert -> pipeline run observability
```

Runtime extraction is real-data only. Unit tests use isolated fixtures, but
failed providers never create fabricated articles. RAG answers and semantic
search operate only over stored article records.

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
NEWS_GDELT_ENABLED=true
NEWS_GDELT_QUERY=Indonesia OR ASEAN
NEWS_GDELT_TIMESPAN=1d
NEWS_GDELT_MAX_RECORDS=50
NEWS_RSS_URLS=https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id
NEWS_RETRY_ATTEMPTS=3
NEWS_RETRY_DELAY_SECONDS=1
```

GDELT DOC 2.0 is an open-data, no-key source. `NEWS_SOURCE=auto` tries
NewsAPI when `NEWS_API_KEY` exists, then enabled GDELT, then RSS feeds
configured through `NEWS_RSS_URLS`. Set `NEWS_GDELT_ENABLED=false`
to skip GDELT only in auto mode. An explicit `--source gdelt` run still uses
GDELT. If every real provider fails or returns zero records, the run ends as
`no_data` and writes no articles.

Optional LLM summary settings:

```dotenv
LLM_SUMMARY_API_URL=https://provider.example/v1/chat/completions
LLM_SUMMARY_API_KEY=your-private-api-key
LLM_SUMMARY_MODEL=provider-model-name
```

The endpoint must accept an OpenAI-compatible chat-completions request. If any
setting is absent or the request fails, extractive summarization is used. The
same backend-only provider can generate RAG answers in Python helpers; Flutter
never receives the key.

Optional local model and embedding settings:

```dotenv
AI_ENABLE_TRANSFORMERS=false
AI_SENTIMENT_PROVIDER=rule-based
AI_TOPIC_PROVIDER=rule-based
AI_EMBEDDING_PROVIDER=none
AI_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
AI_EMBEDDING_DIMENSIONS=384
```

`AI_ENABLE_TRANSFORMERS=true` tries optional `transformers` sentiment and
zero-shot topic providers. If imports or inference fail, rule-based providers
are used. `AI_EMBEDDING_PROVIDER=hash` enables no-key deterministic embeddings
that the Flutter client can query safely. `sentence-transformers` uses an
optional local model for trusted Python/backend retrieval. Leave embeddings as
`none` to skip vector generation.

## Install

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r data_pipeline/requirements.txt
```

## Run

Auto real-source dry-run:

```powershell
python data_pipeline/main_pipeline.py --source auto --limit 10
```

RSS dry-run:

```powershell
python data_pipeline/main_pipeline.py --source rss --limit 10
```

GDELT no-key dry-run:

```powershell
python data_pipeline/main_pipeline.py --source gdelt --limit 10
```

NewsAPI dry-run:

```powershell
python data_pipeline/main_pipeline.py --source newsapi --limit 10
```

Live Supabase load:

```powershell
python data_pipeline/main_pipeline.py --source auto --limit 20 --live
```

Explicit GDELT live ingestion:

```powershell
python data_pipeline/main_pipeline.py --source gdelt --limit 20 --live
```

The default is always dry-run. Supabase writes occur only with `--live`.
The CLI returns a non-zero exit code for `partial`, `failed`, and `no_data`
runs so schedulers expose degraded ingestion instead of silently succeeding.

### Live Verification

Apply `database/schema.sql` and `database/rls_policies.sql`, then run:

```powershell
python data_pipeline/main_pipeline.py --source rss --limit 10 --live
python data_pipeline/main_pipeline.py --source gdelt --limit 10 --live
```

Repeat both commands. Existing URLs are updated idempotently and counted as
`skipped_duplicates`; they do not create duplicate rows.

## Cleaning Contract

The cleaning stage:

- rejects missing titles and invalid/missing HTTP URLs;
- removes HTML, scripts, styles, and excess whitespace;
- removes common tracking query parameters and URL fragments;
- converts timestamps to UTC ISO-8601;
- normalizes source names;
- applies `published` status;
- marks RSS, NewsAPI, and GDELT content as `content_is_snippet=true`;
- removes duplicates by canonical URL or normalized title;
- rejects obvious demo/test markers and reserved example-domain records before
  any Supabase write.

The pipeline does not bypass paywalls or scrape restricted pages. Provider
text or title remains the legal fallback when full article content is
unavailable.

## GDELT Source

The adapter uses the public GDELT DOC 2.0 Article List JSON endpoint. It maps
`title`, `url`, `socialimage`, `domain`, `sourcecountry`, and `seendate` into
the shared article contract. GDELT Article List does not consistently return
article body text, so `snippet`, `description`, or `content` is used when
present; otherwise the title becomes the snippet fallback.

`NEWS_GDELT_MAX_RECORDS` is clamped to the API limit of 250 and is also bounded
by the CLI `--limit`. Boolean `OR` queries are wrapped in parentheses for the
GDELT query syntax. See the
[official GDELT DOC 2.0 API overview](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/).

## Retry and Failure Isolation

- RSS/API requests use configurable timeout and exponential backoff.
- HTTP 408, 425, 429, and common 5xx responses are retried.
- HTTP 429 honors `Retry-After` and uses at least a five-second cooldown.
- A failed RSS feed does not prevent other configured feeds from running.
- Invalid records and per-article Supabase failures are counted and skipped
  without stopping successful articles.
- Provider and load errors are truncated and credentials are redacted.

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
extractive sentence scorer. Sentiment and topic classification use provider
interfaces: optional transformers when configured and available, otherwise a
small Indonesian/English lexicon plus keyword topic overlap. Sentiment output
is always `positive`, `neutral`, or `negative`, with a numeric
`sentiment_score`. Topic output maps to the existing app categories where
possible: World News, Business, Economy, Technology, Politics, Sports,
Finance, and Entertainment. Keywords use frequency-based unigrams plus
repeated bigrams.

When embeddings are enabled, each analyzed article also carries top-level
embedding metadata outside the stable `analysis` object:

```json
{
  "embedding": {
    "text": "title + summary + content snippet",
    "vector": [0.01, -0.02],
    "provider": "hash",
    "dimensions": 384
  }
}
```

The loader stores this in `article_embeddings` only when the optional pgvector
table exists. Embedding write failures do not fail the article load.

## Semantic Search

`database/schema.sql` attempts to enable pgvector and create
`article_embeddings` with a 384-dimension `vector` column. It also defines
`match_articles_by_embedding(query_embedding text, match_count integer,
query_provider text)`. The RPC returns article IDs ordered by cosine distance
for published articles with the same embedding provider as the query. If
pgvector is unavailable, the table is skipped and the RPC returns no rows.

Python helper `data_pipeline.semantic_search.semantic_search_articles` ranks
records by available embeddings and falls back to keyword overlap when
embeddings or providers are unavailable. Flutter uses the same strategy at the
repository boundary: try the RPC with the no-key `hash` query provider first,
then use the existing title/content/summary/topic/keyword search. If stored
embeddings were produced by another provider, the provider filter prevents a
mismatched vector comparison and the app falls back to keyword search.

## RAG Q&A

`data_pipeline.rag_qa.answer_question` retrieves stored article context with
semantic search or keyword fallback. If the backend LLM provider is configured,
it asks the model to answer only from retrieved context. If no LLM is
configured or generation fails, it returns an extractive answer from retrieved
summaries/content. Every result includes source article titles/URLs.

The Flutter **News Assistant** screen uses public stored articles and returns
an extractive answer with a source list. It does not call an LLM directly and
does not contain service-role or LLM keys.

Evaluate the structural contract separately:

```powershell
python -m data_pipeline.evaluate_nlp --source rss --limit 3
```

Example:

```json
{
  "status": "passed",
  "evaluated": 3,
  "failed_checks": 0,
  "failures": []
}
```

## Idempotent Loading

The loader uses existing unique constraints:

| Table | Conflict key |
| --- | --- |
| `sources` | `name` |
| `categories` | `name` |
| `articles` | `url` |
| `article_analysis` | `article_id` |

Running the same input repeatedly updates rows rather than creating duplicates.

## Observability

Every live run attempts to write one service-role-only row to `pipeline_runs`,
including `no_data` and failed runs:

| Field | Meaning |
| --- | --- |
| `started_at`, `completed_at` | UTC run window |
| `source` | Resolved provider |
| `extracted`, `cleaned` | Input and normalized counts |
| `inserted` | New article URLs |
| `skipped_duplicates` | Cleaning duplicates plus existing URLs |
| `failed` | Invalid or failed article writes |
| `status` | `success`, `partial`, `failed`, or `no_data` |
| `error_message` | Truncated safe diagnostic |

RLS is enabled and no anon/authenticated grants or policies are created.
The service-role pipeline can access the table because service-role bypasses
RLS.

## Scheduled Run

`.github/workflows/ingest-news.yml` runs at minute 17 every six hours. It also
supports `workflow_dispatch` with source and limit inputs.

Set GitHub Actions secrets:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NEWS_API_KEY` (optional)

The workflow runs unit tests before the live load. A partial, failed, or
`no_data` pipeline exits non-zero and marks the workflow run as failed.

## Tests

```powershell
python -m unittest discover -s data_pipeline/tests -v
```

Tests cover validation, HTML cleanup, duplicate removal, timestamp
normalization, mocked GDELT extraction, real-provider priority and zero-data
behavior, NLP structure/evaluation, LLM fallback, embedding shape, semantic
fallback, RAG context use, demo-content rejection, observability writes, seed
safety, and idempotent fake-client upserts.

## Security

- Root `.env` is ignored by Git.
- `SUPABASE_SERVICE_ROLE_KEY`, NewsAPI keys, and LLM keys are backend-only.
- `mobile_app/.env` contains only `SUPABASE_URL` and
  `SUPABASE_ANON_KEY`.
- The pipeline never includes secret values in its JSON output.
- Do not place the service-role key in Dart, Flutter assets, APKs, logs, or
  screenshots.
- Do not place `LLM_SUMMARY_API_KEY` in Dart, Flutter assets, APKs, logs, or
  screenshots.

## Limitations

- RSS and NewsAPI frequently provide snippets instead of full content.
- GDELT is open and no-key, but Article List results may omit body text,
  images, topic labels, or source country. Indexing time is not guaranteed to
  equal the publisher's original publication time. The public endpoint may
  also return HTTP 429 during busy periods; retry/backoff and RSS keep the
  pipeline operational when another real source is available.
- NLP remains deterministic rule-based fallback unless optional LLM or local
  transformer providers are configured and available.
- pgvector semantic search requires `article_embeddings` and matching
  384-dimension query/article embeddings. Without them, search falls back to
  keyword matching.
- Flutter Q&A is extractive unless a separate trusted backend invokes
  `data_pipeline.rag_qa` with LLM configuration.
- Recommendation remains client-side over a bounded recent article/history
  window.
- `pipeline_runs` is operational logging, not a full analytics dashboard.
