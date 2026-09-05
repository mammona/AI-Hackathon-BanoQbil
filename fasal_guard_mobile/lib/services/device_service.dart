import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../config/api_config.dart';

/// Device registration service.
///
/// Generates a persistent UUID device_id on first launch, stores it in
/// SharedPreferences, and registers the device with the backend.
class DeviceService {
  static final DeviceService instance = DeviceService._();
  DeviceService._();

  String? _deviceId;

  /// The unique device identifier. Must call [init] before accessing.
  String get deviceId => _deviceId!;

  /// Loads or generates the device_id from SharedPreferences.
  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _deviceId = prefs.getString('device_id');
    if (_deviceId == null) {
      _deviceId = const Uuid().v4();
      await prefs.setString('device_id', _deviceId!);
    }
  }

  /// Registers this device with the backend (fire-and-forget).
  Future<void> register({
    required List<String> crops,
    required String language,
    double? lat,
    double? lon,
    bool notificationsEnabled = true,
  }) async {
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 10);
    try {
      final uri = Uri.parse(ApiConfig.deviceRegisterUrl);
      final req = await client.postUrl(uri);
      req.headers.contentType = ContentType.json;
      req.write(
        jsonEncode({
          'device_id': deviceId,
          'crops': crops,
          'preferred_language': language,
          'latitude': lat,
          'longitude': lon,
          'notifications_enabled': notificationsEnabled,
        }),
      );
      final res = await req.close().timeout(const Duration(seconds: 15));
      await res.drain<void>();
      debugPrint('[device] register status ${res.statusCode}');
    } catch (e) {
      debugPrint('[device] register error: $e');
    } finally {
      client.close(force: true);
    }
  }
}
