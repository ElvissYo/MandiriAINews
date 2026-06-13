# Mandiri News Intelligence App

Mandiri News Intelligence is a Flutter mobile news application backed by
Supabase and a Python ETL/NLP pipeline. The product helps users read news faster
through summaries, sentiment labels, topic classification, keywords,
bookmarks, reading history, and simple recommendations.

This repository currently includes **Phase 3 personal features**. The mobile
app reads published news from Supabase and supports email/password
authentication, persistent sessions, private bookmarks, reading history,
profile statistics, and a basic preferred-category setting.

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
- Modular Python ETL skeleton with dummy extraction and baseline NLP output.
- Product, architecture, and UI documentation.

## Tech Stack

| Area | Technology |
| --- | --- |
| Mobile | Flutter 3, Dart, Riverpod, Material 3 |
| Mobile data | `supabase_flutter`, `cached_network_image`, `intl` |
| Backend | Supabase PostgreSQL, Auth, REST API, Row Level Security |
| Pipeline | Python 3.11+, pandas, requests, supabase-py |
| NLP baseline | Extractive summary, lexicon sentiment, keyword/topic rules |

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
|   |-- prd.md
|   `-- ui_guideline.md
|-- .env.example
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

   `SUPABASE_URL` should normally be the base project URL without `/rest/v1`.
   The app also normalizes that suffix if it is present.

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

## Run the Python Pipeline Skeleton

The default command is a dry run. It does not write to Supabase.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r data_pipeline/requirements.txt
python data_pipeline/main_pipeline.py
```

To load records into Supabase, copy `.env.example` to `.env`, set the backend
values, and explicitly add `--live`:

```powershell
python data_pipeline/main_pipeline.py --live
```

`SUPABASE_SERVICE_ROLE_KEY` is backend-only. It must never appear in
`mobile_app/.env`, Dart source, an APK, screenshots, or committed files.

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

Phase 3 requires no schema migration beyond the Phase 1 tables and unique
constraints. Reapply `database/rls_policies.sql` to ensure authenticated users
can select, insert, update, and delete only rows whose `user_id` equals
`auth.uid()`.

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

## Development Roadmap

1. **Phase 1 - Foundation:** project structure, theme, placeholders, SQL, RLS,
   Supabase bootstrap, and ETL skeleton.
2. **Phase 2 - Basic News App (complete):** query published articles, home
   feed, category filter, article detail, loading/error/empty states, and
   multi-field search.
3. **Phase 3 - Authentication (complete):** persistent auth, guest handling,
   private bookmarks, deduplicated history, profile stats, and preference.
4. **Phase 4 - Data Pipeline:** real API/RSS adapters, normalization,
   deduplication, observability, and scheduled ingestion.
5. **Phase 5 - NLP:** evaluated summarization, sentiment, topic, and keyword
   models.
6. **Phase 6 - Recommendations:** reading-history and content-based ranking.
7. **Phase 7 - Portfolio:** screenshots, architecture assets, demo, and release.

See [docs/prd.md](docs/prd.md), [docs/architecture.md](docs/architecture.md),
and [docs/ui_guideline.md](docs/ui_guideline.md) for implementation contracts.
