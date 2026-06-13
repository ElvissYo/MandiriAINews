import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class SentimentBadge extends StatelessWidget {
  const SentimentBadge({super.key, required this.sentiment});

  final String sentiment;

  @override
  Widget build(BuildContext context) {
    final normalized = sentiment.toLowerCase();
    final color = switch (normalized) {
      'positive' => AppColors.positive,
      'negative' => AppColors.negative,
      _ => AppColors.neutral,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        normalized.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}
