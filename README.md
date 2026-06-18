# Mandiri News Intelligence App

Mandiri News Intelligence is a Flutter mobile news application backed by
Supabase and a Python ETL/NLP pipeline. The product helps users read news faster
through summaries, sentiment labels, topic classification, keywords,
bookmarks, reading history, and simple recommendations.

This repository currently includes **Advanced Phase 6A: AI/NLP Upgrade,
Semantic Search, and RAG Q&A**. The previous intelligence features now include
retry/backoff, backend-only run observability, scheduled ingestion, NLP
contract evaluation, safer network errors, recommendation deduplication, and
verified Android DNS connectivity.

## Current Deliverables

- Android Flutter project with modular `lib/` structure.
- White, navy, and coral Material 3 UI foundation.
- Supabase-backed home feed, featured article, categories, detail, and search.
- Loading, error, empty, retry, and content fallback states.
- Typed models for articles, analysis, categories, sources, and joined records.
- Testable repository abstraction with a Supabase implementation.
- Riverpod providers for latest, featured, categories, detail, and search data.
- Working email/password register, login, logout, and guest flows.
- Supabase session restoration through an auth gate and Riverpod.
- User-owned bookmarks, reading history, profile stats, and category preference.
- Repository and provider boundaries for every user-specific table.
- Supabase bootstrap using environment values instead of hard-coded keys.
- PostgreSQL schema, seed data, indexes, triggers, grants, and RLS policies.
- NewsAPI, open-data GDELT, and RSS extraction with an offline fallback.
- Cleaning, URL/title deduplication, NLP analysis, and idempotent Supabase load.
- Provider-backed AI pipeline with rule-based fallback as the default.
- Optional OpenAI-compatible summaries with local extractive fallback.
- Optional transformer sentiment/topic providers when dependencies are
  installed, with deterministic fallback to `positive`, `neutral`, or
  `negative` sentiment labels and existing topic categories.
- Optional article embeddings for title + summary + content snippet.
- Optional pgvector semantic search RPC with keyword fallback.
- News Assistant Q&A screen based only on stored real articles and source
  references.
- Frequency-based keyword extraction.
- Personalized recommendation ranking from history, preference, topic, and
  keyword overlap.
- Guest trending fallback and Home insight for top topics and keywords.
- Retry/backoff and per-article failure isolation for external ingestion.
- Backend-only `pipeline_runs` observability records.
- Six-hour GitHub Actions ingestion with manual dispatch.
- NLP structural evaluation and recommendation fallback tests.
- User-friendly DNS/network errors with sanitized debug logging.
- Product, architecture, and UI documentation.

## Tech Stack

| Area | Technology |
| --- | --- |
| Mobile | Flutter 3, Dart, Riverpod, Material 3 |
| Mobile data | `supabase_flutter`, `cached_network_image`, `intl` |
| Backend | Supabase PostgreSQL, Auth, REST API, Row Level Security |
| Pipeline | Python 3.11+, requests, supabase-py |
| NLP/AI | Provider abstraction, optional LLM summaries, optional transformers, fallback rules |
| Retrieval | Optional pgvector embeddings/RPC with keyword fallback |

## Repository Structure

```text
MandiriNews/
|-- mobile_app/
|   |-- android/
|   |-- lib/
|   |   |-- models/
|   |   |-- providers/
|   |   |-- repositories/
|   |   |-- screens/
|   |   |-- services/
|   |   |-- theme/
|   |   |-- utils/
|   |   `-- widgets/
|   |-- test/
|   `-- pubspec.yaml
|-- data_pipeline/
|   |-- tests/
|   |-- evaluate_nlp.py
|   |-- extract_news.py
|   |-- clean_news.py
|   |-- nlp_analysis.py
|   |-- load_to_supabase.py
|   |-- main_pipeline.py
|   `-- requirements.txt
|-- database/
|   |-- schema.sql
|   |-- rls_policies.sql
|   `-- seed_data.sql
|-- docs/
|   |-- architecture.md
|   |-- data_pipeline.md
|   |-- prd.md
|   `-- ui_guideline.md
|-- .env.example
|-- .github/workflows/ingest-news.yml
|-- .gitignore
`-- README.md
```

`_backup_old_project/` is a local archive from the project cleanup and is
excluded from Git.

## Prerequisites

- Flutter stable with Android toolchain configured.
- Android Studio or an Android emulator/physical device.
- Python 3.11 or newer for the pipeline.
- A Supabase project for database and authentication integration.

## Run the Flutter App

1. Create the mobile environment file:

   ```powershell
   Copy-Item mobile_app/.env.example mobile_app/.env
   ```

2. Replace only these values in `mobile_app/.env`:

   ```dotenv
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   ```

   `SUPABASE_URL` must be the base project URL without `/rest/v1`.
   The app defensively normalizes that suffix, but keeping the file correct
   avoids confusing diagnostics.

3. Install packages and run:

   ```powershell
   Set-Location mobile_app
   flutter pub get
   flutter run
   ```

   On this workstation Flutter is available through
   `C:\src\flutter\bin\flutter.bat` if it has not been added to `PATH`.

4. Run checks:

   ```powershell
   flutter analyze
   flutter test
   ```

### Verify Phase 2 Data

After applying the SQL files, continue as a guest and confirm:

1. The seeded article appears as the top story and in latest news.
2. Category chips come from the `categories` table.
3. Selecting a category refreshes the article list.
4. Opening a card loads detail by article ID.
5. Search matches title, content, summary, topic, and exact keyword entries.

If only one category is visible, rerun `database/seed_data.sql`; the script is
idempotent and seeds all eight MVP categories.

### Verify Phase 3 Auth and Personal Data

1. In **Supabase Dashboard > Authentication > Providers**, keep Email enabled.
2. Register with an unused email. If email confirmation is enabled, confirm the
   message before signing in.
3. Close and reopen the app; an active Supabase session should open Home.
4. Open an article while signed in, then check that Profile shows one article
   read. Reopening it updates `read_at` instead of creating a duplicate.
5. Add and remove bookmarks from Home, detail, or Saved.
6. Select a preferred category on Profile and reopen the screen to verify it
   persists.
7. Sign out and confirm the app returns to the login/guest state.

Guest users can continue reading public news. Bookmark actions prompt them to
sign in, and no user-specific query assumes a non-null session.

## Backend Environment

Create a root environment file that is separate from `mobile_app/.env`:

```powershell
Copy-Item .env.example .env
```

For live ingestion, set:

```dotenv
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
NEWS_API_KEY=
NEWS_GDELT_ENABLED=true
NEWS_GDELT_QUERY=Indonesia OR ASEAN
NEWS_GDELT_TIMESPAN=1d
NEWS_GDELT_MAX_RECORDS=50
LLM_SUMMARY_API_URL=
LLM_SUMMARY_API_KEY=
LLM_SUMMARY_MODEL=
AI_EMBEDDING_PROVIDER=none
```

`NEWS_API_KEY` is optional because no-key GDELT and RSS remain available.
Never place
`SUPABASE_SERVICE_ROLE_KEY` or `LLM_SUMMARY_API_KEY` in `mobile_app/.env`,
Dart source, Flutter assets, APK output, logs, or GitHub workflow YAML.

Optional AI settings are backend-only:

- `LLM_SUMMARY_API_URL`, `LLM_SUMMARY_API_KEY`, and `LLM_SUMMARY_MODEL` enable
  OpenAI-compatible summary generation and backend RAG generation.
- `AI_ENABLE_TRANSFORMERS=true` or provider-specific transformer settings
  enable local model sentiment/topic classification when dependencies exist.
- `AI_EMBEDDING_PROVIDER=hash` enables no-key 384-dimension embeddings that
  Flutter can query through the semantic RPC. The `sentence-transformers`
  provider uses the optional local model path for trusted Python/backend
  retrieval. Leave it as `none` to skip embeddings.

## Run the Python Pipeline

The default command is a dry run. It does not write to Supabase.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r data_pipeline/requirements.txt
python data_pipeline/main_pipeline.py --source auto --limit 10
```

Use GDELT, RSS, or NewsAPI without changing the downstream flow:

```powershell
python data_pipeline/main_pipeline.py --source gdelt --limit 10
python data_pipeline/main_pipeline.py --source rss --limit 10
python data_pipeline/main_pipeline.py --source newsapi --limit 10
```

GDELT uses the public DOC 2.0 API and does not require an API key. In `auto`
mode the priority is NewsAPI when its key exists, enabled GDELT, RSS, then
an explicit `no_data` result. Failed providers are never replaced with
fabricated articles.

To load records into Supabase, copy `.env.example` to `.env`, set the backend
values, and explicitly add `--live`:

```powershell
python data_pipeline/main_pipeline.py --source auto --limit 20 --live
python data_pipeline/main_pipeline.py --source gdelt --limit 20 --live
```

Before the first Phase 6A live run, reapply:

1. `database/schema.sql`
2. `database/rls_policies.sql`

This adds `articles.content_is_snippet`, the backend-only `pipeline_runs`
table, optional `article_embeddings` storage when pgvector is available, and
the fallback-safe `match_articles_by_embedding` RPC. If pgvector is not
available, semantic search returns no rows and the app falls back to keyword
search.

Required live verification:

```powershell
python data_pipeline/main_pipeline.py --source rss --limit 10 --live
python data_pipeline/main_pipeline.py --source gdelt --limit 10 --live
```

Run each command twice. The second run should report existing URLs under
`skipped_duplicates` rather than creating new article rows.

See [docs/data_pipeline.md](docs/data_pipeline.md) for provider configuration,
NLP output, upsert behavior, tests, and fallback details.

## Scheduled Ingestion

The workflow `.github/workflows/ingest-news.yml` runs every six hours and can
also be started from **GitHub > Actions > Scheduled News Ingestion > Run
workflow**.

Configure these repository Actions secrets:

| Secret | Required |
| --- | --- |
| `SUPABASE_URL` | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes |
| `NEWS_API_KEY` | No |
| `LLM_SUMMARY_API_URL` | No |
| `LLM_SUMMARY_API_KEY` | No |
| `LLM_SUMMARY_MODEL` | No |

Optional repository Actions variables:

| Variable | Default |
| --- | --- |
| `AI_EMBEDDING_PROVIDER` | `none` |
| `AI_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |

The workflow runs Python tests and then performs a live real-source ingestion.
Run output is visible in Actions logs, while the durable summary is written to
`pipeline_runs`.

## Android Network Verification

The Android manifest already includes `android.permission.INTERNET`. For a
device test:

1. Ensure `mobile_app/.env` uses the base Supabase URL.
2. Confirm the device network is validated and can resolve the Supabase host.
3. Rebuild the app because `.env` is bundled as a Flutter asset.
4. Open Home, retry the feed, then open an article detail.
5. If DNS fails, switch WiFi, use a mobile hotspot, or restart the router DNS.

During Phase 5 diagnosis the device was connected to validated WiFi but had
previously produced a transient resolver failure. A later direct device test
resolved and reached the Supabase host successfully. The UI now shows a short
DNS/network message instead of the raw exception.

## Verify Phase 4 Intelligence

Run Python checks:

```powershell
python -m unittest discover -s data_pipeline/tests -v
python data_pipeline/main_pipeline.py --source rss --limit 10
python data_pipeline/main_pipeline.py --source gdelt --limit 10
python data_pipeline/main_pipeline.py --source auto --limit 10
python -m data_pipeline.evaluate_nlp --source rss --limit 3
```

Run Flutter checks:

```powershell
Set-Location mobile_app
flutter analyze
flutter test
```

Manual recommendation test:

1. As a guest, Home shows `Trending now`, derived from recent article topics,
   keywords, and publication time.
2. Sign in, choose a preferred category, and open two articles in that
   category.
3. Return to Home and refresh. `Recommended for you` should prioritize unread
   articles matching the preferred/read categories, topics, or keywords.
4. Reopening an article updates history and removes it from personalized
   candidates when alternatives exist.

Manual trending test:

1. Load several analyzed records through the pipeline.
2. Open Home and verify `Trending Topics` and `Top Keywords` chips.
3. Run the pipeline again with the same records and verify chips are not
   duplicated because the underlying article URLs are upserted.

The MVP trend score is based on topic/keyword frequency plus recency. It is not
an engagement or social-velocity metric.

## Verify Phase 6A AI, Semantic Search, and Q&A

Run Python checks:

```powershell
python -m unittest discover -s data_pipeline/tests -v
python -m data_pipeline.evaluate_nlp --source rss --limit 3
python data_pipeline/main_pipeline.py --source rss --limit 10
```

Optional embedding dry-run:

```powershell
$env:AI_EMBEDDING_PROVIDER='hash'
python data_pipeline/main_pipeline.py --source rss --limit 10
```

Run Flutter checks:

```powershell
Set-Location mobile_app
flutter analyze
flutter test
```

Manual app checks:

1. Search for a concept such as `economy policy`. If pgvector hash embeddings
   are available, the repository tries semantic retrieval first; otherwise
   results come from keyword search. Provider mismatches fall back safely.
2. Open **News Assistant**, ask about stored news, and verify the answer card
   includes source article titles.
3. Remove all LLM variables and confirm summaries, search, and Q&A still work
   with local fallbacks.

## Apply the Supabase SQL

Open **Supabase Dashboard > SQL Editor** and run the files in this exact order:

1. `database/schema.sql`
2. `database/rls_policies.sql`
3. `database/seed_data.sql`

The scripts are designed to be re-runnable. After applying them:

- Guests can select only articles whose status is `published`.
- Guests can read analysis only for published articles.
- Authenticated users can manage only their own bookmarks, reading history,
  and preferences.
- Article and NLP writes remain available only to trusted backend/service-role
  processes.

Phase 5 adds `articles.content_is_snippet` and `pipeline_runs`. Reapply
`database/schema.sql` and `database/rls_policies.sql` before enabling scheduled
ingestion.

## Environment Variables

### Mobile: `mobile_app/.env`

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | Public Supabase project URL |
| `SUPABASE_ANON_KEY` | Public anon client key protected by RLS |

### Backend: root `.env`

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Privileged ETL key, backend only |
| `NEWS_API_KEY` | External provider credential for Phase 4 |
| `NEWS_SOURCE` | `auto`, `newsapi`, `gdelt`, or `rss` |
| `NEWS_GDELT_ENABLED` | Enable no-key GDELT in `auto` mode |
| `NEWS_GDELT_QUERY` | GDELT DOC query |
| `NEWS_GDELT_TIMESPAN` | Recent GDELT search window |
| `NEWS_GDELT_MAX_RECORDS` | GDELT request cap, maximum 250 |
| `NEWS_RSS_URLS` | Comma-separated public RSS feeds |
| `LLM_SUMMARY_API_*` | Optional private summary endpoint configuration |
| `AI_ENABLE_TRANSFORMERS` | Optional local transformer sentiment/topic toggle |
| `AI_SENTIMENT_PROVIDER` | `rule-based` or transformer provider selection |
| `AI_TOPIC_PROVIDER` | `rule-based` or zero-shot transformer provider selection |
| `AI_EMBEDDING_PROVIDER` | `none`, `hash`, `auto`, or `sentence-transformers`; mobile semantic RPC is provider-matched and works with `hash` vectors |
| `AI_EMBEDDING_MODEL` | Optional sentence-transformers model name |
| `AI_EMBEDDING_DIMENSIONS` | Embedding size; pgvector schema expects `384` |

## Development Roadmap

1. **Phase 1 - Foundation:** project structure, theme, placeholders, SQL, RLS,
   Supabase bootstrap, and ETL skeleton.
2. **Phase 2 - Basic News App (complete):** query published articles, home
   feed, category filter, article detail, loading/error/empty states, and
   multi-field search.
3. **Phase 3 - Authentication (complete):** persistent auth, guest handling,
   private bookmarks, deduplicated history, profile stats, and preference.
4. **Phase 4 - Intelligence MVP (complete):** real API/RSS adapters,
   normalization, deduplication, fallback NLP, simple recommendations, and
   trending insight.
5. **Phase 5 - Stabilization (implemented):** retries, observability, scheduled
   ingestion, NLP contract evaluation, network UX, and recommendation
   hardening.
6. **Phase 6A - AI/NLP upgrade (implemented):** provider-backed NLP, optional
   LLM summaries, optional embeddings, semantic-search fallback, and RAG Q&A
   over stored real articles.
7. **Later release work:** signed build preparation, model quality review,
   analytics dashboards, and push notifications.

See [docs/prd.md](docs/prd.md), [docs/architecture.md](docs/architecture.md),
and [docs/ui_guideline.md](docs/ui_guideline.md) for implementation contracts.
