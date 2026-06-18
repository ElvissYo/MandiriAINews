import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../utils/error_message.dart';
import '../utils/safe_debug_log.dart';

class AppErrorState extends StatefulWidget {
  const AppErrorState({
    super.key,
    required this.title,
    required this.error,
    required this.onRetry,
  });

  final String title;
  final Object error;
  final VoidCallback onRetry;

  @override
  State<AppErrorState> createState() => _AppErrorStateState();
}

class _AppErrorStateState extends State<AppErrorState> {
  @override
  void initState() {
    super.initState();
    SafeDebugLog.error(widget.title, widget.error);
  }

  @override
  void didUpdateWidget(covariant AppErrorState oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.error.toString() != widget.error.toString()) {
      SafeDebugLog.error(widget.title, widget.error);
    }
  }

  @override
  Widget build(BuildContext context) {
    final details = ErrorMessage.from(widget.error);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: const BoxDecoration(
                color: AppColors.coralSoft,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.cloud_off_outlined,
                size: 32,
                color: AppColors.coral,
              ),
            ),
            const SizedBox(height: 18),
            Text(
              widget.title,
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              details,
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: widget.onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }
}
