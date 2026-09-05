import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';

import 'package:fasal_guard_mobile/models/farmer_notification.dart';

/// Tests for read-state handling of cached notifications: marking a
/// notification as read keeps it in the list, and a server re-fetch must
/// never reset the local read state.
///
/// The helpers below mirror the exact logic of
/// NotificationCacheService.markRead / upsertAll / getAll. (The service
/// itself cannot be used in plain tests because init() calls
/// Hive.initFlutter(), which needs the path_provider plugin.)
void main() {
  late Directory tempDir;
  late Box<FarmerNotification> box;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('fasal_notif_read');
    Hive.init(tempDir.path);
    if (!Hive.isAdapterRegistered(FarmerNotificationAdapter().typeId)) {
      Hive.registerAdapter(FarmerNotificationAdapter());
    }
    // Same box name the app uses — each test gets a fresh temp directory.
    box = await Hive.openBox<FarmerNotification>('notifications');
  });

  tearDown(() async {
    await Hive.close();
    try {
      await tempDir.delete(recursive: true);
    } catch (_) {
      // Best effort on Windows: the directory lives in the OS temp dir.
    }
  });

  /// Mirrors NotificationCacheService.markRead().
  Future<void> markRead(String notificationId, DateTime readAt) async {
    final n = box.get(notificationId);
    if (n == null) return;
    n.status = 'read';
    n.readAt = readAt;
    await box.put(notificationId, n);
  }

  /// Mirrors NotificationCacheService.upsertAll(): server content wins,
  /// but a locally-read notification keeps its read state.
  Future<void> upsertAll(List<FarmerNotification> incoming) async {
    for (final n in incoming) {
      final existing = box.get(n.notificationId);
      if (existing != null && existing.status == 'read') {
        // Preserve local read state.
        n.status = 'read';
        n.readAt = existing.readAt;
      }
      await box.put(n.notificationId, n);
    }
  }

  /// Mirrors NotificationCacheService.getAll(): newest first.
  List<FarmerNotification> getAll() =>
      box.values.toList()..sort((a, b) => b.createdAt.compareTo(a.createdAt));

  FarmerNotification unreadNotification({
    required String id,
    required DateTime createdAt,
    String title = 'Alert',
  }) => FarmerNotification(
    notificationId: id,
    crop: 'cotton',
    title: title,
    message: 'message for $id',
    messageLocal: 'پیغام $id',
    distanceKm: 2.0,
    status: 'unread',
    createdAt: createdAt,
  );

  group('markRead', () {
    test('updates status and readAt', () async {
      final notification = unreadNotification(
        id: 'ntf_mark_read',
        createdAt: DateTime(2026, 9, 4, 8, 0),
      );
      await box.put(notification.notificationId, notification);

      final readAt = DateTime(2026, 9, 4, 12, 30);
      await box.put(
        notification.notificationId,
        notification
          ..status = 'read'
          ..readAt = readAt,
      );

      final updated = box.get('ntf_mark_read');
      expect(updated, isNotNull);
      expect(updated!.status, 'read');
      expect(updated.readAt, readAt);
    });

    test('persists to disk and survives a box reopen', () async {
      final notification = unreadNotification(
        id: 'ntf_disk_read',
        createdAt: DateTime(2026, 9, 4, 8, 0),
      );
      await box.put(notification.notificationId, notification);

      final readAt = DateTime(2026, 9, 4, 12, 31);
      await markRead('ntf_disk_read', readAt);

      await box.close();
      final reopened = await Hive.openBox<FarmerNotification>('notifications');
      final reread = reopened.get('ntf_disk_read');

      expect(reread, isNotNull);
      expect(reread!.status, 'read');
      expect(
        reread.readAt!.millisecondsSinceEpoch,
        readAt.millisecondsSinceEpoch,
      );
      await reopened.close();
    });

    test('is a no-op for an unknown notification id', () async {
      // NotificationCacheService.markRead returns silently on a miss.
      await markRead('ntf_missing', DateTime(2026, 9, 4, 13));
      expect(box.get('ntf_missing'), isNull);
      expect(box.length, 0);
    });
  });

  group('notification visibility after read', () {
    test('a read notification remains in the list', () async {
      final older = unreadNotification(
        id: 'ntf_older',
        createdAt: DateTime(2026, 9, 3, 8, 0),
      );
      final newer = unreadNotification(
        id: 'ntf_newer',
        createdAt: DateTime(2026, 9, 4, 9, 0),
      );
      await box.put(older.notificationId, older);
      await box.put(newer.notificationId, newer);

      await markRead('ntf_newer', DateTime(2026, 9, 4, 12, 0));

      final list = box.values.toList();
      expect(list, hasLength(2));
      expect(list.map((n) => n.notificationId).toSet(), {
        'ntf_older',
        'ntf_newer',
      }, reason: 'marking as read must never remove the notification');

      // getAll() pattern: newest first, the read notification still on top.
      final sorted = getAll();
      expect(sorted.first.notificationId, 'ntf_newer');
      expect(sorted.first.status, 'read');

      // unreadCount pattern: only the unread one remains.
      final unread = sorted.where((n) => n.status != 'read').toList();
      expect(unread, hasLength(1));
      expect(unread.single.notificationId, 'ntf_older');
    });
  });

  group('server re-fetch preserves local read state', () {
    test('a locally-read notification stays read after a re-fetch', () async {
      final readAt = DateTime(2026, 9, 4, 12, 0);
      final local = FarmerNotification(
        notificationId: 'ntf_refetch',
        alertId: 'alert_refetch',
        crop: 'cotton',
        title: 'Original server title',
        message: 'm',
        messageLocal: 'پیغام',
        distanceKm: 2.5,
        status: 'read',
        createdAt: DateTime(2026, 9, 4, 8, 0),
        readAt: readAt,
      );
      await box.put(local.notificationId, local);

      // Server re-fetch: same notification, but the server does not know
      // about the local read state and sends 'unread' + refreshed content.
      final serverCopy = unreadNotification(
        id: 'ntf_refetch',
        createdAt: DateTime(2026, 9, 4, 8, 0),
        title: 'Refreshed server title',
      );
      await upsertAll([serverCopy]);

      final merged = box.get('ntf_refetch');
      expect(merged, isNotNull);
      expect(
        merged!.status,
        'read',
        reason: 'local read state must survive a server re-fetch',
      );
      expect(merged.readAt, readAt);
      expect(
        merged.title,
        'Refreshed server title',
        reason: 'server content wins; only the read state is preserved',
      );
    });

    test(
      'a mixed batch keeps local read state and server state for new ones',
      () async {
        final readAt = DateTime(2026, 9, 4, 11, 0);
        final readLocal = FarmerNotification(
          notificationId: 'ntf_seen',
          title: 'Seen locally',
          message: 'm',
          status: 'read',
          createdAt: DateTime(2026, 9, 4, 7, 0),
          readAt: readAt,
        );
        await box.put(readLocal.notificationId, readLocal);

        await upsertAll([
          // Already read locally -> stays read.
          unreadNotification(
            id: 'ntf_seen',
            createdAt: DateTime(2026, 9, 4, 7, 0),
            title: 'Seen refreshed',
          ),
          // Never seen before -> keeps the server (unread) state.
          unreadNotification(
            id: 'ntf_fresh',
            createdAt: DateTime(2026, 9, 4, 10, 0),
            title: 'Fresh alert',
          ),
        ]);

        expect(box.length, 2);
        expect(box.get('ntf_seen')!.status, 'read');
        expect(
          box.get('ntf_seen')!.readAt!.millisecondsSinceEpoch,
          readAt.millisecondsSinceEpoch,
        );
        expect(box.get('ntf_fresh')!.status, 'unread');
        expect(box.get('ntf_fresh')!.readAt, isNull);
      },
    );

    test('read state survives a restart after the re-fetch', () async {
      final readAt = DateTime(2026, 9, 4, 12, 0);
      final local = FarmerNotification(
        notificationId: 'ntf_restart',
        title: 'Original title',
        message: 'm',
        status: 'read',
        createdAt: DateTime(2026, 9, 4, 8, 0),
        readAt: readAt,
      );
      await box.put(local.notificationId, local);

      await upsertAll([
        unreadNotification(
          id: 'ntf_restart',
          createdAt: DateTime(2026, 9, 4, 8, 0),
          title: 'Refreshed after restart',
        ),
      ]);

      await box.close();
      final reopened = await Hive.openBox<FarmerNotification>('notifications');
      final after = reopened.get('ntf_restart');

      expect(after, isNotNull);
      expect(after!.status, 'read');
      expect(
        after.readAt!.millisecondsSinceEpoch,
        readAt.millisecondsSinceEpoch,
      );
      expect(after.title, 'Refreshed after restart');
      await reopened.close();
    });
  });
}
