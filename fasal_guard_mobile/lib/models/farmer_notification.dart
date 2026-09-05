import 'package:hive_ce/hive.dart';

/// A notification received from the backend alert system.
class FarmerNotification {
  final String notificationId;
  final String? alertId;
  final String? crop;
  final String title;
  final String message;
  final String? messageLocal;
  final double? distanceKm;
  String status; // 'unread' | 'read'
  final DateTime createdAt;
  DateTime? readAt;

  FarmerNotification({
    required this.notificationId,
    this.alertId,
    this.crop,
    required this.title,
    required this.message,
    this.messageLocal,
    this.distanceKm,
    this.status = 'unread',
    required this.createdAt,
    this.readAt,
  });

  factory FarmerNotification.fromJson(Map<String, dynamic> json) =>
      FarmerNotification(
        notificationId: json['notification_id'] as String,
        alertId: json['alert_id'] as String?,
        crop: json['crop'] as String?,
        title: json['title'] as String? ?? '',
        message: json['message'] as String? ?? '',
        messageLocal: json['message_local'] as String?,
        distanceKm: (json['distance_km'] as num?)?.toDouble(),
        status: json['status'] as String? ?? 'unread',
        createdAt:
            DateTime.tryParse(json['created_at'] as String? ?? '') ??
            DateTime.now(),
        readAt: json['read_at'] == null
            ? null
            : DateTime.tryParse(json['read_at'] as String),
      );

  Map<String, dynamic> toJson() => {
    'notification_id': notificationId,
    'alert_id': alertId,
    'crop': crop,
    'title': title,
    'message': message,
    'message_local': messageLocal,
    'distance_km': distanceKm,
    'status': status,
    'created_at': createdAt.toIso8601String(),
    'read_at': readAt?.toIso8601String(),
  };
}

/// Manual Hive TypeAdapter (no codegen).
class FarmerNotificationAdapter extends TypeAdapter<FarmerNotification> {
  @override
  final int typeId = 1;

  @override
  FarmerNotification read(BinaryReader reader) {
    final numFields = reader.readByte();
    final fields = <int, dynamic>{};
    for (var i = 0; i < numFields; i++) {
      fields[reader.readByte()] = reader.read();
    }
    return FarmerNotification(
      notificationId: fields[0] as String,
      alertId: fields[1] as String?,
      crop: fields[2] as String?,
      title: fields[3] as String,
      message: fields[4] as String,
      messageLocal: fields[5] as String?,
      distanceKm: fields[6] as double?,
      status: fields[7] as String? ?? 'unread',
      createdAt: fields[8] as DateTime,
      readAt: fields[9] as DateTime?,
    );
  }

  @override
  void write(BinaryWriter writer, FarmerNotification obj) {
    writer.writeByte(10); // number of fields
    writer.writeByte(0);
    writer.write(obj.notificationId);
    writer.writeByte(1);
    writer.write(obj.alertId);
    writer.writeByte(2);
    writer.write(obj.crop);
    writer.writeByte(3);
    writer.write(obj.title);
    writer.writeByte(4);
    writer.write(obj.message);
    writer.writeByte(5);
    writer.write(obj.messageLocal);
    writer.writeByte(6);
    writer.write(obj.distanceKm);
    writer.writeByte(7);
    writer.write(obj.status);
    writer.writeByte(8);
    writer.write(obj.createdAt);
    writer.writeByte(9);
    writer.write(obj.readAt);
  }
}
