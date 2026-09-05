import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';

import 'package:fasal_guard_mobile/models/farmer_notification.dart';

/// Tests for RED notification retrieval: parsing backend payloads, JSON
/// round-trips, notification_id de-duplication, and the manual Hive
/// [FarmerNotificationAdapter].
void main() {
  group('FarmerNotification.fromJson (RED alert payload)', () {
    test('parses every field of a RED notification', () {
      final redJson = {
        'notification_id': 'ntf_red_001',
        'alert_id': 'alert_20260904_red',
        'crop': 'cotton',
        'title': 'Red alert: cotton leaf curl confirmed 2.5 km away',
        'message':
            'A severe cotton disease was confirmed near your village. '
            'Inspect the underside of leaves.',
        'message_local': 'تہاڈے پنڈ دے نیڑے کپاہ دی بیماری دی تصدیق ہوئی اے۔',
        'distance_km': 2.5,
        'status': 'red',
        'created_at': '2026-09-04T08:15:30.000Z',
      };

      final n = FarmerNotification.fromJson(redJson);

      expect(n.notificationId, 'ntf_red_001');
      expect(n.alertId, 'alert_20260904_red');
      expect(n.crop, 'cotton');
      expect(n.title, 'Red alert: cotton leaf curl confirmed 2.5 km away');
      expect(
        n.message,
        'A severe cotton disease was confirmed near your village. '
        'Inspect the underside of leaves.',
      );
      expect(
        n.messageLocal,
        'تہاڈے پنڈ دے نیڑے کپاہ دی بیماری دی تصدیق ہوئی اے۔',
      );
      expect(n.distanceKm, 2.5);
      expect(n.status, 'red');
      expect(n.createdAt, DateTime.parse('2026-09-04T08:15:30.000Z'));
      expect(n.readAt, isNull);
    });

    test('a RED alert counts as unread for the badge count', () {
      // NotificationCacheService.unreadCount treats anything that is not
      // 'read' as unread — including the 'red' alert severity.
      final n = FarmerNotification.fromJson({
        'notification_id': 'ntf_red_002',
        'title': 't',
        'message': 'm',
        'status': 'red',
        'created_at': '2026-09-04T09:00:00.000Z',
      });
      expect(n.status != 'read', isTrue);
    });

    test('missing optional fields fall back to safe defaults', () {
      final n = FarmerNotification.fromJson({
        'notification_id': 'ntf_minimal',
        'created_at': '2026-09-04T09:30:00.000Z',
      });

      expect(n.notificationId, 'ntf_minimal');
      expect(n.alertId, isNull);
      expect(n.crop, isNull);
      expect(n.title, '');
      expect(n.message, '');
      expect(n.messageLocal, isNull);
      expect(n.distanceKm, isNull);
      expect(n.status, 'unread');
      expect(n.readAt, isNull);
    });
  });

  group('FarmerNotification JSON round-trip', () {
    test('toJson() -> fromJson() preserves all 10 fields', () {
      final original = FarmerNotification(
        notificationId: 'ntf_round_trip',
        alertId: 'alert_round_trip',
        crop: 'rice',
        title: 'Rice blast detected nearby',
        message: 'A rice blast outbreak was confirmed within 1 km.',
        messageLocal: 'دھان وچ بلاسٹ دی تصدیق۔',
        distanceKm: 1.25,
        status: 'red',
        createdAt: DateTime.utc(2026, 9, 2, 6, 30),
        readAt: DateTime.utc(2026, 9, 2, 7, 0),
      );

      final decoded = FarmerNotification.fromJson(
        jsonDecode(jsonEncode(original.toJson())) as Map<String, dynamic>,
      );

      expect(decoded.notificationId, original.notificationId);
      expect(decoded.alertId, original.alertId);
      expect(decoded.crop, original.crop);
      expect(decoded.title, original.title);
      expect(decoded.message, original.message);
      expect(decoded.messageLocal, original.messageLocal);
      expect(decoded.distanceKm, original.distanceKm);
      expect(decoded.status, original.status);
      expect(decoded.createdAt, original.createdAt);
      expect(decoded.readAt, original.readAt);
    });
  });

  group('duplicate prevention by notification_id', () {
    test('re-putting the same notification_id keeps one latest entry', () {
      final first = FarmerNotification(
        notificationId: 'ntf_dup',
        title: 'First fetch title',
        message: 'm',
        createdAt: DateTime.utc(2026, 9, 4, 8),
      );
      final refreshed = FarmerNotification(
        notificationId: 'ntf_dup', // same backend notification
        title: 'Refreshed title',
        message: 'm',
        createdAt: DateTime.utc(2026, 9, 4, 8),
      );

      // A Hive box keyed by notificationId behaves like this map.
      final byId = <String, FarmerNotification>{};
      byId[first.notificationId] = first;
      byId[refreshed.notificationId] = refreshed;

      expect(byId.length, 1);
      expect(byId.values.single.title, 'Refreshed title');
    });

    test('different notification_ids stay separate entries', () {
      final a = FarmerNotification(
        notificationId: 'ntf_a',
        title: 'A',
        message: 'm',
        createdAt: DateTime.utc(2026, 9, 4, 8),
      );
      final b = FarmerNotification(
        notificationId: 'ntf_b',
        title: 'B',
        message: 'm',
        createdAt: DateTime.utc(2026, 9, 4, 9),
      );

      final byId = <String, FarmerNotification>{};
      byId[a.notificationId] = a;
      byId[b.notificationId] = b;

      expect(byId.length, 2);
      expect(byId.keys.toSet(), {'ntf_a', 'ntf_b'});
    });
  });

  group('FarmerNotificationAdapter (Hive TypeAdapter)', () {
    late Directory tempDir;

    setUpAll(() async {
      tempDir = await Directory.systemTemp.createTemp('fasal_notif_fetch');
      Hive.init(tempDir.path);
      if (!Hive.isAdapterRegistered(FarmerNotificationAdapter().typeId)) {
        Hive.registerAdapter(FarmerNotificationAdapter());
      }
    });

    tearDownAll(() async {
      await Hive.close();
      try {
        await tempDir.delete(recursive: true);
      } catch (_) {
        // Best effort: on Windows an AV scan can briefly hold the handle.
        // The directory lives in the OS temp dir anyway.
      }
    });

    test('uses typeId 1, matching NotificationCacheService.init()', () {
      // NotificationCacheService.init() guards with
      // Hive.isAdapterRegistered(1) — a different typeId would break the
      // no-double-registration contract.
      expect(FarmerNotificationAdapter().typeId, 1);
    });

    test('writes and reads a RED notification back from disk', () async {
      final original = FarmerNotification(
        notificationId: 'ntf_hive_red',
        alertId: 'alert_hive_red',
        crop: 'cotton',
        title: 'RED alert cached offline',
        message: 'Severe pest outbreak confirmed near your field.',
        messageLocal: 'تہاڈے کھیت دے نیڑے کیڑیاں دا شدید حملہ',
        distanceKm: 3.75,
        status: 'red',
        createdAt: DateTime.utc(2026, 9, 1, 5, 15),
      );

      final box = await Hive.openBox<FarmerNotification>('notif_adapter_red');
      await box.put(original.notificationId, original);

      // In-memory read (served from the box cache).
      final live = box.get(original.notificationId);
      expect(live, isNotNull);
      expect(live!.title, 'RED alert cached offline');

      // Full disk round-trip: close the box (flush + release the file),
      // reopen it (every frame is re-read and deserialized by the
      // adapter), then compare.
      await box.close();
      final reopened = await Hive.openBox<FarmerNotification>(
        'notif_adapter_red',
      );
      final reread = reopened.get(original.notificationId);

      expect(reread, isNotNull);
      expect(reread!.notificationId, 'ntf_hive_red');
      expect(reread.alertId, 'alert_hive_red');
      expect(reread.crop, 'cotton');
      expect(reread.title, 'RED alert cached offline');
      expect(reread.message, 'Severe pest outbreak confirmed near your field.');
      expect(reread.messageLocal, 'تہاڈے کھیت دے نیڑے کیڑیاں دا شدید حملہ');
      expect(reread.distanceKm, 3.75);
      expect(reread.status, 'red');
      // Hive's DateTime adapter stores milliseconds since epoch and drops
      // the UTC flag, so compare the moment, not the DateTime identity.
      expect(
        reread.createdAt.millisecondsSinceEpoch,
        original.createdAt.millisecondsSinceEpoch,
      );
      expect(reread.readAt, isNull);

      await reopened.close();
    });

    test('round-trips read state (status and readAt)', () async {
      final readAt = DateTime.utc(2026, 9, 1, 6, 0);
      final original = FarmerNotification(
        notificationId: 'ntf_hive_read',
        title: 'Read notification',
        message: 'm',
        distanceKm: 0.5,
        status: 'read',
        createdAt: DateTime.utc(2026, 9, 1, 5, 0),
        readAt: readAt,
      );

      final box = await Hive.openBox<FarmerNotification>('notif_adapter_read');
      await box.put(original.notificationId, original);
      await box.close();

      final reopened = await Hive.openBox<FarmerNotification>(
        'notif_adapter_read',
      );
      final reread = reopened.get(original.notificationId);

      expect(reread, isNotNull);
      expect(reread!.status, 'read');
      expect(
        reread.readAt!.millisecondsSinceEpoch,
        readAt.millisecondsSinceEpoch,
      );
      await reopened.close();
    });

    test('a real Hive box de-duplicates by notification_id', () async {
      final first = FarmerNotification(
        notificationId: 'ntf_box_dup',
        title: 'Old title',
        message: 'm',
        createdAt: DateTime.utc(2026, 9, 4, 8),
      );
      final refreshed = FarmerNotification(
        notificationId: 'ntf_box_dup',
        title: 'Latest title',
        message: 'm',
        createdAt: DateTime.utc(2026, 9, 4, 8),
      );

      final box = await Hive.openBox<FarmerNotification>('notif_adapter_dedup');
      await box.put(first.notificationId, first);
      await box.put(refreshed.notificationId, refreshed);

      expect(box.length, 1);
      expect(box.values.single.title, 'Latest title');
      await box.close();
    });
  });
}
