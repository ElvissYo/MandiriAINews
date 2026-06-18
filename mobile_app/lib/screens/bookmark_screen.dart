import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/app_providers.dart';
import '../utils/app_routes.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/app_empty_state.dart';
import '../widgets/app_error_state.dart';
import '../widgets/app_loading_state.dart';
import '../widgets/news_card.dart';

class BookmarkScreen extends ConsumerWidget {
  const BookmarkScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Saved articles')),
      body: user == null
          ? _GuestBookmarks(
              onLogin: () => Navigator.pushNamed(context, AppRoutes.login),
            )
          : RefreshIndicator(
              onRefresh: () async {
                ref.invalidate(userBookmarksProvider);
                await ref.read(userBookmarksProvider.future);
              },
              child: ref
                  .watch(userBookmarksProvider)
                  .when(
                    loading: () =>
                        const AppLoadingState(label: 'Loading bookmarks...'),
                    error: (error, _) => AppErrorState(
                      title: 'Unable to load bookmarks',
                      error: error,
                      onRetry: () => ref.invalidate(userBookmarksProvider),
                    ),
                    data: (articles) {
                      if (articles.isEmpty) {
                        return const AppEmptyState(
                          icon: Icons.bookmark_border,
                          title: 'No saved articles yet',
                          message:
                              'Use the bookmark icon on an article to save it.',
                        );
                      }
                      return ListView.separated(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
                        itemCount: articles.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final article = articles[index];
                          return NewsCard(
                            article: article,
                            onTap: () => Navigator.pushNamed(
                              context,
                              AppRoutes.articleDetail,
                              arguments: article.id,
                            ),
                          );
                        },
                      );
                    },
                  ),
            ),
      bottomNavigationBar: const AppBottomNavigation(currentIndex: 3),
    );
  }
}

class _GuestBookmarks extends StatelessWidget {
  const _GuestBookmarks({required this.onLogin});

  final VoidCallback onLogin;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const AppEmptyState(
          icon: Icons.lock_outline,
          title: 'Sign in to see bookmarks',
          message:
              'Your saved articles are private and linked to your account.',
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: ElevatedButton(
            onPressed: onLogin,
            child: const Text('Sign in'),
          ),
        ),
      ],
    );
  }
}
