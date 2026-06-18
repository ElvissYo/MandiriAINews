-- Mandiri News Intelligence App
-- Run this file before rls_policies.sql and seed_data.sql.

create extension if not exists pgcrypto;

do $$
begin
  begin
    create extension if not exists vector;
  exception when others then
    raise notice 'pgvector extension is unavailable; semantic search tables are skipped: %', sqlerrm;
  end;
end $$;

create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  url text,
  country text,
  created_at timestamptz not null default now(),
  constraint sources_name_unique unique (name)
);

create table if not exists public.categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  created_at timestamptz not null default now(),
  constraint categories_name_unique unique (name)
);

create table if not exists public.articles (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  content text not null default '',
  url text not null,
  image_url text,
  source_id uuid references public.sources(id) on delete set null,
  category_id uuid references public.categories(id) on delete set null,
  published_at timestamptz not null,
  status text not null default 'published',
  content_is_snippet boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint articles_url_unique unique (url),
  constraint articles_status_check
    check (status in ('draft', 'published', 'archived'))
);

alter table public.articles
  add column if not exists content_is_snippet boolean not null default false;

create table if not exists public.article_analysis (
  id uuid primary key default gen_random_uuid(),
  article_id uuid not null references public.articles(id) on delete cascade,
  summary text,
  sentiment text,
  sentiment_score numeric(6, 5),
  topic text,
  keywords text[] not null default '{}',
  created_at timestamptz not null default now(),
  constraint article_analysis_article_unique unique (article_id),
  constraint article_analysis_sentiment_check
    check (sentiment is null or sentiment in ('positive', 'neutral', 'negative')),
  constraint article_analysis_score_check
    check (
      sentiment_score is null
      or sentiment_score between -1 and 1
    )
);

do $$
begin
  if exists (select 1 from pg_extension where extname = 'vector') then
    execute '
      create table if not exists public.article_embeddings (
        id uuid primary key default gen_random_uuid(),
        article_id uuid not null references public.articles(id) on delete cascade,
        embedding_text text not null,
        embedding vector(384) not null,
        embedding_provider text not null default ''unknown'',
        embedding_dimensions integer not null default 384,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        constraint article_embeddings_article_unique unique (article_id),
        constraint article_embeddings_dimensions_check
          check (embedding_dimensions = 384)
      )';
  end if;
end $$;

create table if not exists public.bookmarks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  article_id uuid not null references public.articles(id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint bookmarks_user_article_unique unique (user_id, article_id)
);

create table if not exists public.reading_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  article_id uuid not null references public.articles(id) on delete cascade,
  read_at timestamptz not null default now(),
  constraint reading_history_user_article_unique unique (user_id, article_id)
);

create table if not exists public.user_preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  preferred_category_id uuid references public.categories(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint user_preferences_user_unique unique (user_id)
);

create table if not exists public.pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null,
  completed_at timestamptz not null,
  source text not null,
  extracted integer not null default 0,
  cleaned integer not null default 0,
  inserted integer not null default 0,
  skipped_duplicates integer not null default 0,
  failed integer not null default 0,
  status text not null,
  error_message text,
  created_at timestamptz not null default now(),
  constraint pipeline_runs_counts_check check (
    extracted >= 0
    and cleaned >= 0
    and inserted >= 0
    and skipped_duplicates >= 0
    and failed >= 0
  ),
    constraint pipeline_runs_status_check
      check (status in ('success', 'partial', 'failed', 'no_data'))
  );

alter table public.pipeline_runs
  drop constraint if exists pipeline_runs_status_check;
alter table public.pipeline_runs
  add constraint pipeline_runs_status_check
  check (status in ('success', 'partial', 'failed', 'no_data'));

create index if not exists articles_published_at_idx
  on public.articles (published_at desc);
create index if not exists articles_status_idx
  on public.articles (status);
create index if not exists articles_category_id_idx
  on public.articles (category_id);
create index if not exists articles_source_id_idx
  on public.articles (source_id);
create index if not exists article_analysis_topic_idx
  on public.article_analysis (topic);
create index if not exists article_analysis_keywords_gin_idx
  on public.article_analysis using gin (keywords);
do $$
begin
  if to_regclass('public.article_embeddings') is not null then
    execute '
      create index if not exists article_embeddings_article_id_idx
      on public.article_embeddings (article_id)';
    execute '
      create index if not exists article_embeddings_vector_idx
      on public.article_embeddings
      using ivfflat (embedding vector_cosine_ops)
      with (lists = 64)';
  end if;
end $$;
create index if not exists bookmarks_user_id_idx
  on public.bookmarks (user_id);
create index if not exists reading_history_user_read_at_idx
  on public.reading_history (user_id, read_at desc);
create index if not exists pipeline_runs_started_at_idx
  on public.pipeline_runs (started_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists articles_set_updated_at on public.articles;
create trigger articles_set_updated_at
before update on public.articles
for each row execute function public.set_updated_at();

drop trigger if exists user_preferences_set_updated_at
  on public.user_preferences;
create trigger user_preferences_set_updated_at
before update on public.user_preferences
for each row execute function public.set_updated_at();

do $$
begin
  if to_regclass('public.article_embeddings') is not null then
    execute 'drop trigger if exists article_embeddings_set_updated_at
      on public.article_embeddings';
    execute 'create trigger article_embeddings_set_updated_at
      before update on public.article_embeddings
      for each row execute function public.set_updated_at()';
  end if;
end $$;

drop function if exists public.match_articles_by_embedding(text, integer);
drop function if exists public.match_articles_by_embedding(text, integer, text);

create or replace function public.match_articles_by_embedding(
  query_embedding text,
  match_count integer default 20,
  query_provider text default 'hash'
)
returns table(article_id uuid, similarity double precision)
language plpgsql
stable
security invoker
set search_path = ''
as $$
declare
  vector_type_oid oid;
  vector_type text;
  vector_operator_schema text;
begin
  if query_embedding is null or btrim(query_embedding) = '' then
    return;
  end if;

  select pg_type.oid,
         format('%I.%I', namespace.nspname, pg_type.typname)
    into vector_type_oid,
         vector_type
    from pg_catalog.pg_type
    join pg_catalog.pg_namespace namespace
      on namespace.oid = pg_type.typnamespace
   where pg_type.typname = 'vector'
   order by case namespace.nspname
      when 'extensions' then 0
      when 'public' then 1
      else 2
   end
   limit 1;

  if vector_type is null then
    return;
  end if;

  select format('%I', namespace.nspname)
    into vector_operator_schema
    from pg_catalog.pg_operator op
    join pg_catalog.pg_namespace namespace
      on namespace.oid = op.oprnamespace
   where op.oprname = '<=>'
     and op.oprleft = vector_type_oid
     and op.oprright = vector_type_oid
   order by case namespace.nspname
      when 'extensions' then 0
      when 'public' then 1
      else 2
   end
   limit 1;

  if vector_operator_schema is null then
    return;
  end if;

  return query execute format(
    'select e.article_id,
            1 - (e.embedding operator(%s.<=>) $1::%s) as similarity
       from public.article_embeddings e
       join public.articles a on a.id = e.article_id
      where a.status = ''published''
        and ($3 is null or btrim($3) = '''' or e.embedding_provider = $3)
      order by e.embedding operator(%s.<=>) $1::%s
      limit least(greatest($2, 1), 50)',
    vector_operator_schema,
    vector_type,
    vector_operator_schema,
    vector_type
  )
    using query_embedding, match_count, query_provider;
exception
  when undefined_table
    or undefined_object
    or invalid_text_representation
    or invalid_parameter_value then
    return;
end;
$$;

grant execute on function public.match_articles_by_embedding(text, integer, text)
  to anon, authenticated;

comment on table public.articles is
  'Normalized news articles loaded only by trusted backend processes.';
comment on table public.article_analysis is
  'NLP outputs generated by the Python data pipeline.';
comment on table public.reading_history is
  'One row per user/article; upsert read_at when an article is reopened.';
comment on table public.pipeline_runs is
  'Backend-only observability records for scheduled and manual ETL runs.';
comment on function public.match_articles_by_embedding(text, integer, text) is
  'Optional semantic article match RPC. Filters by embedding provider and returns no rows when pgvector is unavailable.';

do $$
begin
  if to_regclass('public.article_embeddings') is not null then
    execute 'comment on table public.article_embeddings is
      ''Optional pgvector embeddings generated by trusted backend AI providers.''';
  end if;
end $$;
