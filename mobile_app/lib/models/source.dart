class Source {
  const Source({required this.id, required this.name, this.url, this.country});

  final String id;
  final String name;
  final String? url;
  final String? country;

  factory Source.fromMap(Map<String, dynamic> map) {
    return Source(
      id: map['id'] as String,
      name: _text(map['name'], fallback: 'Unknown source'),
      url: _nullableText(map['url']),
      country: _nullableText(map['country']),
    );
  }

  static String _text(Object? value, {required String fallback}) {
    final text = value?.toString().trim() ?? '';
    return text.isEmpty ? fallback : text;
  }

  static String? _nullableText(Object? value) {
    final text = value?.toString().trim() ?? '';
    return text.isEmpty ? null : text;
  }
}
