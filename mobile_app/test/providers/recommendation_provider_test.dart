import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mandiri_news_intelligence/models/app_user.dart';
import 'package:mandiri_news_intelligence/providers/app_providers.dart';

import '../support/fake_news_repository.dart';
import '../support/fake_user_repositories.dart';

void main() {
  test(
    'recommended provider passes the signed-in user to repository',
    () async {
      final news = FakeNewsRepository();
      final auth = FakeAuthRepository(
        initialUser: const AppUser(id: 'user-1', email: 'reader@example.com'),
      );
      addTearDown(auth.dispose);
      final container = ProviderContainer(
        overrides: [
          newsRepositoryProvider.overrideWithValue(news),
          authRepositoryProvider.overrideWithValue(auth),
        ],
      );
      addTearDown(container.dispose);

      final articles = await container.read(recommendedArticlesProvider.future);

      expect(articles, isNotEmpty);
      expect(news.lastRecommendationUserId, 'user-1');
    },
  );

  test('trending provider delegates to repository', () async {
    final news = FakeNewsRepository();
    final container = ProviderContainer(
      overrides: [newsRepositoryProvider.overrideWithValue(news)],
    );
    addTearDown(container.dispose);

    await container.read(trendingArticlesProvider.future);

    expect(news.trendingCalls, 1);
  });
}
