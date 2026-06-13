import 'dart:async';

import 'package:mandiri_news_intelligence/models/app_user.dart';
import 'package:mandiri_news_intelligence/models/article_with_analysis.dart';
import 'package:mandiri_news_intelligence/models/category.dart';
import 'package:mandiri_news_intelligence/models/reading_history_entry.dart';
import 'package:mandiri_news_intelligence/models/user_preference.dart';
import 'package:mandiri_news_intelligence/repositories/auth_repository.dart';
import 'package:mandiri_news_intelligence/repositories/bookmark_repository.dart';
import 'package:mandiri_news_intelligence/repositories/reading_history_repository.dart';
import 'package:mandiri_news_intelligence/repositories/user_preference_repository.dart';

import 'fake_news_repository.dart';

class FakeAuthRepository implements AuthRepository {
  FakeAuthRepository({AppUser? initialUser}) : _currentUser = initialUser;

  final _controller = StreamController<AppUser?>.broadcast();
  AppUser? _currentUser;

  int signInCalls = 0;
  int registerCalls = 0;
  int signOutCalls = 0;

  @override
  AppUser? get currentUser => _currentUser;

  @override
  Stream<AppUser?> get authStateChanges async* {
    yield _currentUser;
    yield* _controller.stream;
  }

  @override
  Future<AppUser> signIn({
    required String email,
    required String password,
  }) async {
    signInCalls++;
    _currentUser = AppUser(id: 'user-1', email: email.trim());
    _controller.add(_currentUser);
    return _currentUser!;
  }

  @override
  Future<RegistrationResult> register({
    required String email,
    required String password,
    String? name,
  }) async {
    registerCalls++;
    _currentUser = AppUser(id: 'user-1', email: email.trim());
    _controller.add(_currentUser);
    return RegistrationResult(
      user: _currentUser!,
      requiresEmailConfirmation: false,
    );
  }

  @override
  Future<void> signOut() async {
    signOutCalls++;
    _currentUser = null;
    _controller.add(null);
  }

  Future<void> dispose() => _controller.close();
}

class FakeBookmarkRepository implements BookmarkRepository {
  final Set<String> savedArticleIds = {};

  @override
  Future<void> addBookmark(String userId, String articleId) async {
    savedArticleIds.add(articleId);
  }

  @override
  Future<List<ArticleWithAnalysis>> getBookmarks(String userId) async {
    return testArticles
        .where((article) => savedArticleIds.contains(article.id))
        .toList(growable: false);
  }

  @override
  Future<int> getBookmarkCount(String userId) async => savedArticleIds.length;

  @override
  Future<bool> isBookmarked(String userId, String articleId) async {
    return savedArticleIds.contains(articleId);
  }

  @override
  Future<void> removeBookmark(String userId, String articleId) async {
    savedArticleIds.remove(articleId);
  }
}

class FakeReadingHistoryRepository implements ReadingHistoryRepository {
  final Map<String, DateTime> readAtByArticleId = {};

  @override
  Future<int> getArticlesReadCount(String userId) async {
    return readAtByArticleId.length;
  }

  @override
  Future<List<ReadingHistoryEntry>> getReadingHistory(String userId) async {
    return readAtByArticleId.entries
        .map((entry) {
          final article = testArticles.firstWhere(
            (item) => item.id == entry.key,
          );
          return ReadingHistoryEntry(
            id: 'history-${entry.key}',
            readAt: entry.value,
            article: article,
          );
        })
        .toList(growable: false);
  }

  @override
  Future<void> recordArticleRead(String userId, String articleId) async {
    readAtByArticleId[articleId] = DateTime.utc(2026, 6, 13);
  }
}

class FakeUserPreferenceRepository implements UserPreferenceRepository {
  FakeUserPreferenceRepository({List<Category>? categories})
    : categories = categories ?? testCategories;

  final List<Category> categories;
  String? selectedCategoryId;

  @override
  Future<UserPreference?> getPreference(String userId) async {
    final categoryId = selectedCategoryId;
    if (categoryId == null) {
      return null;
    }
    return UserPreference(
      id: 'preference-1',
      userId: userId,
      preferredCategory: categories.firstWhere(
        (category) => category.id == categoryId,
      ),
    );
  }

  @override
  Future<void> savePreferredCategory(String userId, String categoryId) async {
    selectedCategoryId = categoryId;
  }
}
