import 'article_with_analysis.dart';

class NewsAssistantAnswer {
  const NewsAssistantAnswer({
    required this.question,
    required this.answer,
    required this.sources,
    required this.usedSemanticSearch,
  });

  final String question;
  final String answer;
  final List<ArticleWithAnalysis> sources;
  final bool usedSemanticSearch;
}
