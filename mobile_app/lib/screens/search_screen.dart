import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/article_with_analysis.dart';
import '../providers/app_providers.dart';
import '../utils/app_routes.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/app_empty_state.dart';
import '../widgets/app_error_state.dart';
import '../widgets/app_loading_state.dart';
import '../widgets/news_card.dart';
import '../widgets/section_header.dart';

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _controller = TextEditingController();
  Timer? _debounce;
  String _query = '';

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(searchArticlesProvider(_query));
    return Scaffold(
      appBar: AppBar(title: const Text('Search news')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
            child: TextField(
              controller: _controller,
              autofocus: true,
              textInputAction: TextInputAction.search,
              onChanged: _onQueryChanged,
              decoration: InputDecoration(
                hintText: 'Search meaning, title, topic, or keyword',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _controller.text.isEmpty
                    ? null
                    : IconButton(
                        tooltip: 'Clear search',
                        onPressed: _clearSearch,
                        icon: const Icon(Icons.close),
                      ),
              ),
            ),
          ),
          Expanded(
            child: results.when(
              loading: () =>
                  const AppLoadingState(label: 'Searching articles...'),
              error: (error, _) => AppErrorState(
                title: 'Search is unavailable',
                error: error,
                onRetry: () => ref.invalidate(searchArticlesProvider(_query)),
              ),
              data: _buildResults,
            ),
          ),
        ],
      ),
      bottomNavigationBar: const AppBottomNavigation(currentIndex: 1),
    );
  }

  Widget _buildResults(List<ArticleWithAnalysis> articles) {
    if (articles.isEmpty) {
      return AppEmptyState(
        icon: Icons.manage_search,
        title: _query.isEmpty ? 'No recent news' : 'No matching articles',
        message: _query.isEmpty
            ? 'No real news data available yet. Please run the ingestion '
                  'pipeline.'
            : 'Try a different title, topic, or keyword.',
      );
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      children: [
        SectionHeader(title: _query.isEmpty ? 'Recent news' : 'Search results'),
        const SizedBox(height: 12),
        ...articles.map(
          (article) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: NewsCard(
              article: article,
              onTap: () => Navigator.pushNamed(
                context,
                AppRoutes.articleDetail,
                arguments: article.id,
              ),
            ),
          ),
        ),
      ],
    );
  }

  void _onQueryChanged(String value) {
    setState(() {});
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) {
        return;
      }
      setState(() => _query = value.trim());
    });
  }

  void _clearSearch() {
    _debounce?.cancel();
    _controller.clear();
    setState(() => _query = '');
  }
}
