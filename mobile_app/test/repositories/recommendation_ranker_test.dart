import 'package:flutter_test/flutter_test.dart';
import 'package:mandiri_news_intelligence/models/trending_insight.dart';
import 'package:mandiri_news_intelligence/repositories/recommendation_ranker.dart';

import '../support/fake_news_repository.dart';

void main() {
  test('recommendation prioritizes preferred category and excludes reads', () {
    final ranked = RecommendationRanker.rankRecommended(
      fixtureArticles,
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
      fixtureArticles,
      const RecommendationSignals(topics: {'technology'}, keywords: {'ai'}),
      now: DateTime.utc(2026, 6, 14),
    );

    expect(ranked.first.id, 'article-technology');
  });

  test('trending insight exposes top topics and keywords', () {
    final insight = TrendingInsight.fromArticles(fixtureArticles);

    expect(insight.topics, containsAll(['Economy', 'Technology']));
    expect(insight.keywords, contains('ai'));
  });

  test(
    'guest or signed-in user without signals receives stable recency order',
    () {
      final ranked = RecommendationRanker.rankRecommended(
        [
          fixtureArticles.first,
          fixtureArticles.first,
          fixtureArticles.last,
        ],
        const RecommendationSignals(),
        now: DateTime.utc(2026, 6, 14),
      );

      expect(ranked.map((article) => article.id), [
        'article-economy',
        'article-technology',
      ]);
    },
  );

  test('all-read recommendation can fall back to unique trending articles', () {
    final recommended = RecommendationRanker.rankRecommended(
      fixtureArticles,
      const RecommendationSignals(
        readArticleIds: {'article-economy', 'article-technology'},
      ),
    );
    final trending = RecommendationRanker.rankTrending([
      ...fixtureArticles,
      fixtureArticles.first,
    ]);

    expect(recommended, isEmpty);
    expect(trending.map((article) => article.id).toSet().length, 2);
  });
}
