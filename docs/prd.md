# Product Requirements Document

## Mandiri News Intelligence App

### Product Summary

Mandiri News Intelligence is a Flutter mobile application that collects news
through a Python data pipeline, stores normalized records in Supabase, and
surfaces NLP outputs that help users understand articles quickly.

The project is an independent capstone inspired by the Bank Mandiri
Project-Based Internship and is intended to demonstrate mobile engineering,
data engineering, database security, and applied AI/NLP in one portfolio.

## Problem

News readers face long articles, fragmented sources, information overload, and
weak personalization. The product should:

1. Show current news in a clear mobile feed.
2. Expose concise summaries and article context.
3. Make category and keyword discovery practical.
4. Protect bookmarks, reading history, and preferences per user.
5. Turn heterogeneous external news into structured, deduplicated data.

## Target Users

- Students and young professionals.
- Daily news readers with limited reading time.
- Users interested in topic, sentiment, and personalized discovery.

## MVP Scope

### Mobile

- Guest and authenticated entry paths.
- Latest article feed.
- Category filter and keyword search.
- Article detail with summary, sentiment, topic, and keywords.
- Bookmark list, reading history, and user preference.
- Loading, error, and empty states.

### Data and AI

- Manual or scheduled API/RSS extraction.
- HTML cleanup, timestamp normalization, and deduplication.
- Article summary, sentiment, topic, and keyword generation.
- Supabase loading through a trusted backend environment.
- Simple recommendations using categories, keywords, recency, and history.

### Platform

- Supabase PostgreSQL and Auth.
- RLS on all exposed tables.
- Flutter client uses only project URL and anon key.
- Service-role and provider credentials remain backend-only.

## Out of Scope for MVP

- Semantic search and embeddings.
- RAG question answering.
- Push notifications.
- Comment, chat, payment, and social systems.
- Full administration or analytics dashboards.
- Complex real-time ingestion and advanced recommender models.

## Functional Requirements

### Authentication

- Guests can browse published articles.
- Users can register, sign in, and sign out with email/password.
- Personal features require an authenticated session.

### Feed and Detail

- Feed is ordered by `published_at` descending.
- Cards show title, source, category, date, summary, and sentiment.
- Detail shows article content and all available analysis.
- Opening a detail records history for authenticated users.

### Search and Categories

- Users can filter by the eight seeded categories.
- Search covers title, content, summary, topic, and keywords.
- Empty queries and no-result queries have explicit states.

### Bookmarks and History

- Bookmarks are unique per user/article.
- Reading history is unique per user/article and updates `read_at`.
- RLS prevents cross-user access.

### Recommendation

- Guests receive latest or trending content.
- Authenticated users receive unread content weighted by frequently read
  categories, overlapping keywords, topic, and recency.
- The same article must not be repeated excessively.

## Data Model

- `sources`: normalized provider identity.
- `categories`: controlled category list.
- `articles`: canonical article content and publication state.
- `article_analysis`: one NLP record per article.
- `bookmarks`: unique user/article saved relationship.
- `reading_history`: unique user/article reading relationship.
- `user_preferences`: one preference row per user.

Detailed DDL and policies live in `database/`.

## Non-Functional Requirements

### Security

- No service-role or AI provider key in the Flutter project.
- All public tables use RLS.
- Public article access requires `status = 'published'`.
- User-owned rows require `auth.uid() = user_id`.

### Performance

- Cache remote images.
- Paginate the feed before production-scale use.
- Avoid duplicate requests and rebuilds.
- Index publication date, status, relationships, topics, and keywords.

### Maintainability

- Mobile code is split into screens, widgets, models, services, providers,
  theme, and utilities.
- Pipeline code is split by extract, clean, analyze, and load stages.
- SQL is separated into schema, policies, and seed data.
- Every feature includes loading, error, empty, and success behavior.

## Phase 1 Acceptance Criteria

- Flutter Android project can resolve dependencies and pass static analysis.
- All requested placeholder screens are navigable.
- UI follows the white/navy/coral design foundation.
- Supabase initialization reads placeholders from a non-committed environment
  file and tolerates an unconfigured project.
- Seven required tables, constraints, indexes, seed rows, and RLS policies are
  defined.
- ETL unit fixtures validate extract, clean, analysis, and dry-run contracts
  without entering the runtime ingestion path.
- README contains reproducible setup and security instructions.

## Roadmap

1. Foundation and contracts.
2. Supabase-backed feed, detail, category, and search.
3. Authentication and personal features.
4. Real extraction, cleanup, deduplication, and scheduling.
5. Evaluated NLP implementation.
6. Simple personalized recommendations.
7. Portfolio documentation, screenshots, demo, and release build.

## Success Metrics

- Published articles load in the mobile app.
- Pipeline inserts canonical, deduplicated records.
- Analysis exists and renders for ingested articles.
- Personal records remain isolated by RLS.
- Core user paths can be demonstrated reliably.
- Repository setup is reproducible by another developer.
