import 'article_with_analysis.dart';

class ReadingHistoryEntry {
  const ReadingHistoryEntry({
    required this.id,
    required this.readAt,
    required this.article,
  });

  final String id;
  final DateTime readAt;
  final ArticleWithAnalysis article;
}
