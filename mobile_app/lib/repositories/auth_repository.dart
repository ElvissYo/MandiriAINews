import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/app_user.dart';

abstract interface class AuthRepository {
  AppUser? get currentUser;

  Stream<AppUser?> get authStateChanges;

  Future<AppUser> signIn({required String email, required String password});

  Future<RegistrationResult> register({
    required String email,
    required String password,
    String? name,
  });

  Future<void> signOut();
}

class SupabaseAuthRepository implements AuthRepository {
  SupabaseAuthRepository({required SupabaseClient client}) : _client = client;

  final SupabaseClient _client;

  @override
  AppUser? get currentUser => _mapUser(_client.auth.currentUser);

  @override
  Stream<AppUser?> get authStateChanges async* {
    yield currentUser;
    yield* _client.auth.onAuthStateChange.map(
      (state) => _mapUser(state.session?.user),
    );
  }

  @override
  Future<AppUser> signIn({
    required String email,
    required String password,
  }) async {
    final response = await _client.auth.signInWithPassword(
      email: email.trim(),
      password: password,
    );
    final user = _mapUser(response.user);
    if (user == null) {
      throw const AuthException('Unable to start a user session.');
    }
    return user;
  }

  @override
  Future<RegistrationResult> register({
    required String email,
    required String password,
    String? name,
  }) async {
    final response = await _client.auth.signUp(
      email: email.trim(),
      password: password,
      data: {if (name != null && name.trim().isNotEmpty) 'name': name.trim()},
    );
    final user = _mapUser(response.user);
    if (user == null) {
      throw const AuthException('Unable to create the account.');
    }
    return RegistrationResult(
      user: user,
      requiresEmailConfirmation: response.session == null,
    );
  }

  @override
  Future<void> signOut() => _client.auth.signOut();

  static AppUser? _mapUser(User? user) {
    if (user == null) {
      return null;
    }
    return AppUser(
      id: user.id,
      email: user.email?.trim().isNotEmpty == true
          ? user.email!.trim()
          : 'No email',
    );
  }
}
