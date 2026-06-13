import 'package:flutter_dotenv/flutter_dotenv.dart';

class AppConfig {
  const AppConfig._();

  static Future<void> load() async {
    await dotenv.load(fileName: '.env');
  }

  static String get supabaseUrl {
    final raw = dotenv.env['SUPABASE_URL']?.trim() ?? '';
    final uri = Uri.tryParse(raw);
    if (uri == null) {
      return raw;
    }
    final normalizedPath = uri.path.replaceAll(RegExp(r'/+$'), '');
    if (normalizedPath == '/rest/v1') {
      return uri.replace(path: '', query: null, fragment: null).toString();
    }
    return raw.replaceAll(RegExp(r'/+$'), '');
  }

  static String get supabaseAnonKey =>
      dotenv.env['SUPABASE_ANON_KEY']?.trim() ?? '';

  static bool get isSupabaseConfigured {
    final uri = Uri.tryParse(supabaseUrl);
    return uri != null &&
        uri.hasScheme &&
        uri.host.endsWith('.supabase.co') &&
        !supabaseUrl.toLowerCase().contains('your-project') &&
        supabaseAnonKey.isNotEmpty &&
        !supabaseAnonKey.toLowerCase().contains('your-');
  }
}
