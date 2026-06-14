import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/article_with_analysis.dart';
import '../models/category.dart';
import '../models/trending_insight.dart';
import '../providers/app_providers.dart';
import '../theme/app_colors.dart';
import '../utils/app_routes.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/app_empty_state.dart';
import '../widgets/app_error_state.dart';
import '../widgets/app_loading_state.dart';
import '../widgets/news_card.dart';
import '../widgets/section_header.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categories = ref.watch(categoriesProvider);
    final featuredArticle = ref.watch(featuredArticleProvider);
    final latestArticles = ref.watch(latestArticlesProvider);
    final recommendedArticles = ref.watch(recommendedArticlesProvider);
    final trendingInsight = ref.watch(trendingInsightProvider);
    final selectedCategoryId = ref.watch(selectedCategoryProvider);
    final currentUser = ref.watch(currentUserProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'MANDIRI NEWS',
              style: TextStyle(
                color: AppColors.coral,
                fontSize: 12,
                fontWeight: FontWeight.w900,
                letterSpacing: 1.4,
              ),
            ),
            Text('Your intelligence brief'),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Profile',
            onPressed: () => Navigator.pushNamed(context, AppRoutes.profile),
            icon: const CircleAvatar(
              backgroundColor: AppColors.coralSoft,
              child: Icon(Icons.person_outline, color: AppColors.coral),
            ),
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.coral,
        onRefresh: () => _refresh(ref),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () => Navigator.pushNamed(context, AppRoutes.search),
              child: const IgnorePointer(
                child: TextField(
                  decoration: InputDecoration(
                    hintText: 'Search title, topic, or keyword',
                    prefixIcon: Icon(Icons.search),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 18),
            _CategoryFilter(
              categories: categories,
              selectedCategoryId: selectedCategoryId,
              onSelected: (categoryId) {
                ref.read(selectedCategoryProvider.notifier).select(categoryId);
              },
              onRetry: () => ref.invalidate(categoriesProvider),
            ),
            const SizedBox(height: 26),
            const SectionHeader(title: 'Top story'),
            const SizedBox(height: 12),
            _FeaturedArticle(
              value: featuredArticle,
              onOpen: (article) => _openArticle(context, article.id),
              onRetry: () => ref.invalidate(featuredArticleProvider),
            ),
            const SizedBox(height: 28),
            const SectionHeader(title: 'Trending Topics'),
            const SizedBox(height: 12),
            _TrendingInsightSection(
              value: trendingInsight,
              onRetry: () => ref.invalidate(trendingInsightProvider),
            ),
            const SizedBox(height: 28),
            SectionHeader(
              title: currentUser == null
                  ? 'Trending now'
                  : 'Recommended for you',
            ),
            const SizedBox(height: 12),
            _HorizontalArticleList(
              value: recommendedArticles,
              onOpen: (article) => _openArticle(context, article.id),
              onRetry: () => ref.invalidate(recommendedArticlesProvider),
            ),
            const SizedBox(height: 28),
            SectionHeader(
              title: selectedCategoryId == null
                  ? 'Latest news'
                  : _selectedCategoryName(categories, selectedCategoryId),
              actionLabel: 'Search',
              onAction: () => Navigator.pushNamed(context, AppRoutes.search),
            ),
            const SizedBox(height: 12),
            _ArticleList(
              value: latestArticles,
              onOpen: (article) => _openArticle(context, article.id),
              onRetry: () => ref.invalidate(latestArticlesProvider),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const AppBottomNavigation(currentIndex: 0),
    );
  }

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(categoriesProvider);
    ref.invalidate(featuredArticleProvider);
    ref.invalidate(latestArticlesProvider);
    ref.invalidate(recommendedArticlesProvider);
    ref.invalidate(trendingArticlesProvider);
    ref.invalidate(trendingInsightProvider);
    await Future.wait([
      ref.read(latestArticlesProvider.future),
      ref.read(recommendedArticlesProvider.future),
      ref.read(trendingInsightProvider.future),
    ]);
  }

  void _openArticle(BuildContext context, String articleId) {
    Navigator.pushNamed(context, AppRoutes.articleDetail, arguments: articleId);
  }

  String _selectedCategoryName(
    AsyncValue<List<Category>> categories,
    String selectedCategoryId,
  ) {
    return categories.maybeWhen(
      data: (items) {
        for (final category in items) {
          if (category.id == selectedCategoryId) {
            return category.name;
          }
        }
        return 'Category news';
      },
      orElse: () => 'Category news',
    );
  }
}

class _TrendingInsightSection extends StatelessWidget {
  const _TrendingInsightSection({required this.value, required this.onRetry});

  final AsyncValue<TrendingInsight> value;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => const SizedBox(
        height: 72,
        child: Center(
          child: CircularProgressIndicator(
            color: AppColors.coral,
            strokeWidth: 2,
          ),
        ),
      ),
      error: (_, _) => Align(
        alignment: Alignment.centerLeft,
        child: ActionChip(
          avatar: const Icon(Icons.refresh, size: 18),
          label: const Text('Reload trends'),
          onPressed: onRetry,
        ),
      ),
      data: (insight) {
        if (insight.topics.isEmpty && insight.keywords.isEmpty) {
          return Text(
            'Trend insight will appear after analyzed articles are available.',
            style: Theme.of(context).textTheme.bodyMedium,
          );
        }
        return Container(
          key: const Key('trendingInsightSection'),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            border: Border.all(color: AppColors.border),
            borderRadius: BorderRadius.circular(18),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: insight.topics
                    .map(
                      (topic) => Chip(
                        avatar: const Icon(
                          Icons.trending_up,
                          size: 17,
                          color: AppColors.coral,
                        ),
                        label: Text(topic),
                      ),
                    )
                    .toList(growable: false),
              ),
              if (insight.keywords.isNotEmpty) ...[
                const SizedBox(height: 14),
                Text(
                  'Top Keywords',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: insight.keywords
                      .map((keyword) => Chip(label: Text('#$keyword')))
                      .toList(growable: false),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _HorizontalArticleList extends StatelessWidget {
  const _HorizontalArticleList({
    required this.value,
    required this.onOpen,
    required this.onRetry,
  });

  final AsyncValue<List<ArticleWithAnalysis>> value;
  final ValueChanged<ArticleWithAnalysis> onOpen;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => const SizedBox(
        height: 152,
        child: Center(
          child: CircularProgressIndicator(
            color: AppColors.coral,
            strokeWidth: 2,
          ),
        ),
      ),
      error: (error, _) => AppErrorState(
        title: 'Recommendations are unavailable',
        error: error,
        onRetry: onRetry,
      ),
      data: (articles) {
        if (articles.isEmpty) {
          return const AppEmptyState(
            icon: Icons.recommend_outlined,
            title: 'No recommendations yet',
            message: 'Read a few articles or refresh when more news is loaded.',
          );
        }
        return SizedBox(
          key: const Key('recommendedArticlesSection'),
          height: 152,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: articles.length,
            separatorBuilder: (_, _) => const SizedBox(width: 12),
            itemBuilder: (context, index) {
              final article = articles[index];
              return SizedBox(
                width: 340,
                child: NewsCard(article: article, onTap: () => onOpen(article)),
              );
            },
          ),
        );
      },
    );
  }
}

class _CategoryFilter extends StatelessWidget {
  const _CategoryFilter({
    required this.categories,
    required this.selectedCategoryId,
    required this.onSelected,
    required this.onRetry,
  });

  final AsyncValue<List<Category>> categories;
  final String? selectedCategoryId;
  final ValueChanged<String?> onSelected;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 42,
      child: categories.when(
        loading: () => const Align(
          alignment: Alignment.centerLeft,
          child: SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
        error: (_, _) => Align(
          alignment: Alignment.centerLeft,
          child: ActionChip(
            avatar: const Icon(Icons.refresh, size: 18),
            label: const Text('Reload categories'),
            onPressed: onRetry,
          ),
        ),
        data: (items) => ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: items.length + 1,
          separatorBuilder: (_, _) => const SizedBox(width: 8),
          itemBuilder: (context, index) {
            final category = index == 0 ? null : items[index - 1];
            return ChoiceChip(
              label: Text(category?.name ?? 'All'),
              selected: category?.id == selectedCategoryId,
              onSelected: (_) => onSelected(category?.id),
            );
          },
        ),
      ),
    );
  }
}

class _FeaturedArticle extends StatelessWidget {
  const _FeaturedArticle({
    required this.value,
    required this.onOpen,
    required this.onRetry,
  });

  final AsyncValue<ArticleWithAnalysis?> value;
  final ValueChanged<ArticleWithAnalysis> onOpen;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => const SizedBox(
        height: 260,
        child: AppLoadingState(label: 'Loading top story...'),
      ),
      error: (error, _) => AppErrorState(
        title: 'Top story is unavailable',
        error: error,
        onRetry: onRetry,
      ),
      data: (article) {
        if (article == null) {
          return const AppEmptyState(
            icon: Icons.newspaper_outlined,
            title: 'No featured article',
            message: 'A published article will appear here once available.',
          );
        }
        return NewsCard(
          article: article,
          featured: true,
          onTap: () => onOpen(article),
        );
      },
    );
  }
}

class _ArticleList extends StatelessWidget {
  const _ArticleList({
    required this.value,
    required this.onOpen,
    required this.onRetry,
  });

  final AsyncValue<List<ArticleWithAnalysis>> value;
  final ValueChanged<ArticleWithAnalysis> onOpen;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => const SizedBox(height: 220, child: AppLoadingState()),
      error: (error, _) => AppErrorState(
        title: 'Unable to load the news feed',
        error: error,
        onRetry: onRetry,
      ),
      data: (articles) {
        if (articles.isEmpty) {
          return const AppEmptyState(
            icon: Icons.article_outlined,
            title: 'No published articles',
            message: 'Try another category or refresh the feed.',
          );
        }
        return Column(
          children: articles
              .map(
                (article) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: NewsCard(
                    article: article,
                    onTap: () => onOpen(article),
                  ),
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}
