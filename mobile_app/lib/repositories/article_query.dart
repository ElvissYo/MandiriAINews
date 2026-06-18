const articleSelect = '''
  id,
  title,
  content,
  url,
  canonical_url,
  image_url,
  source_id,
  category_id,
  published_at,
  status,
  content_is_snippet,
  extraction_method,
  extraction_status,
  sources (
    id,
    name,
    url,
    country
  ),
  categories (
    id,
    name,
    description
  ),
  article_analysis (
    id,
    article_id,
    summary,
    sentiment,
    sentiment_score,
    topic,
    keywords
  )
''';
