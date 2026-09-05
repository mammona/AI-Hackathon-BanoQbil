import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;

import '../config/api_config.dart';
import '../models/farmer_notification.dart';
import 'notification_cache_service.dart';

/// Backend notification API service.
///
/// Fetches device notifications from the backend and caches them locally
/// via [NotificationCacheService]. Read-state updates are optimistically
/// applied to the local cache before the network call.
class NotificationApiService {
  static final NotificationApiService instance = NotificationApiService._();
  NotificationApiService._();

  /// Fetches notifications for [deviceId], merges into local cache, and
  /// returns the full sorted list.
  Future<List<FarmerNotification>> fetchNotifications(String deviceId) async {
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 10);
    try {
      final uri = Uri.parse(ApiConfig.notificationsUrl(deviceId));
      final req = await client.getUrl(uri);
      final res = await req.close().timeout(const Duration(seconds: 15));
      final body = await res.transform(utf8.decoder).join();

      if (res.statusCode != 200) {
        throw HttpException(
          'notifications HTTP ${res.statusCode}: $body',
          uri: uri,
        );
      }

      final list = jsonDecode(body) as List<dynamic>;
      final parsed = list
          .map((e) => FarmerNotification.fromJson(e as Map<String, dynamic>))
          .toList();

      await NotificationCacheService.instance.upsertAll(parsed);
      return NotificationCacheService.instance.getAll();
    } catch (e) {
      debugPrint('[notif-api] fetch error: $e');
      return NotificationCacheService.instance.getAll();
    } finally {
      client.close(force: true);
    }
  }

  /// Marks a notification as read.
  ///
  /// Optimistically updates the local cache first, then POSTs to the
  /// backend. If the server returns a different `read_at` timestamp the
  /// cache is updated again.
  Future<DateTime?> markRead(String notificationId) async {
    // Optimistic local update.
    final optimisticTime = DateTime.now();
    await NotificationCacheService.instance.markRead(
      notificationId,
      optimisticTime,
    );

    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 10);
    try {
      final uri = Uri.parse(ApiConfig.markReadUrl(notificationId));
      final req = await client.postUrl(uri);
      final res = await req.close().timeout(const Duration(seconds: 15));
      final body = await res.transform(utf8.decoder).join();

      if (res.statusCode == 200) {
        final json = jsonDecode(body) as Map<String, dynamic>;
        final serverReadAt = json['read_at'] as String?;
        if (serverReadAt != null) {
          final parsed = DateTime.tryParse(serverReadAt);
          if (parsed != null) {
            await NotificationCacheService.instance.markRead(
              notificationId,
              parsed,
            );
            return parsed;
          }
        }
      }
      return optimisticTime;
    } catch (e) {
      debugPrint('[notif-api] markRead error: $e');
      // Optimistic update already applied.
      return optimisticTime;
    } finally {
      client.close(force: true);
    }
  }
}
