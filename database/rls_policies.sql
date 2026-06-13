-- Apply after schema.sql.
-- The service_role bypasses RLS and must only be used by trusted ETL/backend code.

alter table public.sources enable row level security;
alter table public.categories enable row level security;
alter table public.articles enable row level security;
alter table public.article_analysis enable row level security;
alter table public.bookmarks enable row level security;
alter table public.reading_history enable row level security;
alter table public.user_preferences enable row level security;

revoke all on table public.sources from anon, authenticated;
revoke all on table public.categories from anon, authenticated;
revoke all on table public.articles from anon, authenticated;
revoke all on table public.article_analysis from anon, authenticated;
revoke all on table public.bookmarks from anon, authenticated;
revoke all on table public.reading_history from anon, authenticated;
revoke all on table public.user_preferences from anon, authenticated;

grant usage on schema public to anon, authenticated;
grant select on table public.sources to anon, authenticated;
grant select on table public.categories to anon, authenticated;
grant select on table public.articles to anon, authenticated;
grant select on table public.article_analysis to anon, authenticated;
grant select, insert, update, delete on table public.bookmarks to authenticated;
grant select, insert, update, delete
  on table public.reading_history to authenticated;
grant select, insert, update, delete
  on table public.user_preferences to authenticated;

drop policy if exists "Public can read sources" on public.sources;
create policy "Public can read sources"
on public.sources for select
to anon, authenticated
using (true);

drop policy if exists "Public can read categories" on public.categories;
create policy "Public can read categories"
on public.categories for select
to anon, authenticated
using (true);

drop policy if exists "Public can read published articles" on public.articles;
create policy "Public can read published articles"
on public.articles for select
to anon, authenticated
using (status = 'published');

drop policy if exists "Public can read published article analysis"
  on public.article_analysis;
create policy "Public can read published article analysis"
on public.article_analysis for select
to anon, authenticated
using (
  exists (
    select 1
    from public.articles
    where articles.id = article_analysis.article_id
      and articles.status = 'published'
  )
);

drop policy if exists "Users can read own bookmarks" on public.bookmarks;
create policy "Users can read own bookmarks"
on public.bookmarks for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can create own bookmarks" on public.bookmarks;
create policy "Users can create own bookmarks"
on public.bookmarks for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update own bookmarks" on public.bookmarks;
create policy "Users can update own bookmarks"
on public.bookmarks for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete own bookmarks" on public.bookmarks;
create policy "Users can delete own bookmarks"
on public.bookmarks for delete
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can read own history"
  on public.reading_history;
create policy "Users can read own history"
on public.reading_history for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can create own history"
  on public.reading_history;
create policy "Users can create own history"
on public.reading_history for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update own history"
  on public.reading_history;
create policy "Users can update own history"
on public.reading_history for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete own history"
  on public.reading_history;
create policy "Users can delete own history"
on public.reading_history for delete
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can read own preferences"
  on public.user_preferences;
create policy "Users can read own preferences"
on public.user_preferences for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can create own preferences"
  on public.user_preferences;
create policy "Users can create own preferences"
on public.user_preferences for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update own preferences"
  on public.user_preferences;
create policy "Users can update own preferences"
on public.user_preferences for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete own preferences"
  on public.user_preferences;
create policy "Users can delete own preferences"
on public.user_preferences for delete
to authenticated
using ((select auth.uid()) = user_id);
