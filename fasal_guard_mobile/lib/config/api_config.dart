/// Backend API configuration.
///
/// All endpoint URLs are derived from a single [baseUrl] so switching
/// between the Android-emulator loopback and a physical-phone LAN address
/// requires changing ONE constant.
///
/// Android emulator  → http://10.0.2.2:8000
/// Physical phone    → http://<your-PC-LAN-IP>:8000
///
/// Override at compile time:
///   flutter run --dart-define=BACKEND_HOST=192.168.1.42:8000
class ApiConfig {
  ApiConfig._();

  static const String _host = String.fromEnvironment(
    'BACKEND_HOST',
    defaultValue: '10.0.2.2:8000',
  );

  static const String baseUrl = 'http://$_host';

  // ── Device ──────────────────────────────────────────────
  static String get deviceRegisterUrl => '$baseUrl/api/v1/devices/register';

  static String locationUpdateUrl(String deviceId) =>
      '$baseUrl/api/v1/devices/$deviceId/location';

  // ── Reports ─────────────────────────────────────────────
  static String get reportProcessUrl => '$baseUrl/api/v1/reports/process';

  // ── Notifications ───────────────────────────────────────
  static String notificationsUrl(String deviceId) =>
      '$baseUrl/api/v1/devices/$deviceId/notifications';

  static String markReadUrl(String notificationId) =>
      '$baseUrl/api/v1/notifications/$notificationId/read';
}
