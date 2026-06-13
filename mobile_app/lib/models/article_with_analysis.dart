import 'article.dart';
import 'article_analysis.dart';
import 'category.dart';
import 'source.dart';

class ArticleWithAnalysis {
  const ArticleWithAnalysis({
    required this.article,
    this.analysis,
    this.category,
    this.source,
  });

  final Article article;
  final ArticleAnalysis? analysis;
  final Category? category;
  final Source? source;

  String get id => article.id;
  String get title => article.title;
  String get url => article.url;
  String? get imageUrl => article.imageUrl;
  DateTime get publishedAt => article.publishedAt;

  String get content {
    final value = article.content.trim();
    return value.isEmpty ? 'Full article content is not available.' : value;
  }

  String get summary {
    final value = analysis?.summary?.trim() ?? '';
    return value.isEmpty ? 'Summary is not available.' : value;
  }

  String get sentiment {
    final value = analysis?.sentiment?.trim().toLowerCase() ?? '';
    return switch (value) {
      'positive' || 'negative' || 'neutral' => value,
      _ => 'neutral',
    };
  }

  double? get sentimentScore => analysis?.sentimentScore;

  String get topic {
    final value = analysis?.topic?.trim() ?? '';
    return value.isEmpty ? categoryName : value;
  }

  List<String> get keywords => analysis?.keywords ?? const [];

  String get categoryName {
    final value = category?.name.trim() ?? '';
    return value.isEmpty ? 'Uncategorized' : value;
  }

  String get sourceName {
    final value = source?.name.trim() ?? '';
    return value.isEmpty ? 'Unknown source' : value;
  }

  factory ArticleWithAnalysis.fromMap(Map<String, dynamic> map) {
    return ArticleWithAnalysis(
      article: Article.fromMap(map),
      source: _relatedMap(map['sources'], Source.fromMap),
      category: _relatedMap(map['categories'], Category.fromMap),
      analysis: _relatedMap(map['article_analysis'], ArticleAnalysis.fromMap),
    );
  }

  static T? _relatedMap<T>(
    Object? raw,
    T Function(Map<String, dynamic>) parser,
  ) {
    if (raw is Map<String, dynamic>) {
      return parser(raw);
    }
    if (raw is Map) {
      return parser(Map<String, dynamic>.from(raw));
    }
    if (raw is List && raw.isNotEmpty) {
      final first = raw.first;
      if (first is Map<String, dynamic>) {
        return parser(first);
      }
      if (first is Map) {
        return parser(Map<String, dynamic>.from(first));
      }
    }
    return null;
  }
}
