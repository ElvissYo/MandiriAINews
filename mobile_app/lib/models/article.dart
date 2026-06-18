class Article {
  const Article({
    required this.id,
    required this.title,
    required this.content,
    required this.url,
    required this.publishedAt,
    required this.status,
    this.imageUrl,
    this.sourceId,
    this.categoryId,
    this.canonicalUrl,
    this.contentIsSnippet = false,
    this.extractionMethod,
    this.extractionStatus,
  });

  final String id;
  final String title;
  final String content;
  final String url;
  final String? imageUrl;
  final String? sourceId;
  final String? categoryId;
  final String? canonicalUrl;
  final DateTime publishedAt;
  final String status;
  final bool contentIsSnippet;
  final String? extractionMethod;
  final String? extractionStatus;

  factory Article.fromMap(Map<String, dynamic> map) {
    return Article(
      id: map['id'] as String,
      title: _text(map['title'], fallback: 'Untitled article'),
      content: _text(map['content']),
      url: _text(map['url']),
      imageUrl: _nullableText(map['image_url']),
      sourceId: _nullableText(map['source_id']),
      categoryId: _nullableText(map['category_id']),
      canonicalUrl: _nullableText(map['canonical_url']),
      publishedAt:
          DateTime.tryParse(_text(map['published_at'])) ?? DateTime.now(),
      status: _text(map['status'], fallback: 'published'),
      contentIsSnippet: map['content_is_snippet'] == true,
      extractionMethod: _nullableText(map['extraction_method']),
      extractionStatus: _nullableText(map['extraction_status']),
    );
  }

  static String _text(Object? value, {String fallback = ''}) {
    final text = value?.toString().trim() ?? '';
    return text.isEmpty ? fallback : text;
  }

  static String? _nullableText(Object? value) {
    final text = value?.toString().trim() ?? '';
    return text.isEmpty ? null : text;
  }
}
