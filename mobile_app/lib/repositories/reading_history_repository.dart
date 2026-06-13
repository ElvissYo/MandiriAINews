import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/article_with_analysis.dart';
import '../models/reading_history_entry.dart';
import 'article_query.dart';

abstract interface class ReadingHistoryRepository {
  Future<List<ReadingHistoryEntry>> getReadingHistory(String userId);

  Future<void> recordArticleRead(String userId, String articleId);

  Future<int> getArticlesReadCount(String userId);
}

class SupabaseReadingHistoryRepository implements ReadingHistoryRepository {
  SupabaseReadingHistoryRepository({required SupabaseClient client})
    : _client = client;

  final SupabaseClient _client;

  @override
  Future<List<ReadingHistoryEntry>> getReadingHistory(String userId) async {
    final rows = await _client
        .from('reading_history')
        .select('id, read_at, articles!inner($articleSelect)')
        .eq('user_id', userId)
        .order('read_at', ascending: false);
    return rows
        .map(
          (row) => ReadingHistoryEntry(
            id: row['id'] as String,
            readAt:
                DateTime.tryParse(row['read_at']?.toString() ?? '') ??
                DateTime.now(),
            article: ArticleWithAnalysis.fromMap(
              Map<String, dynamic>.from(row['articles'] as Map),
            ),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<void> recordArticleRead(String userId, String articleId) async {
    await _client.from('reading_history').upsert({
      'user_id': userId,
      'article_id': articleId,
      'read_at': DateTime.now().toUtc().toIso8601String(),
    }, onConflict: 'user_id,article_id');
  }

  @override
  Future<int> getArticlesReadCount(String userId) {
    return _client.from('reading_history').count().eq('user_id', userId);
  }
}
