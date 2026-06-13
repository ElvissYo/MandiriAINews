import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/article_with_analysis.dart';
import '../providers/app_providers.dart';
import '../theme/app_colors.dart';
import '../utils/date_formatter.dart';
import '../widgets/app_empty_state.dart';
import '../widgets/app_error_state.dart';
import '../widgets/app_loading_state.dart';
import '../widgets/article_image.dart';
import '../widgets/bookmark_button.dart';
import '../widgets/sentiment_badge.dart';

class ArticleDetailScreen extends ConsumerStatefulWidget {
  const ArticleDetailScreen({super.key, required this.articleId});

  final String articleId;

  @override
  ConsumerState<ArticleDetailScreen> createState() =>
      _ArticleDetailScreenState();
}

class _ArticleDetailScreenState extends ConsumerState<ArticleDetailScreen> {
  bool _historyRecorded = false;

  @override
  Widget build(BuildContext context) {
    if (widget.articleId.isEmpty) {
      return const Scaffold(
        body: AppEmptyState(
          icon: Icons.link_off,
          title: 'Article link is invalid',
          message: 'Return to the news feed and select an article again.',
        ),
      );
    }

    final article = ref.watch(articleDetailProvider(widget.articleId));
    return Scaffold(
      appBar: AppBar(
        actions: [
          BookmarkButton(articleId: widget.articleId),
          const SizedBox(width: 8),
        ],
      ),
      body: article.when(
        loading: () => const AppLoadingState(label: 'Loading article...'),
        error: (error, _) => AppErrorState(
          title: 'Unable to load this article',
          error: error,
          onRetry: () =>
              ref.invalidate(articleDetailProvider(widget.articleId)),
        ),
        data: (value) {
          if (value == null) {
            return const AppEmptyState(
              icon: Icons.article_outlined,
              title: 'Article not found',
              message: 'The article may have been removed or unpublished.',
            );
          }
          _recordReadingHistory();
          return _ArticleContent(article: value);
        },
      ),
    );
  }

  void _recordReadingHistory() {
    if (_historyRecorded || ref.read(currentUserProvider) == null) {
      return;
    }
    _historyRecorded = true;
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      try {
        await ref.read(readingHistoryActionsProvider).record(widget.articleId);
      } catch (_) {
        // Reading history must never block access to a public article.
      }
    });
  }
}

class _ArticleContent extends StatelessWidget {
  const _ArticleContent({required this.article});

  final ArticleWithAnalysis article;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
      children: [
        Text(
          article.categoryName.toUpperCase(),
          style: const TextStyle(
            color: AppColors.coral,
            fontWeight: FontWeight.w900,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 10),
        Text(article.title, style: Theme.of(context).textTheme.headlineLarge),
        const SizedBox(height: 16),
        Text(
          '${article.sourceName}  |  '
          '${DateFormatter.articleDate(article.publishedAt)}',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 20),
        ArticleImage(
          imageUrl: article.imageUrl,
          height: 220,
          width: double.infinity,
          borderRadius: BorderRadius.circular(20),
        ),
        const SizedBox(height: 22),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: AppColors.coralSoft,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.auto_awesome, color: AppColors.coral),
                  SizedBox(width: 8),
                  Text(
                    'AI SUMMARY',
                    style: TextStyle(
                      color: AppColors.coral,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.6,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                article.summary,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SentimentBadge(sentiment: article.sentiment),
            if (article.sentimentScore case final score?)
              Chip(label: Text('Score ${score.toStringAsFixed(2)}')),
            Chip(label: Text(article.topic)),
          ],
        ),
        const SizedBox(height: 14),
        if (article.keywords.isEmpty)
          Text(
            'Keywords are not available.',
            style: Theme.of(context).textTheme.bodyMedium,
          )
        else
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: article.keywords
                .map((keyword) => Chip(label: Text('#$keyword')))
                .toList(growable: false),
          ),
        const SizedBox(height: 28),
        Text('Full article', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        Text(article.content, style: Theme.of(context).textTheme.bodyLarge),
      ],
    );
  }
}
