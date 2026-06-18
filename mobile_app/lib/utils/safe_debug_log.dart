import 'package:flutter/foundation.dart';

class SafeDebugLog {
  const SafeDebugLog._();

  static void error(String operation, Object error, [StackTrace? stackTrace]) {
    if (!kDebugMode) {
      return;
    }
    debugPrint('$operation: ${sanitize(error)}');
    if (stackTrace != null) {
      debugPrintStack(stackTrace: stackTrace, maxFrames: 8);
    }
  }

  static String sanitize(Object value) {
    var text = value.toString();
    text = text.replaceAllMapped(
      RegExp(r'(apikey=)[^&\s]+', caseSensitive: false),
      (match) => '${match.group(1)}[redacted]',
    );
    text = text.replaceAllMapped(
      RegExp(r'(authorization:\s*bearer\s+)\S+', caseSensitive: false),
      (match) => '${match.group(1)}[redacted]',
    );
    return text.replaceAll(
      RegExp(r'eyJ[\w-]{20,}\.[\w-]+\.[\w-]+'),
      '[redacted-jwt]',
    );
  }
}
