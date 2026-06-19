import 'package:flutter/material.dart';

import '../models/article_with_analysis.dart';
import '../theme/app_colors.dart';
import '../utils/date_formatter.dart';
import 'article_image.dart';
import 'bookmark_button.dart';
import 'sentiment_badge.dart';

class NewsCard extends StatelessWidget {
  const NewsCard({
    super.key,
    required this.article,
    required this.onTap,
    this.featured = false,
  });

  final ArticleWithAnalysis article;
  final VoidCallback onTap;
  final bool featured;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: featured ? _featured(context) : _compact(context),
      ),
    );
  }

  Widget _featured(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _image(height: 190, width: double.infinity),
        Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  SentimentBadge(sentiment: article.sentiment),
                  const Spacer(),
                  Text(
                    article.categoryName,
                    style: const TextStyle(
                      color: AppColors.coral,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  BookmarkButton(articleId: article.id, compact: true),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                article.title,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 10),
              Text(
                article.summary,
                style: Theme.of(context).textTheme.bodyMedium,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 14),
              _metadata(context),
            ],
          ),
        ),
      ],
    );
  }

  Widget _compact(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _image(height: 112, width: 112),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  article.categoryName.toUpperCase(),
                  style: const TextStyle(
                    color: AppColors.coral,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  article.title,
                  style: Theme.of(context).textTheme.titleMedium,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 10),
                _metadata(context),
              ],
            ),
          ),
          BookmarkButton(articleId: article.id, compact: true),
        ],
      ),
    );
  }

  Widget _image({required double height, required double width}) {
    return ArticleImage(
      imageUrl: article.imageUrl,
      height: height,
      width: width,
      fallbackLabel: article.categoryName,
    );
  }

  Widget _metadata(BuildContext context) {
    return Text(
      '${article.sourceName}  |  ${DateFormatter.articleDate(article.publishedAt)}',
      style: Theme.of(
        context,
      ).textTheme.bodySmall?.copyWith(color: AppColors.navyMuted),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }
}
