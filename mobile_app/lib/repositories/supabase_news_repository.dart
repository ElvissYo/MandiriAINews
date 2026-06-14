import 'dart:math';

import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/article_with_analysis.dart';
import '../models/category.dart';
import 'article_query.dart';
import 'news_repository.dart';
import 'recommendation_ranker.dart';

class SupabaseNewsRepository implements NewsRepository {
  SupabaseNewsRepository({required SupabaseClient client}) : _client = client;

  final SupabaseClient _client;

  @override
  Future<List<ArticleWithAnalysis>> getLatestArticles({int limit = 20}) async {
    final rows = await _client
        .from('articles')
        .select(articleSelect)
        .eq('status', 'published')
        .order('published_at', ascending: false)
        .limit(limit);
    return _mapArticles(rows);
  }

  @override
  Future<ArticleWithAnalysis?> getArticleById(String articleId) async {
    final row = await _client
        .from('articles')
        .select(articleSelect)
        .eq('id', articleId)
        .eq('status', 'published')
        .maybeSingle();
    return row == null ? null : ArticleWithAnalysis.fromMap(row);
  }

  @override
  Future<List<ArticleWithAnalysis>> getArticlesByCategory(
    String categoryId, {
    int limit = 20,
  }) async {
    final rows = await _client
        .from('articles')
        .select(articleSelect)
        .eq('status', 'published')
        .eq('category_id', categoryId)
        .order('published_at', ascending: false)
        .limit(limit);
    return _mapArticles(rows);
  }

  @override
  Future<List<ArticleWithAnalysis>> searchArticles(
    String query, {
    int limit = 20,
  }) async {
    final normalized = query.trim();
    if (normalized.isEmpty) {
      return getLatestArticles(limit: limit);
    }

    final pattern = '%$normalized%';
    final keywordCandidates = <String>{
      normalized.toLowerCase(),
      ...normalized
          .toLowerCase()
          .split(RegExp(r'\s+'))
          .where((word) => word.length >= 3),
    }.toList(growable: false);

    final matches = await Future.wait<Set<String>>([
      _articleIdsMatchingText('title', pattern, limit),
      _articleIdsMatchingText('content', pattern, limit),
      _analysisIdsMatchingText('summary', pattern, limit),
      _analysisIdsMatchingText('topic', pattern, limit),
      _analysisIdsMatchingKeywords(keywordCandidates, limit),
    ]);

    final articleIds = matches.expand((ids) => ids).toSet().toList();
    if (articleIds.isEmpty) {
      return const [];
    }

    final rows = await _client
        .from('articles')
        .select(articleSelect)
        .eq('status', 'published')
        .inFilter('id', articleIds)
        .order('published_at', ascending: false)
        .limit(limit);
    return _mapArticles(rows);
  }

  @override
  Future<ArticleWithAnalysis?> getFeaturedArticle() async {
    final row = await _client
        .from('articles')
        .select(articleSelect)
        .eq('status', 'published')
        .order('published_at', ascending: false)
        .limit(1)
        .maybeSingle();
    return row == null ? null : ArticleWithAnalysis.fromMap(row);
  }

  @override
  Future<List<Category>> getCategories() async {
    final rows = await _client
        .from('categories')
        .select('id, name, description')
        .order('name', ascending: true);
    return rows
        .map((row) => Category.fromMap(Map<String, dynamic>.from(row)))
        .toList(growable: false);
  }

  @override
  Future<List<ArticleWithAnalysis>> getRecommendedArticles({
    String? userId,
    int limit = 10,
  }) async {
    if (userId == null) {
      return getTrendingArticles(limit: limit);
    }

    try {
      final results = await Future.wait<dynamic>([
        _client
            .from('reading_history')
            .select('article_id, articles!inner($articleSelect)')
            .eq('user_id', userId)
            .order('read_at', ascending: false)
            .limit(50),
        _client
            .from('user_preferences')
            .select('preferred_category_id')
            .eq('user_id', userId)
            .maybeSingle(),
        getLatestArticles(limit: max(limit * 6, 40)),
      ]);

      final historyRows = results[0] as List<dynamic>;
      final preference = results[1] as Map<String, dynamic>?;
      final candidates = results[2] as List<ArticleWithAnalysis>;
      final historyArticles = historyRows
          .map((row) => (row as Map<String, dynamic>)['articles'])
          .whereType<Map>()
          .map(
            (row) =>
                ArticleWithAnalysis.fromMap(Map<String, dynamic>.from(row)),
          )
          .toList(growable: false);

      final categoryReadCounts = <String, int>{};
      final topics = <String>{};
      final keywords = <String>{};
      for (final article in historyArticles) {
        final categoryId = article.article.categoryId;
        if (categoryId != null) {
          categoryReadCounts.update(
            categoryId,
            (count) => count + 1,
            ifAbsent: () => 1,
          );
        }
        topics.add(article.topic.toLowerCase());
        keywords.addAll(article.keywords.map((item) => item.toLowerCase()));
      }

      final ranked = RecommendationRanker.rankRecommended(
        candidates,
        RecommendationSignals(
          preferredCategoryId: preference?['preferred_category_id']?.toString(),
          categoryReadCounts: categoryReadCounts,
          topics: topics,
          keywords: keywords,
          readArticleIds: historyArticles.map((article) => article.id).toSet(),
        ),
        limit: limit,
      );
      return ranked.isEmpty
          ? RecommendationRanker.rankTrending(candidates, limit: limit)
          : ranked;
    } catch (_) {
      return getTrendingArticles(limit: limit);
    }
  }

  @override
  Future<List<ArticleWithAnalysis>> getTrendingArticles({
    int limit = 10,
  }) async {
    final candidates = await getLatestArticles(limit: max(limit * 5, 30));
    return RecommendationRanker.rankTrending(candidates, limit: limit);
  }

  Future<Set<String>> _articleIdsMatchingText(
    String column,
    String pattern,
    int limit,
  ) async {
    final rows = await _client
        .from('articles')
        .select('id')
        .eq('status', 'published')
        .ilike(column, pattern)
        .limit(limit);
    return _ids(rows, 'id');
  }

  Future<Set<String>> _analysisIdsMatchingText(
    String column,
    String pattern,
    int limit,
  ) async {
    final rows = await _client
        .from('article_analysis')
        .select('article_id')
        .ilike(column, pattern)
        .limit(limit);
    return _ids(rows, 'article_id');
  }

  Future<Set<String>> _analysisIdsMatchingKeywords(
    List<String> candidates,
    int limit,
  ) async {
    if (candidates.isEmpty) {
      return const {};
    }
    final rows = await _client
        .from('article_analysis')
        .select('article_id')
        .overlaps('keywords', candidates)
        .limit(limit);
    return _ids(rows, 'article_id');
  }

  static Set<String> _ids(List<dynamic> rows, String column) {
    return rows
        .map((row) => (row as Map<String, dynamic>)[column]?.toString())
        .whereType<String>()
        .where((id) => id.isNotEmpty)
        .toSet();
  }

  static List<ArticleWithAnalysis> _mapArticles(List<dynamic> rows) {
    return rows
        .map(
          (row) => ArticleWithAnalysis.fromMap(
            Map<String, dynamic>.from(row as Map),
          ),
        )
        .toList(growable: false);
  }
}
