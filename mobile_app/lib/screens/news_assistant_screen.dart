import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/news_assistant_answer.dart';
import '../providers/app_providers.dart';
import '../theme/app_colors.dart';
import '../utils/app_routes.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/app_empty_state.dart';
import '../widgets/app_error_state.dart';
import '../widgets/app_loading_state.dart';
import '../widgets/section_header.dart';

class NewsAssistantScreen extends ConsumerStatefulWidget {
  const NewsAssistantScreen({super.key});

  @override
  ConsumerState<NewsAssistantScreen> createState() =>
      _NewsAssistantScreenState();
}

class _NewsAssistantScreenState extends ConsumerState<NewsAssistantScreen> {
  final _controller = TextEditingController();
  String _submittedQuestion = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final question = _submittedQuestion;
    final answer = question.isEmpty
        ? null
        : ref.watch(newsAssistantAnswerProvider(question));
    return Scaffold(
      appBar: AppBar(title: const Text('News Assistant')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: TextField(
                    key: const Key('newsAssistantQuestionField'),
                    controller: _controller,
                    minLines: 1,
                    maxLines: 3,
                    textInputAction: TextInputAction.search,
                    onSubmitted: (_) => _ask(),
                    decoration: const InputDecoration(
                      hintText: 'Ask about stored news articles',
                      prefixIcon: Icon(Icons.auto_awesome_outlined),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                FilledButton(
                  key: const Key('newsAssistantAskButton'),
                  onPressed: _ask,
                  child: const Text('Ask'),
                ),
              ],
            ),
          ),
          Expanded(
            child: answer == null
                ? const AppEmptyState(
                    icon: Icons.auto_awesome_outlined,
                    title: 'Ask the news assistant',
                    message:
                        'Answers use stored real articles and include sources.',
                  )
                : answer.when(
                    loading: () =>
                        const AppLoadingState(label: 'Reading articles...'),
                    error: (error, _) => AppErrorState(
                      title: 'Assistant is unavailable',
                      error: error,
                      onRetry: () =>
                          ref.invalidate(newsAssistantAnswerProvider(question)),
                    ),
                    data: _buildAnswer,
                  ),
          ),
        ],
      ),
      bottomNavigationBar: const AppBottomNavigation(currentIndex: 2),
    );
  }

  Widget _buildAnswer(NewsAssistantAnswer answer) {
    if (answer.sources.isEmpty) {
      return const AppEmptyState(
        icon: Icons.travel_explore,
        title: 'No matching article context',
        message: 'Run the real news ingestion pipeline, then ask again.',
      );
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.auto_awesome, color: AppColors.coral),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        answer.question,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(answer.answer),
                const SizedBox(height: 12),
                Chip(
                  avatar: Icon(
                    answer.usedSemanticSearch
                        ? Icons.hub_outlined
                        : Icons.manage_search,
                    size: 18,
                  ),
                  label: Text(
                    answer.usedSemanticSearch
                        ? 'Semantic retrieval'
                        : 'Keyword fallback',
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 18),
        const SectionHeader(title: 'Sources'),
        const SizedBox(height: 10),
        ...answer.sources.map(
          (article) => ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(article.title),
            subtitle: Text(article.sourceName),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.pushNamed(
              context,
              AppRoutes.articleDetail,
              arguments: article.id,
            ),
          ),
        ),
      ],
    );
  }

  void _ask() {
    final question = _controller.text.trim();
    if (question.isEmpty) {
      return;
    }
    setState(() => _submittedQuestion = question);
  }
}
