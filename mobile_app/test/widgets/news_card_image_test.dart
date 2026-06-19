import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mandiri_news_intelligence/models/article.dart';
import 'package:mandiri_news_intelligence/models/article_with_analysis.dart';
import 'package:mandiri_news_intelligence/models/category.dart';
import 'package:mandiri_news_intelligence/models/source.dart';
import 'package:mandiri_news_intelligence/providers/app_providers.dart';
import 'package:mandiri_news_intelligence/screens/article_detail_screen.dart';
import 'package:mandiri_news_intelligence/widgets/news_card.dart';

import '../support/fake_news_repository.dart';
import '../support/fake_user_repositories.dart';

void main() {
  testWidgets('news card renders placeholder when imageUrl is null', (
    tester,
  ) async {
    final auth = FakeAuthRepository();
    addTearDown(auth.dispose);

    await tester.pumpWidget(_cardHarness(_article(imageUrl: null), auth: auth));
    await tester.pump();

    expect(find.byIcon(Icons.newspaper_outlined), findsOneWidget);
    expect(find.text('Economy'), findsOneWidget);
    expect(find.byType(CachedNetworkImage), findsNothing);
  });

  testWidgets('news card renders network image when imageUrl exists', (
    tester,
  ) async {
    final auth = FakeAuthRepository();
    addTearDown(auth.dispose);
    const imageUrl = 'https://cdn.newsroom.id/story.jpg';

    await tester.pumpWidget(
      _cardHarness(_article(imageUrl: imageUrl), auth: auth),
    );

    final image = tester.widget<CachedNetworkImage>(
      find.byType(CachedNetworkImage),
    );
    expect(image.imageUrl, imageUrl);
  });

  testWidgets('featured news card renders network image for hero', (
    tester,
  ) async {
    final auth = FakeAuthRepository();
    addTearDown(auth.dispose);
    const imageUrl = 'https://cdn.newsroom.id/hero.jpg';

    await tester.pumpWidget(
      _cardHarness(_article(imageUrl: imageUrl), auth: auth, featured: true),
    );

    final image = tester.widget<CachedNetworkImage>(
      find.byType(CachedNetworkImage),
    );
    expect(image.imageUrl, imageUrl);
  });

  testWidgets('article detail renders network image for header', (
    tester,
  ) async {
    final auth = FakeAuthRepository();
    final article = _article(imageUrl: 'https://cdn.newsroom.id/detail.jpg');
    addTearDown(auth.dispose);

    await tester.pumpWidget(_detailHarness(article, auth: auth));
    await tester.pumpAndSettle();

    final image = tester.widget<CachedNetworkImage>(
      find.byType(CachedNetworkImage).first,
    );
    expect(image.imageUrl, 'https://cdn.newsroom.id/detail.jpg');
  });
}

Widget _cardHarness(
  ArticleWithAnalysis article, {
  required FakeAuthRepository auth,
  bool featured = false,
}) {
  return ProviderScope(
    overrides: [authRepositoryProvider.overrideWithValue(auth)],
    child: MaterialApp(
      home: Scaffold(
        body: Center(
          child: SizedBox(
            width: 360,
            child: NewsCard(article: article, featured: featured, onTap: () {}),
          ),
        ),
      ),
    ),
  );
}

Widget _detailHarness(
  ArticleWithAnalysis article, {
  required FakeAuthRepository auth,
}) {
  final news = FakeNewsRepository(articles: [article]);
  final bookmarks = FakeBookmarkRepository();
  final history = FakeReadingHistoryRepository();
  final preferences = FakeUserPreferenceRepository();
  return ProviderScope(
    overrides: [
      newsRepositoryProvider.overrideWithValue(news),
      authRepositoryProvider.overrideWithValue(auth),
      bookmarkRepositoryProvider.overrideWithValue(bookmarks),
      readingHistoryRepositoryProvider.overrideWithValue(history),
      userPreferenceRepositoryProvider.overrideWithValue(preferences),
    ],
    child: MaterialApp(home: ArticleDetailScreen(articleId: article.id)),
  );
}

ArticleWithAnalysis _article({required String? imageUrl}) {
  return ArticleWithAnalysis(
    article: Article(
      id: 'article-image-test',
      title: 'Regional markets gain after policy update',
      content: 'Markets gained after a policy update.',
      url: 'https://newsroom.id/regional-markets',
      imageUrl: imageUrl,
      publishedAt: DateTime.utc(2026, 6, 14),
      status: 'published',
    ),
    source: const Source(id: 'source-1', name: 'Newsroom Indonesia'),
    category: const Category(id: 'economy', name: 'Economy'),
  );
}
