import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../utils/app_routes.dart';

class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 58,
                height: 58,
                decoration: BoxDecoration(
                  color: AppColors.coral,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: const Icon(
                  Icons.auto_awesome,
                  color: Colors.white,
                  size: 30,
                ),
              ),
              const Spacer(),
              Text(
                'Understand the news,\nnot just the headline.',
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const SizedBox(height: 18),
              Text(
                'Read concise AI summaries, explore article sentiment, and '
                'build a news feed around the topics that matter to you.',
                style: Theme.of(
                  context,
                ).textTheme.bodyLarge?.copyWith(color: AppColors.navyMuted),
              ),
              const SizedBox(height: 28),
              const _FeatureRow(
                icon: Icons.summarize_outlined,
                text: 'AI summaries for faster reading',
              ),
              const SizedBox(height: 14),
              const _FeatureRow(
                icon: Icons.insights_outlined,
                text: 'Sentiment, topics, and keywords',
              ),
              const SizedBox(height: 14),
              const _FeatureRow(
                icon: Icons.lock_outline,
                text: 'Personal data protected with Supabase RLS',
              ),
              const Spacer(),
              ElevatedButton(
                onPressed: () => Navigator.pushNamed(context, AppRoutes.login),
                child: const Text('Get started'),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                key: const Key('continueAsGuestButton'),
                onPressed: () =>
                    Navigator.pushReplacementNamed(context, AppRoutes.home),
                child: const Text('Continue as guest'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(
            color: AppColors.coralSoft,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: AppColors.coral, size: 20),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Text(text, style: Theme.of(context).textTheme.titleMedium),
        ),
      ],
    );
  }
}
