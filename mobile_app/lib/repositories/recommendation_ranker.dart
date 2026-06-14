import '../models/article_with_analysis.dart';

class RecommendationSignals {
  const RecommendationSignals({
    this.preferredCategoryId,
    this.categoryReadCounts = const {},
    this.topics = const {},
    this.keywords = const {},
    this.readArticleIds = const {},
  });

  final String? preferredCategoryId;
  final Map<String, int> categoryReadCounts;
  final Set<String> topics;
  final Set<String> keywords;
  final Set<String> readArticleIds;
}

class RecommendationRanker {
  const RecommendationRanker._();

  static List<ArticleWithAnalysis> rankRecommended(
    List<ArticleWithAnalysis> candidates,
    RecommendationSignals signals, {
    int limit = 10,
    DateTime? now,
  }) {
    final scored = candidates
        .where((article) => !signals.readArticleIds.contains(article.id))
        .map(
          (article) => (
            article: article,
            score: _recommendationScore(
              article,
              signals,
              now ?? DateTime.now().toUtc(),
            ),
          ),
        )
        .toList();
    scored.sort(_compareScoredArticles);
    return scored
        .take(limit)
        .map((item) => item.article)
        .toList(growable: false);
  }

  static List<ArticleWithAnalysis> rankTrending(
    List<ArticleWithAnalysis> candidates, {
    int limit = 10,
    DateTime? now,
  }) {
    final topicCounts = <String, int>{};
    final keywordCounts = <String, int>{};
    for (final article in candidates) {
      final topic = _normalize(article.topic);
      if (topic.isNotEmpty) {
        topicCounts.update(topic, (count) => count + 1, ifAbsent: () => 1);
      }
      for (final keyword in article.keywords.map(_normalize).toSet()) {
        if (keyword.isNotEmpty) {
          keywordCounts.update(
            keyword,
            (count) => count + 1,
            ifAbsent: () => 1,
          );
        }
      }
    }

    final referenceTime = now ?? DateTime.now().toUtc();
    final scored = candidates
        .map(
          (article) => (
            article: article,
            score:
                (topicCounts[_normalize(article.topic)] ?? 0) * 1.5 +
                article.keywords
                    .map(_normalize)
                    .toSet()
                    .fold<double>(
                      0,
                      (score, keyword) =>
                          score + (keywordCounts[keyword] ?? 0) * 0.2,
                    ) +
                _recencyScore(article.publishedAt, referenceTime),
          ),
        )
        .toList();
    scored.sort(_compareScoredArticles);
    return scored
        .take(limit)
        .map((item) => item.article)
        .toList(growable: false);
  }

  static double _recommendationScore(
    ArticleWithAnalysis article,
    RecommendationSignals signals,
    DateTime now,
  ) {
    var score = _recencyScore(article.publishedAt, now);
    final categoryId = article.article.categoryId;
    if (categoryId != null) {
      if (categoryId == signals.preferredCategoryId) {
        score += 6;
      }
      score += (signals.categoryReadCounts[categoryId] ?? 0) * 2;
    }
    if (signals.topics.contains(_normalize(article.topic))) {
      score += 2.5;
    }
    final keywordMatches = article.keywords
        .map(_normalize)
        .where(signals.keywords.contains)
        .toSet()
        .length;
    score += keywordMatches * 1.25;
    return score;
  }

  static double _recencyScore(DateTime publishedAt, DateTime now) {
    final age = now.difference(publishedAt.toUtc()).inHours;
    final boundedHours = age.clamp(0, 24 * 30);
    return 1 - boundedHours / (24 * 30);
  }

  static int _compareScoredArticles(
    ({ArticleWithAnalysis article, double score}) left,
    ({ArticleWithAnalysis article, double score}) right,
  ) {
    final scoreComparison = right.score.compareTo(left.score);
    if (scoreComparison != 0) {
      return scoreComparison;
    }
    return right.article.publishedAt.compareTo(left.article.publishedAt);
  }

  static String _normalize(String value) => value.trim().toLowerCase();
}
