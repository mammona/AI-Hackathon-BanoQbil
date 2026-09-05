import 'package:hive_ce/hive.dart';
import 'package:hive_ce_flutter/hive_ce_flutter.dart';

import '../models/farmer_notification.dart';

/// Hive-based local notification storage.
///
/// Keeps a persistent box of [FarmerNotification] objects so the UI can
/// render notifications even when the device is offline.
class NotificationCacheService {
  static final NotificationCacheService instance = NotificationCacheService._();
  NotificationCacheService._();

  late Box<FarmerNotification> _box;

  /// Opens (or creates) the Hive box and registers the adapter.
  Future<void> init() async {
    await Hive.initFlutter();
    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(FarmerNotificationAdapter());
    }
    _box = await Hive.openBox<FarmerNotification>('notifications');
  }

  /// Merges server notifications into the local box.
  ///
  /// Existing entries keep their local read state when already marked read.
  Future<void> upsertAll(List<FarmerNotification> serverNotifications) async {
    for (final incoming in serverNotifications) {
      final existing = _box.get(incoming.notificationId);
      if (existing != null && existing.status == 'read') {
        // Preserve local read state.
        incoming.status = 'read';
        incoming.readAt = existing.readAt;
      }
      await _box.put(incoming.notificationId, incoming);
    }
  }

  /// Returns all cached notifications, newest first.
  List<FarmerNotification> getAll() =>
      _box.values.toList()..sort((a, b) => b.createdAt.compareTo(a.createdAt));

  /// Marks a single notification as read.
  Future<void> markRead(String notificationId, DateTime readAt) async {
    final n = _box.get(notificationId);
    if (n == null) return;
    n.status = 'read';
    n.readAt = readAt;
    await _box.put(notificationId, n);
  }

  /// Count of unread notifications.
  int get unreadCount => _box.values.where((n) => n.status != 'read').length;
}
