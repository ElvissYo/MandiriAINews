import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/app_providers.dart';
import '../widgets/app_loading_state.dart';
import 'home_screen.dart';
import 'onboarding_screen.dart';

class AuthGateScreen extends ConsumerWidget {
  const AuthGateScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ref
        .watch(authStateProvider)
        .when(
          loading: () => const Scaffold(
            body: SafeArea(
              child: AppLoadingState(label: 'Restoring your session...'),
            ),
          ),
          error: (_, _) => const OnboardingScreen(),
          data: (user) =>
              user == null ? const OnboardingScreen() : const HomeScreen(),
        );
  }
}
