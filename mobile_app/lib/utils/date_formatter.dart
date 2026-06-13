import 'package:intl/intl.dart';

class DateFormatter {
  const DateFormatter._();

  static String articleDate(DateTime value) {
    return DateFormat('dd MMM yyyy, HH:mm').format(value.toLocal());
  }
}
