const articleSelect = '''
  id,
  title,
  content,
  url,
  image_url,
  source_id,
  category_id,
  published_at,
  status,
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
