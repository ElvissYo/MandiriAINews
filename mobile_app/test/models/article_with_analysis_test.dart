import 'package:flutter_test/flutter_test.dart';
import 'package:mandiri_news_intelligence/models/article_with_analysis.dart';

void main() {
  test('maps joined Supabase response and applies safe fallbacks', () {
    final article = ArticleWithAnalysis.fromMap({
      'id': 'article-1',
      'title': 'A seeded article',
      'content': '',
      'url': 'https://example.com/article',
      'canonical_url': 'https://example.com/canonical-article',
      'image_url': null,
      'source_id': 'source-1',
      'category_id': 'category-1',
      'published_at': '2026-06-13T02:30:00Z',
      'status': 'published',
      'content_is_snippet': true,
      'extraction_method': 'rss_snippet',
      'extraction_status': 'snippet',
      'sources': {
        'id': 'source-1',
        'name': 'Demo Source',
        'url': 'https://example.com',
        'country': 'Indonesia',
      },
      'categories': {
        'id': 'category-1',
        'name': 'Economy',
        'description': null,
      },
      'article_analysis': [
        {
          'id': 'analysis-1',
          'article_id': 'article-1',
          'summary': null,
          'sentiment': null,
          'sentiment_score': '0.25',
          'topic': null,
          'keywords': null,
        },
      ],
    });

    expect(article.sourceName, 'Demo Source');
    expect(article.categoryName, 'Economy');
    expect(article.summary, 'Summary is not available.');
    expect(article.sentiment, 'neutral');
    expect(article.sentimentScore, 0.25);
    expect(article.topic, 'Economy');
    expect(article.keywords, isEmpty);
    expect(article.content, 'Full article content is not available.');
    expect(article.contentIsSnippet, isTrue);
    expect(
      article.article.canonicalUrl,
      'https://example.com/canonical-article',
    );
    expect(article.article.extractionMethod, 'rss_snippet');
    expect(article.article.extractionStatus, 'snippet');
  });
}
