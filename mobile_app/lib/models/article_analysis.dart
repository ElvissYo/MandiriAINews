class ArticleAnalysis {
  const ArticleAnalysis({
    required this.id,
    required this.articleId,
    required this.keywords,
    this.summary,
    this.sentiment,
    this.sentimentScore,
    this.topic,
  });

  final String id;
  final String articleId;
  final String? summary;
  final String? sentiment;
  final double? sentimentScore;
  final String? topic;
  final List<String> keywords;

  factory ArticleAnalysis.fromMap(Map<String, dynamic> map) {
    return ArticleAnalysis(
      id: map['id'] as String,
      articleId: map['article_id'] as String,
      summary: _nullableText(map['summary']),
      sentiment: _nullableText(map['sentiment']),
      sentimentScore: _toDouble(map['sentiment_score']),
      topic: _nullableText(map['topic']),
      keywords: _keywords(map['keywords']),
    );
  }

  static String? _nullableText(Object? value) {
    final text = value?.toString().trim() ?? '';
    return text.isEmpty ? null : text;
  }

  static double? _toDouble(Object? value) {
    if (value is num) {
      return value.toDouble();
    }
    return double.tryParse(value?.toString() ?? '');
  }

  static List<String> _keywords(Object? value) {
    if (value is! List) {
      return const [];
    }
    return value
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }
}
