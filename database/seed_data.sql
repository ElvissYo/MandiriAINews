-- Apply after schema.sql. This seed is safe to run repeatedly.

insert into public.categories (name, description)
values
  ('Business', 'Companies, industries, and entrepreneurship.'),
  ('Economy', 'Macroeconomics, policy, trade, and economic indicators.'),
  ('Technology', 'Software, hardware, AI, startups, and digital products.'),
  ('Politics', 'Government, elections, policy, and public affairs.'),
  ('Sports', 'National and international sports coverage.'),
  ('Finance', 'Banking, markets, investing, and personal finance.'),
  ('Entertainment', 'Film, music, culture, and public figures.'),
  ('World News', 'International events and global affairs.')
on conflict (name) do update
set description = excluded.description;

insert into public.sources (name, url, country)
values (
  'Mandiri Intelligence Demo',
  'https://example.com',
  'Indonesia'
)
on conflict (name) do update
set
  url = excluded.url,
  country = excluded.country;

insert into public.articles (
  id,
  title,
  content,
  url,
  image_url,
  source_id,
  category_id,
  published_at,
  status
)
values (
  '00000000-0000-4000-8000-000000000001',
  'Indonesia accelerates its digital economy roadmap',
  'This demo article validates the Phase 1 database and mobile UI foundation.',
  'https://example.com/mandiri-news-phase-1',
  'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d',
  (
    select id from public.sources
    where name = 'Mandiri Intelligence Demo'
  ),
  (
    select id from public.categories
    where name = 'Economy'
  ),
  '2026-06-13T02:30:00Z',
  'published'
)
on conflict (url) do update
set
  title = excluded.title,
  content = excluded.content,
  image_url = excluded.image_url,
  source_id = excluded.source_id,
  category_id = excluded.category_id,
  published_at = excluded.published_at,
  status = excluded.status;

insert into public.article_analysis (
  article_id,
  summary,
  sentiment,
  sentiment_score,
  topic,
  keywords
)
values (
  '00000000-0000-4000-8000-000000000001',
  'Indonesia is strengthening its digital economy roadmap and inclusion.',
  'positive',
  0.65000,
  'Economy',
  array['digital economy', 'inclusion', 'infrastructure']
)
on conflict (article_id) do update
set
  summary = excluded.summary,
  sentiment = excluded.sentiment,
  sentiment_score = excluded.sentiment_score,
  topic = excluded.topic,
  keywords = excluded.keywords;
