class ErrorMessage {
  const ErrorMessage._();

  static String from(Object error) {
    final raw = error.toString().replaceFirst(RegExp(r'^[^:]+:\s*'), '');
    final lower = raw.toLowerCase();
    if (lower.contains('invalid login credentials')) {
      return 'Email or password is incorrect.';
    }
    if (lower.contains('email not confirmed')) {
      return 'Confirm your email before signing in.';
    }
    if (lower.contains('user already registered')) {
      return 'An account with this email already exists.';
    }
    if (lower.contains('password should be')) {
      return 'Password does not meet the minimum requirements.';
    }
    if (lower.contains('failed host lookup') ||
        lower.contains('name or service not known') ||
        lower.contains('no address associated with hostname') ||
        lower.contains('dns')) {
      return 'Cannot reach the news service. Check your internet or DNS '
          'connection, then try again.';
    }
    if (lower.contains('timed out') || lower.contains('timeout')) {
      return 'The news service took too long to respond. Please try again.';
    }
    if (lower.contains('network') ||
        lower.contains('socket') ||
        lower.contains('clientexception') ||
        lower.contains('connection refused') ||
        lower.contains('connection closed')) {
      return 'Network connection failed. Check your connection and try again.';
    }
    if (lower.contains('supabase is not configured')) {
      return 'The news service is not configured on this app build.';
    }
    return 'Something went wrong. Please try again.';
  }
}
