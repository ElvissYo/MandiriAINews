import 'package:flutter_test/flutter_test.dart';
import 'package:mandiri_news_intelligence/models/trending_insight.dart';
import 'package:mandiri_news_intelligence/repositories/recommendation_ranker.dart';

import '../support/fake_news_repository.dart';

void main() {
  test('recommendation prioritizes preferred category and excludes reads', () {
    final ranked = RecommendationRanker.rankRecommended(
      testArticles,
      const RecommendationSignals(
        preferredCategoryId: 'technology',
        readArticleIds: {'article-economy'},
      ),
      now: DateTime.utc(2026, 6, 14),
    );

    expect(ranked.map((article) => article.id), ['article-technology']);
  });

  test('history topic and keyword signals influence recommendation order', () {
    final ranked = RecommendationRanker.rankRecommended(
      testArticles,
      const RecommendationSignals(topics: {'technology'}, keywords: {'ai'}),
      now: DateTime.utc(2026, 6, 14),
    );

    expect(ranked.first.id, 'article-technology');
  });

  test('trending insight exposes top topics and keywords', () {
    final insight = TrendingInsight.fromArticles(testArticles);

    expect(insight.topics, containsAll(['Economy', 'Technology']));
    expect(insight.keywords, contains('ai'));
  });
}
