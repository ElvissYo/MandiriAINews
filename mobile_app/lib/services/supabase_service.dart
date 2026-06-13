import 'package:supabase_flutter/supabase_flutter.dart';

import '../utils/app_config.dart';

class SupabaseService {
  const SupabaseService();

  static bool _isInitialized = false;

  static bool get isInitialized => _isInitialized;

  static Future<void> initialize() async {
    if (!AppConfig.isSupabaseConfigured) {
      return;
    }

    await Supabase.initialize(
      url: AppConfig.supabaseUrl,
      publishableKey: AppConfig.supabaseAnonKey,
    );
    _isInitialized = true;
  }

  SupabaseClient get client {
    if (!_isInitialized) {
      throw StateError(
        'Supabase is not configured. Add valid values to mobile_app/.env.',
      );
    }
    return Supabase.instance.client;
  }
}
