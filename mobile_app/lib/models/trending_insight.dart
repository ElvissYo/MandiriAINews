import 'article_with_analysis.dart';

class TrendingInsight {
  const TrendingInsight({required this.topics, required this.keywords});

  final List<String> topics;
  final List<String> keywords;

  factory TrendingInsight.fromArticles(
    Iterable<ArticleWithAnalysis> articles, {
    int limit = 5,
  }) {
    final topicCounts = <String, int>{};
    final topicLabels = <String, String>{};
    final keywordCounts = <String, int>{};
    for (final article in articles) {
      final topic = article.topic.trim();
      final topicKey = topic.toLowerCase();
      if (topicKey.isNotEmpty) {
        topicLabels.putIfAbsent(topicKey, () => topic);
        topicCounts.update(topicKey, (count) => count + 1, ifAbsent: () => 1);
      }
      for (final keyword in article.keywords) {
        final normalized = keyword.trim().toLowerCase();
        if (normalized.isNotEmpty) {
          keywordCounts.update(
            normalized,
            (count) => count + 1,
            ifAbsent: () => 1,
          );
        }
      }
    }

    return TrendingInsight(
      topics: _topEntries(
        topicCounts,
        limit,
      ).map((key) => topicLabels[key] ?? key).toList(growable: false),
      keywords: _topEntries(keywordCounts, limit),
    );
  }

  static List<String> _topEntries(Map<String, int> counts, int limit) {
    final entries = counts.entries.toList()
      ..sort((left, right) {
        final countComparison = right.value.compareTo(left.value);
        return countComparison != 0
            ? countComparison
            : left.key.compareTo(right.key);
      });
    return entries
        .take(limit)
        .map((entry) => entry.key)
        .toList(growable: false);
  }
}
