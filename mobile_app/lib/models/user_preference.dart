import 'category.dart';

class UserPreference {
  const UserPreference({
    required this.id,
    required this.userId,
    this.preferredCategory,
  });

  final String id;
  final String userId;
  final Category? preferredCategory;
}
