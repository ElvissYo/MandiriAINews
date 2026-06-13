class Category {
  const Category({required this.id, required this.name, this.description});

  final String id;
  final String name;
  final String? description;

  factory Category.fromMap(Map<String, dynamic> map) {
    final description = map['description']?.toString().trim();
    return Category(
      id: map['id'] as String,
      name: map['name']?.toString().trim() ?? 'Uncategorized',
      description: description == null || description.isEmpty
          ? null
          : description,
    );
  }
}
