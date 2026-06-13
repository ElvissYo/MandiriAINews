import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/category.dart';
import '../models/user_preference.dart';

abstract interface class UserPreferenceRepository {
  Future<UserPreference?> getPreference(String userId);

  Future<void> savePreferredCategory(String userId, String categoryId);
}

class SupabaseUserPreferenceRepository implements UserPreferenceRepository {
  SupabaseUserPreferenceRepository({required SupabaseClient client})
    : _client = client;

  final SupabaseClient _client;

  @override
  Future<UserPreference?> getPreference(String userId) async {
    final row = await _client
        .from('user_preferences')
        .select('id, user_id, categories(id, name, description)')
        .eq('user_id', userId)
        .maybeSingle();
    if (row == null) {
      return null;
    }
    final categoryMap = row['categories'];
    return UserPreference(
      id: row['id'] as String,
      userId: row['user_id'] as String,
      preferredCategory: categoryMap is Map
          ? Category.fromMap(Map<String, dynamic>.from(categoryMap))
          : null,
    );
  }

  @override
  Future<void> savePreferredCategory(String userId, String categoryId) async {
    await _client.from('user_preferences').upsert({
      'user_id': userId,
      'preferred_category_id': categoryId,
    }, onConflict: 'user_id');
  }
}
