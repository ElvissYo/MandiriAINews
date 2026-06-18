-- Apply after schema.sql. Only static reference data is seeded.

-- Remove the article row used by the original Phase 1 UI bootstrap.
-- article_analysis is removed by the article foreign key cascade.
delete from public.articles
where id = '00000000-0000-4000-8000-000000000001';

delete from public.sources
where url = 'https://example.com'
  and not exists (
    select 1
    from public.articles
    where articles.source_id = sources.id
  );

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
