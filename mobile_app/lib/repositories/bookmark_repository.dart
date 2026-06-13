import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/article_with_analysis.dart';
import 'article_query.dart';

abstract interface class BookmarkRepository {
  Future<List<ArticleWithAnalysis>> getBookmarks(String userId);

  Future<bool> isBookmarked(String userId, String articleId);

  Future<void> addBookmark(String userId, String articleId);

  Future<void> removeBookmark(String userId, String articleId);

  Future<int> getBookmarkCount(String userId);
}

class SupabaseBookmarkRepository implements BookmarkRepository {
  SupabaseBookmarkRepository({required SupabaseClient client})
    : _client = client;

  final SupabaseClient _client;

  @override
  Future<List<ArticleWithAnalysis>> getBookmarks(String userId) async {
    final rows = await _client
        .from('bookmarks')
        .select('created_at, articles!inner($articleSelect)')
        .eq('user_id', userId)
        .order('created_at', ascending: false);
    return rows
        .map(
          (row) => ArticleWithAnalysis.fromMap(
            Map<String, dynamic>.from(row['articles'] as Map),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<bool> isBookmarked(String userId, String articleId) async {
    final row = await _client
        .from('bookmarks')
        .select('id')
        .eq('user_id', userId)
        .eq('article_id', articleId)
        .maybeSingle();
    return row != null;
  }

  @override
  Future<void> addBookmark(String userId, String articleId) async {
    await _client.from('bookmarks').upsert({
      'user_id': userId,
      'article_id': articleId,
    }, onConflict: 'user_id,article_id');
  }

  @override
  Future<void> removeBookmark(String userId, String articleId) async {
    await _client
        .from('bookmarks')
        .delete()
        .eq('user_id', userId)
        .eq('article_id', articleId);
  }

  @override
  Future<int> getBookmarkCount(String userId) {
    return _client.from('bookmarks').count().eq('user_id', userId);
  }
}
