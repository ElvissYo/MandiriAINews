import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/app_providers.dart';
import '../theme/app_colors.dart';
import '../utils/app_routes.dart';
import '../utils/error_message.dart';

class BookmarkButton extends ConsumerStatefulWidget {
  const BookmarkButton({
    super.key,
    required this.articleId,
    this.compact = false,
  });

  final String articleId;
  final bool compact;

  @override
  ConsumerState<BookmarkButton> createState() => _BookmarkButtonState();
}

class _BookmarkButtonState extends ConsumerState<BookmarkButton> {
  bool _isUpdating = false;

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final status = ref.watch(bookmarkStatusProvider(widget.articleId));
    final isSaved = status.asData?.value ?? false;

    return IconButton(
      key: Key('bookmarkButton-${widget.articleId}'),
      visualDensity: widget.compact ? VisualDensity.compact : null,
      tooltip: user == null
          ? 'Sign in to bookmark'
          : isSaved
          ? 'Remove bookmark'
          : 'Save article',
      onPressed: _isUpdating ? null : () => _toggle(user != null),
      icon: _isUpdating
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(
              isSaved ? Icons.bookmark : Icons.bookmark_border,
              color: isSaved ? AppColors.coral : AppColors.navy,
            ),
    );
  }

  Future<void> _toggle(bool isSignedIn) async {
    if (!isSignedIn) {
      final shouldLogin = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Sign in required'),
          content: const Text(
            'Sign in to save articles and sync bookmarks across sessions.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Not now'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Sign in'),
            ),
          ],
        ),
      );
      if (mounted && shouldLogin == true) {
        await Navigator.pushNamed(context, AppRoutes.login);
      }
      return;
    }

    setState(() => _isUpdating = true);
    try {
      final isSaved = await ref
          .read(bookmarkActionsProvider)
          .toggle(widget.articleId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(isSaved ? 'Article saved.' : 'Bookmark removed.'),
          ),
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
        setState(() => _isUpdating = false);
      }
    }
  }
}
