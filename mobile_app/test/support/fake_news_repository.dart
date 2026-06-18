import 'package:mandiri_news_intelligence/models/article.dart';
import 'package:mandiri_news_intelligence/models/article_analysis.dart';
import 'package:mandiri_news_intelligence/models/article_with_analysis.dart';
import 'package:mandiri_news_intelligence/models/category.dart';
import 'package:mandiri_news_intelligence/models/news_assistant_answer.dart';
import 'package:mandiri_news_intelligence/models/source.dart';
import 'package:mandiri_news_intelligence/repositories/news_repository.dart';

class FakeNewsRepository implements NewsRepository {
  FakeNewsRepository({
    List<ArticleWithAnalysis>? articles,
    List<Category>? categories,
  }) : articles = articles ?? fixtureArticles,
       categories = categories ?? fixtureCategories;

  final List<ArticleWithAnalysis> articles;
  final List<Category> categories;

  String? lastCategoryId;
  String? lastArticleId;
  String? lastSearchQuery;
  String? lastAssistantQuestion;
  String? lastRecommendationUserId;
  int trendingCalls = 0;

  @override
  Future<List<ArticleWithAnalysis>> getLatestArticles({int limit = 20}) async {
    return articles.take(limit).toList(growable: false);
  }

  @override
  Future<ArticleWithAnalysis?> getArticleById(String articleId) async {
    lastArticleId = articleId;
    for (final article in articles) {
      if (article.id == articleId) {
        return article;
      }
    }
    return null;
  }

  @override
  Future<List<ArticleWithAnalysis>> getArticlesByCategory(
    String categoryId, {
    int limit = 20,
  }) async {
    lastCategoryId = categoryId;
    return articles
        .where((article) => article.category?.id == categoryId)
        .take(limit)
        .toList(growable: false);
  }

  @override
  Future<List<ArticleWithAnalysis>> searchArticles(
    String query, {
    int limit = 20,
  }) async {
    lastSearchQuery = query;
    final normalized = query.trim().toLowerCase();
    if (normalized.isEmpty) {
      return getLatestArticles(limit: limit);
    }
    return articles
        .where((article) {
          final searchable = [
            article.title,
            article.content,
            article.summary,
            article.topic,
            ...article.keywords,
          ].join(' ').toLowerCase();
          return searchable.contains(normalized);
        })
        .take(limit)
        .toList(growable: false);
  }

  @override
  Future<List<ArticleWithAnalysis>> semanticSearchArticles(
    String query, {
    int limit = 20,
  }) {
    return searchArticles(query, limit: limit);
  }

  @override
  Future<NewsAssistantAnswer> askNewsAssistant(
    String question, {
    int limit = 5,
  }) async {
    lastAssistantQuestion = question;
    final sources = await searchArticles(question, limit: limit);
    if (sources.isEmpty) {
      return NewsAssistantAnswer(
        question: question,
        answer: 'No stored articles matched the question.',
        sources: const [],
        usedSemanticSearch: false,
      );
    }
    return NewsAssistantAnswer(
      question: question,
      answer:
          'Based on the retrieved articles: ${sources.first.title}: '
          '${sources.first.summary}',
      sources: sources,
      usedSemanticSearch: true,
    );
  }

  @override
  Future<ArticleWithAnalysis?> getFeaturedArticle() async {
    return articles.isEmpty ? null : articles.first;
  }

  @override
  Future<List<Category>> getCategories() async => categories;

  @override
  Future<List<ArticleWithAnalysis>> getRecommendedArticles({
    String? userId,
    int limit = 10,
  }) async {
    lastRecommendationUserId = userId;
    return articles.take(limit).toList(growable: false);
  }

  @override
  Future<List<ArticleWithAnalysis>> getTrendingArticles({
    int limit = 10,
  }) async {
    trendingCalls++;
    return articles.take(limit).toList(growable: false);
  }
}

const fixtureCategories = [
  Category(id: 'economy', name: 'Economy'),
  Category(id: 'technology', name: 'Technology'),
];

final fixtureArticles = [
  ArticleWithAnalysis(
    article: Article(
      id: 'article-economy',
      title: 'Digital economy expands across Indonesia',
      content: 'Digital infrastructure supports broader financial inclusion.',
      url: 'https://example.com/economy',
      categoryId: 'economy',
      publishedAt: DateTime.utc(2026, 6, 13),
      status: 'published',
    ),
    source: const Source(id: 'source-1', name: 'Fixture Newsroom'),
    category: fixtureCategories.first,
    analysis: const ArticleAnalysis(
      id: 'analysis-1',
      articleId: 'article-economy',
      summary: 'Digital infrastructure supports financial inclusion.',
      sentiment: 'positive',
      sentimentScore: 0.65,
      topic: 'Economy',
      keywords: ['digital economy', 'inclusion'],
    ),
  ),
  ArticleWithAnalysis(
    article: Article(
      id: 'article-technology',
      title: 'AI adoption moves into production',
      content: 'Technology teams focus on governed AI systems.',
      url: 'https://example.com/technology',
      categoryId: 'technology',
      publishedAt: DateTime.utc(2026, 6, 12),
      status: 'published',
    ),
    source: const Source(id: 'source-2', name: 'Fixture Technology Desk'),
    category: fixtureCategories.last,
    analysis: const ArticleAnalysis(
      id: 'analysis-2',
      articleId: 'article-technology',
      summary: 'Companies are adopting governed AI systems.',
      sentiment: 'neutral',
      sentimentScore: 0,
      topic: 'Technology',
      keywords: ['ai', 'governance'],
    ),
  ),
];
