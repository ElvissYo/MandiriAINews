class AppUser {
  const AppUser({required this.id, required this.email});

  final String id;
  final String email;
}

class RegistrationResult {
  const RegistrationResult({
    required this.user,
    required this.requiresEmailConfirmation,
  });

  final AppUser user;
  final bool requiresEmailConfirmation;
}
