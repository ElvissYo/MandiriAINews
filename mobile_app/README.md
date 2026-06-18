# Mobile App

Flutter client for Mandiri News Intelligence. Phase 4 adds personalized or
guest recommendations, trending topic/keyword insight, related articles,
semantic-search fallback, and the News Assistant Q&A screen using analyzed
Supabase data. Phase 5 adds safe DNS/network messages, sanitized debug
logging, and recommendation deduplication. Setup, security, pipeline, and
verification instructions are maintained in the repository root `README.md`.
Runtime screens display only published Supabase articles; when the real-source
pipeline has not loaded data yet, the app shows ingestion guidance instead of
fabricated fallback cards.
