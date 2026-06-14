import '../models/article_with_analysis.dart';
import '../models/category.dart';

abstract interface class NewsRepository {
  Future<List<ArticleWithAnalysis>> getLatestArticles({int limit = 20});

  Future<ArticleWithAnalysis?> getArticleById(String articleId);

  Future<List<ArticleWithAnalysis>> getArticlesByCategory(
    String categoryId, {
    int limit = 20,
  });

  Future<List<ArticleWithAnalysis>> searchArticles(
    String query, {
    int limit = 20,
  });

  Future<ArticleWithAnalysis?> getFeaturedArticle();

  Future<List<Category>> getCategories();

  Future<List<ArticleWithAnalysis>> getRecommendedArticles({
    String? userId,
    int limit = 10,
  });

  Future<List<ArticleWithAnalysis>> getTrendingArticles({int limit = 10});
}
