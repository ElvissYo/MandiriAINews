import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/app_user.dart';
import '../models/category.dart';
import '../providers/app_providers.dart';
import '../theme/app_colors.dart';
import '../utils/app_routes.dart';
import '../utils/error_message.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/app_error_state.dart';
import '../widgets/app_loading_state.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: user == null
          ? const _GuestProfile()
          : RefreshIndicator(
              onRefresh: () async {
                ref.invalidate(profileStatsProvider);
                ref.invalidate(userPreferenceProvider);
                await Future.wait([
                  ref.read(profileStatsProvider.future),
                  ref.read(userPreferenceProvider.future),
                ]);
              },
              child: _AuthenticatedProfile(user: user),
            ),
      bottomNavigationBar: const AppBottomNavigation(currentIndex: 3),
    );
  }
}

class _AuthenticatedProfile extends ConsumerWidget {
  const _AuthenticatedProfile({required this.user});

  final AppUser user;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(profileStatsProvider);
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(20),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                const CircleAvatar(
                  radius: 34,
                  backgroundColor: AppColors.coralSoft,
                  child: Icon(
                    Icons.person_outline,
                    color: AppColors.coral,
                    size: 34,
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  user.email,
                  style: Theme.of(context).textTheme.titleLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 6),
                Text(
                  'Personal data is protected by Supabase RLS.',
                  style: Theme.of(context).textTheme.bodyMedium,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 18),
        stats.when(
          loading: () => const SizedBox(
            height: 112,
            child: AppLoadingState(label: 'Loading profile stats...'),
          ),
          error: (error, _) => AppErrorState(
            title: 'Unable to load profile stats',
            error: error,
            onRetry: () => ref.invalidate(profileStatsProvider),
          ),
          data: (value) => Row(
            children: [
              Expanded(
                child: _StatCard(
                  key: const Key('bookmarkCount'),
                  icon: Icons.bookmark_outline,
                  value: value.bookmarkCount.toString(),
                  label: 'Bookmarked',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatCard(
                  key: const Key('articlesReadCount'),
                  icon: Icons.history,
                  value: value.articlesReadCount.toString(),
                  label: 'Articles read',
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        const _PreferenceCard(),
        const SizedBox(height: 18),
        OutlinedButton.icon(
          key: const Key('logoutButton'),
          onPressed: ref.watch(authControllerProvider).isLoading
              ? null
              : () => _logout(context, ref),
          icon: const Icon(Icons.logout),
          label: const Text('Sign out'),
        ),
      ],
    );
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(authControllerProvider.notifier).signOut();
      if (context.mounted) {
        Navigator.pushNamedAndRemoveUntil(
          context,
          AppRoutes.login,
          (_) => false,
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(ErrorMessage.from(error))));
      }
    }
  }
}

class _PreferenceCard extends ConsumerWidget {
  const _PreferenceCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categories = ref.watch(categoriesProvider);
    final preference = ref.watch(userPreferenceProvider);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.tune, color: AppColors.coral),
                const SizedBox(width: 10),
                Text(
                  'Preferred category',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'This basic preference will support recommendations in a later '
              'phase.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            categories.when(
              loading: () => const LinearProgressIndicator(),
              error: (error, _) => Text(
                ErrorMessage.from(error),
                style: const TextStyle(color: AppColors.negative),
              ),
              data: (items) => preference.when(
                loading: () => const LinearProgressIndicator(),
                error: (error, _) => Text(
                  ErrorMessage.from(error),
                  style: const TextStyle(color: AppColors.negative),
                ),
                data: (value) => _CategoryDropdown(
                  categories: items,
                  selectedCategoryId: value?.preferredCategory?.id,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CategoryDropdown extends ConsumerStatefulWidget {
  const _CategoryDropdown({
    required this.categories,
    required this.selectedCategoryId,
  });

  final List<Category> categories;
  final String? selectedCategoryId;

  @override
  ConsumerState<_CategoryDropdown> createState() => _CategoryDropdownState();
}

class _CategoryDropdownState extends ConsumerState<_CategoryDropdown> {
  bool _isSaving = false;

  @override
  Widget build(BuildContext context) {
    final selected =
        widget.categories.any(
          (category) => category.id == widget.selectedCategoryId,
        )
        ? widget.selectedCategoryId
        : null;
    return DropdownButtonFormField<String>(
      key: const Key('preferredCategoryDropdown'),
      initialValue: selected,
      decoration: const InputDecoration(
        labelText: 'Category',
        prefixIcon: Icon(Icons.category_outlined),
      ),
      hint: const Text('Select a category'),
      items: widget.categories
          .map(
            (category) => DropdownMenuItem(
              value: category.id,
              child: Text(category.name),
            ),
          )
          .toList(growable: false),
      onChanged: _isSaving ? null : _save,
    );
  }

  Future<void> _save(String? categoryId) async {
    if (categoryId == null) {
      return;
    }
    setState(() => _isSaving = true);
    try {
      await ref.read(userPreferenceActionsProvider).saveCategory(categoryId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Preferred category updated.')),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(ErrorMessage.from(error))));
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    super.key,
    required this.icon,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 18),
        child: Column(
          children: [
            Icon(icon, color: AppColors.coral),
            const SizedBox(height: 8),
            Text(value, style: Theme.of(context).textTheme.headlineMedium),
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}

class _GuestProfile extends StatelessWidget {
  const _GuestProfile();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                const CircleAvatar(
                  radius: 34,
                  backgroundColor: AppColors.coralSoft,
                  child: Icon(
                    Icons.person_outline,
                    color: AppColors.coral,
                    size: 34,
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  'Guest reader',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 6),
                Text(
                  'Sign in to sync bookmarks, history, and preferences.',
                  style: Theme.of(context).textTheme.bodyMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 18),
                ElevatedButton(
                  onPressed: () =>
                      Navigator.pushNamed(context, AppRoutes.login),
                  child: const Text('Sign in'),
                ),
                const SizedBox(height: 10),
                OutlinedButton(
                  onPressed: () =>
                      Navigator.pushNamed(context, AppRoutes.register),
                  child: const Text('Create an account'),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
