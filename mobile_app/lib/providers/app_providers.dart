import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/app_user.dart';
import '../models/article_with_analysis.dart';
import '../models/category.dart';
import '../models/profile_stats.dart';
import '../models/reading_history_entry.dart';
import '../models/trending_insight.dart';
import '../models/user_preference.dart';
import '../repositories/auth_repository.dart';
import '../repositories/bookmark_repository.dart';
import '../repositories/news_repository.dart';
import '../repositories/reading_history_repository.dart';
import '../repositories/supabase_news_repository.dart';
import '../repositories/user_preference_repository.dart';
import '../services/supabase_service.dart';

final supabaseServiceProvider = Provider<SupabaseService>(
  (ref) => const SupabaseService(),
);

final newsRepositoryProvider = Provider<NewsRepository>((ref) {
  return SupabaseNewsRepository(
    client: ref.watch(supabaseServiceProvider).client,
  );
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return SupabaseAuthRepository(
    client: ref.watch(supabaseServiceProvider).client,
  );
});

final bookmarkRepositoryProvider = Provider<BookmarkRepository>((ref) {
  return SupabaseBookmarkRepository(
    client: ref.watch(supabaseServiceProvider).client,
  );
});

final readingHistoryRepositoryProvider = Provider<ReadingHistoryRepository>((
  ref,
) {
  return SupabaseReadingHistoryRepository(
    client: ref.watch(supabaseServiceProvider).client,
  );
});

final userPreferenceRepositoryProvider = Provider<UserPreferenceRepository>((
  ref,
) {
  return SupabaseUserPreferenceRepository(
    client: ref.watch(supabaseServiceProvider).client,
  );
});

final authStateProvider = StreamProvider<AppUser?>((ref) {
  return ref.watch(authRepositoryProvider).authStateChanges;
});

final currentUserProvider = Provider<AppUser?>((ref) {
  final repository = ref.watch(authRepositoryProvider);
  return ref
      .watch(authStateProvider)
      .when(
        data: (user) => user ?? repository.currentUser,
        loading: () => repository.currentUser,
        error: (_, _) => repository.currentUser,
      );
});

class AuthController extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> signIn({required String email, required String password}) async {
    state = const AsyncLoading();
    try {
      await ref
          .read(authRepositoryProvider)
          .signIn(email: email, password: password);
      state = const AsyncData(null);
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }

  Future<RegistrationResult> register({
    required String email,
    required String password,
    String? name,
  }) async {
    state = const AsyncLoading();
    try {
      final result = await ref
          .read(authRepositoryProvider)
          .register(email: email, password: password, name: name);
      state = const AsyncData(null);
      return result;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }

  Future<void> signOut() async {
    state = const AsyncLoading();
    try {
      await ref.read(authRepositoryProvider).signOut();
      state = const AsyncData(null);
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }
}

final authControllerProvider = AsyncNotifierProvider<AuthController, void>(
  AuthController.new,
);

class SelectedCategoryNotifier extends Notifier<String?> {
  @override
  String? build() => null;

  void select(String? categoryId) {
    state = categoryId;
  }
}

final selectedCategoryProvider =
    NotifierProvider<SelectedCategoryNotifier, String?>(
      SelectedCategoryNotifier.new,
    );

final latestArticlesProvider =
    FutureProvider.autoDispose<List<ArticleWithAnalysis>>((ref) {
      final repository = ref.watch(newsRepositoryProvider);
      final categoryId = ref.watch(selectedCategoryProvider);
      if (categoryId == null) {
        return repository.getLatestArticles();
      }
      return repository.getArticlesByCategory(categoryId);
    });

final featuredArticleProvider =
    FutureProvider.autoDispose<ArticleWithAnalysis?>((ref) {
      return ref.watch(newsRepositoryProvider).getFeaturedArticle();
    });

final categoriesProvider = FutureProvider.autoDispose<List<Category>>((ref) {
  return ref.watch(newsRepositoryProvider).getCategories();
});

final recommendedArticlesProvider =
    FutureProvider.autoDispose<List<ArticleWithAnalysis>>((ref) {
      final user = ref.watch(currentUserProvider);
      return ref
          .watch(newsRepositoryProvider)
          .getRecommendedArticles(userId: user?.id);
    });

final trendingArticlesProvider =
    FutureProvider.autoDispose<List<ArticleWithAnalysis>>((ref) {
      return ref.watch(newsRepositoryProvider).getTrendingArticles();
    });

final trendingInsightProvider = FutureProvider.autoDispose<TrendingInsight>((
  ref,
) async {
  final articles = await ref.watch(trendingArticlesProvider.future);
  return TrendingInsight.fromArticles(articles);
});

final articleDetailProvider = FutureProvider.autoDispose
    .family<ArticleWithAnalysis?, String>((ref, articleId) {
      return ref.watch(newsRepositoryProvider).getArticleById(articleId);
    });

final searchArticlesProvider = FutureProvider.autoDispose
    .family<List<ArticleWithAnalysis>, String>((ref, query) {
      return ref.watch(newsRepositoryProvider).searchArticles(query);
    });

typedef RelatedArticleRequest = ({
  String articleId,
  String? categoryId,
  String topic,
});

final relatedArticlesProvider = FutureProvider.autoDispose
    .family<List<ArticleWithAnalysis>, RelatedArticleRequest>((
      ref,
      request,
    ) async {
      final repository = ref.watch(newsRepositoryProvider);
      final articles = request.categoryId == null
          ? await repository.searchArticles(request.topic, limit: 6)
          : await repository.getArticlesByCategory(
              request.categoryId!,
              limit: 6,
            );
      return articles
          .where((article) => article.id != request.articleId)
          .take(3)
          .toList(growable: false);
    });

final userBookmarksProvider =
    FutureProvider.autoDispose<List<ArticleWithAnalysis>>((ref) {
      final user = ref.watch(currentUserProvider);
      if (user == null) {
        return const [];
      }
      return ref.watch(bookmarkRepositoryProvider).getBookmarks(user.id);
    });

final bookmarkStatusProvider = FutureProvider.autoDispose.family<bool, String>((
  ref,
  articleId,
) {
  final user = ref.watch(currentUserProvider);
  if (user == null) {
    return false;
  }
  return ref.watch(bookmarkRepositoryProvider).isBookmarked(user.id, articleId);
});

final readingHistoryProvider =
    FutureProvider.autoDispose<List<ReadingHistoryEntry>>((ref) {
      final user = ref.watch(currentUserProvider);
      if (user == null) {
        return const [];
      }
      return ref
          .watch(readingHistoryRepositoryProvider)
          .getReadingHistory(user.id);
    });

final profileStatsProvider = FutureProvider.autoDispose<ProfileStats>((ref) {
  final user = ref.watch(currentUserProvider);
  if (user == null) {
    return const ProfileStats(bookmarkCount: 0, articlesReadCount: 0);
  }
  return Future.wait<int>([
    ref.watch(bookmarkRepositoryProvider).getBookmarkCount(user.id),
    ref.watch(readingHistoryRepositoryProvider).getArticlesReadCount(user.id),
  ]).then(
    (counts) =>
        ProfileStats(bookmarkCount: counts[0], articlesReadCount: counts[1]),
  );
});

final userPreferenceProvider = FutureProvider.autoDispose<UserPreference?>((
  ref,
) {
  final user = ref.watch(currentUserProvider);
  if (user == null) {
    return null;
  }
  return ref.watch(userPreferenceRepositoryProvider).getPreference(user.id);
});

class BookmarkActions {
  BookmarkActions(this.ref);

  final Ref ref;

  Future<bool> toggle(String articleId) async {
    final user = ref.read(currentUserProvider);
    if (user == null) {
      throw const AuthRequiredException();
    }
    final repository = ref.read(bookmarkRepositoryProvider);
    final isSaved = await repository.isBookmarked(user.id, articleId);
    if (isSaved) {
      await repository.removeBookmark(user.id, articleId);
    } else {
      await repository.addBookmark(user.id, articleId);
    }
    ref.invalidate(bookmarkStatusProvider(articleId));
    ref.invalidate(userBookmarksProvider);
    ref.invalidate(profileStatsProvider);
    return !isSaved;
  }
}

final bookmarkActionsProvider = Provider<BookmarkActions>(BookmarkActions.new);

class ReadingHistoryActions {
  ReadingHistoryActions(this.ref);

  final Ref ref;

  Future<void> record(String articleId) async {
    final user = ref.read(currentUserProvider);
    if (user == null) {
      return;
    }
    await ref
        .read(readingHistoryRepositoryProvider)
        .recordArticleRead(user.id, articleId);
    ref.invalidate(readingHistoryProvider);
    ref.invalidate(profileStatsProvider);
    ref.invalidate(recommendedArticlesProvider);
  }
}

final readingHistoryActionsProvider = Provider<ReadingHistoryActions>(
  ReadingHistoryActions.new,
);

class UserPreferenceActions {
  UserPreferenceActions(this.ref);

  final Ref ref;

  Future<void> saveCategory(String categoryId) async {
    final user = ref.read(currentUserProvider);
    if (user == null) {
      throw const AuthRequiredException();
    }
    await ref
        .read(userPreferenceRepositoryProvider)
        .savePreferredCategory(user.id, categoryId);
    ref.invalidate(userPreferenceProvider);
    ref.invalidate(recommendedArticlesProvider);
  }
}

final userPreferenceActionsProvider = Provider<UserPreferenceActions>(
  UserPreferenceActions.new,
);

class AuthRequiredException implements Exception {
  const AuthRequiredException();

  @override
  String toString() => 'Please sign in to use this feature.';
}
