import 'package:flutter/material.dart';

import 'screens/article_detail_screen.dart';
import 'screens/auth_gate_screen.dart';
import 'screens/bookmark_screen.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/register_screen.dart';
import 'screens/search_screen.dart';
import 'theme/app_theme.dart';
import 'utils/app_routes.dart';

class MandiriNewsApp extends StatelessWidget {
  const MandiriNewsApp({super.key, this.initialRoute});

  final String? initialRoute;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mandiri News Intelligence',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      initialRoute: initialRoute,
      home: initialRoute == null ? const AuthGateScreen() : null,
      onGenerateRoute: _onGenerateRoute,
    );
  }

  Route<dynamic> _onGenerateRoute(RouteSettings settings) {
    final Widget page = switch (settings.name) {
      AppRoutes.login => const LoginScreen(),
      AppRoutes.register => const RegisterScreen(),
      AppRoutes.home => const HomeScreen(),
      AppRoutes.articleDetail => ArticleDetailScreen(
        articleId: settings.arguments is String
            ? settings.arguments! as String
            : '',
      ),
      AppRoutes.search => const SearchScreen(),
      AppRoutes.bookmarks => const BookmarkScreen(),
      AppRoutes.profile => const ProfileScreen(),
      _ => const AuthGateScreen(),
    };

    return MaterialPageRoute<void>(builder: (_) => page, settings: settings);
  }
}
