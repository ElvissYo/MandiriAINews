import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mandiri_news_intelligence/utils/error_message.dart';
import 'package:mandiri_news_intelligence/utils/safe_debug_log.dart';
import 'package:mandiri_news_intelligence/widgets/app_error_state.dart';

void main() {
  test('DNS errors are converted to a clear safe message', () {
    final message = ErrorMessage.from(
      "ClientException with SocketException: Failed host lookup: "
      "'project.supabase.co'",
    );

    expect(message, contains('internet or DNS'));
    expect(message, isNot(contains('SocketException')));
    expect(message, isNot(contains('project.supabase.co')));
  });

  testWidgets('error state hides technical details and keeps retry action', (
    tester,
  ) async {
    var retries = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppErrorState(
            title: 'Unable to load the news feed',
            error: Exception(
              'ClientException: Failed host lookup: secret.supabase.co',
            ),
            onRetry: () => retries++,
          ),
        ),
      ),
    );

    expect(find.textContaining('internet or DNS'), findsOneWidget);
    expect(find.textContaining('secret.supabase.co'), findsNothing);

    await tester.tap(find.text('Try again'));
    expect(retries, 1);
  });

  test('debug log sanitizer removes query keys and JWT values', () {
    final jwt = 'eyJ${List.filled(20, 'a').join()}.bbbbb.ccccc';
    final sanitized = SafeDebugLog.sanitize(
      'apikey=private-value authorization: Bearer $jwt',
    );

    expect(sanitized, isNot(contains('private-value')));
    expect(sanitized, isNot(contains(jwt)));
  });
}
