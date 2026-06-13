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
    if (lower.contains('network') || lower.contains('socket')) {
      return 'Network connection failed. Please try again.';
    }
    return raw.isEmpty ? 'Something went wrong. Please try again.' : raw;
  }
}
