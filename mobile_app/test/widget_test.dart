import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mandiri_news_intelligence/app.dart';
import 'package:mandiri_news_intelligence/models/app_user.dart';
import 'package:mandiri_news_intelligence/providers/app_providers.dart';
import 'package:mandiri_news_intelligence/utils/app_routes.dart';

import 'support/fake_news_repository.dart';
import 'support/fake_user_repositories.dart';

void main() {
  testWidgets('auth gate restores an existing signed-in session', (
    tester,
  ) async {
    final repositories = _FakeRepositories(
      initialUser: const AppUser(id: 'user-1', email: 'reader@example.com'),
    );
    addTearDown(repositories.dispose);

    await tester.pumpWidget(repositories.app());
    await tester.pumpAndSettle();

    expect(find.text('Your intelligence brief'), findsOneWidget);
  });

  testWidgets('home loads feed, filters category, and opens article detail', (
    tester,
  ) async {
    _useTallTestSurface(tester);
    final repositories = _FakeRepositories();
    addTearDown(repositories.dispose);

    await tester.pumpWidget(repositories.app(initialRoute: AppRoutes.home));
    await tester.pumpAndSettle();

    expect(find.text('Digital economy expands across Indonesia'), findsWidgets);
    expect(find.text('AI adoption moves into production'), findsWidgets);
    expect(find.text('Trending Topics'), findsOneWidget);
    expect(find.text('Top Keywords'), findsOneWidget);
    expect(find.text('Trending now'), findsOneWidget);
    expect(find.byKey(const Key('recommendedArticlesSection')), findsOneWidget);
    expect(repositories.news.lastRecommendationUserId, isNull);

    await tester.tap(find.widgetWithText(ChoiceChip, 'Technology'));
    await tester.pumpAndSettle();

    expect(repositories.news.lastCategoryId, 'technology');
    expect(find.text('AI adoption moves into production'), findsWidgets);

    await tester.tap(find.text('AI adoption moves into production').first);
    await tester.pumpAndSettle();

    expect(repositories.news.lastArticleId, 'article-technology');
    expect(find.text('AI SUMMARY'), findsOneWidget);
    expect(find.text('Companies are adopting governed AI systems.'), findsOne);
    expect(find.text('Score 0.00'), findsOneWidget);
    expect(find.text('Topic: Technology'), findsOneWidget);
    expect(find.text('#ai'), findsOneWidget);
    expect(find.text('Related articles'), findsOneWidget);
  });

  testWidgets('home shows real-data ingestion guidance when feed is empty', (
    tester,
  ) async {
    _useTallTestSurface(tester);
    final repositories = _FakeRepositories(emptyNews: true);
    addTearDown(repositories.dispose);

    await tester.pumpWidget(repositories.app(initialRoute: AppRoutes.home));
    await tester.pumpAndSettle();

    expect(
      find.text(
        'No real news data available yet. Please run the ingestion pipeline.',
      ),
      findsWidgets,
    );
    expect(find.byType(Card), findsNothing);
  });

  testWidgets('search displays matching Supabase-style results', (
    tester,
  ) async {
    final repositories = _FakeRepositories();
    addTearDown(repositories.dispose);
    await tester.pumpWidget(repositories.app(initialRoute: AppRoutes.search));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'inclusion');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();

    expect(repositories.news.lastSearchQuery, 'inclusion');
    expect(find.text('Digital economy expands across Indonesia'), findsOne);
    expect(find.text('AI adoption moves into production'), findsNothing);
  });

  testWidgets('news assistant answers from retrieved article sources', (
    tester,
  ) async {
    _useTallTestSurface(tester);
    final repositories = _FakeRepositories();
    addTearDown(repositories.dispose);
    await tester.pumpWidget(
      repositories.app(initialRoute: AppRoutes.assistant),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('newsAssistantQuestionField')),
      'technology ai',
    );
    await tester.tap(find.byKey(const Key('newsAssistantAskButton')));
    await tester.pumpAndSettle();

    expect(repositories.news.lastAssistantQuestion, 'technology ai');
    expect(find.text('Sources'), findsOneWidget);
    expect(find.text('AI adoption moves into production'), findsOneWidget);
    expect(find.text('Semantic retrieval'), findsOneWidget);
  });

  testWidgets('register, login, and logout use the auth controller', (
    tester,
  ) async {
    _useTallTestSurface(tester);
    final repositories = _FakeRepositories();
    addTearDown(repositories.dispose);
    await tester.pumpWidget(repositories.app(initialRoute: AppRoutes.register));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('registerEmailField')),
      'reader@example.com',
    );
    await tester.enterText(
      find.byKey(const Key('registerPasswordField')),
      'password123',
    );
    await tester.tap(find.byKey(const Key('registerButton')));
    await tester.pumpAndSettle();

    expect(repositories.auth.registerCalls, 1);
    expect(find.text('Your intelligence brief'), findsOneWidget);

    await tester.tap(find.text('Profile').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('logoutButton')));
    await tester.pumpAndSettle();

    expect(repositories.auth.signOutCalls, 1);
    expect(find.text('Welcome back'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('loginEmailField')),
      'reader@example.com',
    );
    await tester.enterText(
      find.byKey(const Key('loginPasswordField')),
      'password123',
    );
    await tester.tap(find.byKey(const Key('signInButton')));
    await tester.pumpAndSettle();

    expect(repositories.auth.signInCalls, 1);
    expect(find.text('Your intelligence brief'), findsOneWidget);
  });

  testWidgets('signed-in user can add and remove a bookmark', (tester) async {
    _useTallTestSurface(tester);
    final repositories = _FakeRepositories(
      initialUser: const AppUser(id: 'user-1', email: 'reader@example.com'),
    );
    addTearDown(repositories.dispose);
    await tester.pumpWidget(repositories.app(initialRoute: AppRoutes.home));
    await tester.pumpAndSettle();

    await tester.tap(
      find.byKey(const Key('bookmarkButton-article-economy')).first,
    );
    await tester.pumpAndSettle();
    expect(repositories.bookmarks.savedArticleIds, contains('article-economy'));

    await tester.tap(find.text('Saved'));
    await tester.pumpAndSettle();
    expect(find.text('Digital economy expands across Indonesia'), findsOne);

    await tester.tap(find.byKey(const Key('bookmarkButton-article-economy')));
    await tester.pumpAndSettle();
    expect(repositories.bookmarks.savedArticleIds, isEmpty);
    expect(find.text('No saved articles yet'), findsOneWidget);
  });

  testWidgets('article read updates profile stats and category preference', (
    tester,
  ) async {
    _useTallTestSurface(tester);
    final repositories = _FakeRepositories(
      initialUser: const AppUser(id: 'user-1', email: 'reader@example.com'),
    );
    addTearDown(repositories.dispose);
    await tester.pumpWidget(repositories.app(initialRoute: AppRoutes.home));
    await tester.pumpAndSettle();

    await tester.tap(find.text('AI adoption moves into production').first);
    await tester.pumpAndSettle();
    expect(
      repositories.history.readAtByArticleId,
      contains('article-technology'),
    );

    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.tap(find.text('Profile').last);
    await tester.pumpAndSettle();

    expect(
      find.descendant(
        of: find.byKey(const Key('articlesReadCount')),
        matching: find.text('1'),
      ),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const Key('preferredCategoryDropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Technology').last);
    await tester.pumpAndSettle();

    expect(repositories.preferences.selectedCategoryId, 'technology');
  });
}

class _FakeRepositories {
  _FakeRepositories({AppUser? initialUser, bool emptyNews = false})
    : news = FakeNewsRepository(articles: emptyNews ? const [] : null),
      auth = FakeAuthRepository(initialUser: initialUser);

  final FakeNewsRepository news;
  final FakeAuthRepository auth;
  final bookmarks = FakeBookmarkRepository();
  final history = FakeReadingHistoryRepository();
  final preferences = FakeUserPreferenceRepository();

  Widget app({String? initialRoute}) {
    return ProviderScope(
      overrides: [
        newsRepositoryProvider.overrideWithValue(news),
        authRepositoryProvider.overrideWithValue(auth),
        bookmarkRepositoryProvider.overrideWithValue(bookmarks),
        readingHistoryRepositoryProvider.overrideWithValue(history),
        userPreferenceRepositoryProvider.overrideWithValue(preferences),
      ],
      child: MandiriNewsApp(initialRoute: initialRoute),
    );
  }

  Future<void> dispose() => auth.dispose();
}

void _useTallTestSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}
