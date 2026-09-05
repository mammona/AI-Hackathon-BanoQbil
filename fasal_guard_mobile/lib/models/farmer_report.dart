import 'question_answer.dart';

/// How the farmer provided the crop image for this report.
enum ReportImageSource { camera, gallery }

String imageSourceName(ReportImageSource s) => switch (s) {
      ReportImageSource.camera => 'camera',
      ReportImageSource.gallery => 'gallery',
    };

ReportImageSource imageSourceFromName(String? name) => switch (name) {
      'gallery' => ReportImageSource.gallery,
      _ => ReportImageSource.camera,
    };

/// GPS capture outcome. A denied permission must never block the report;
/// it is only flagged.
class ReportLocation {
  final double? latitude;
  final double? longitude;
  final double? accuracyM;

  /// 'captured' | 'permission_denied' | 'unavailable'
  final String status;

  const ReportLocation({
    this.latitude,
    this.longitude,
    this.accuracyM,
    required this.status,
  });

  Map<String, dynamic> toJson() => {
        'latitude': latitude,
        'longitude': longitude,
        'accuracy_m': accuracyM,
        'status': status,
      };

  factory ReportLocation.fromJson(Map<String, dynamic> json) => ReportLocation(
        latitude: (json['latitude'] as num?)?.toDouble(),
        longitude: (json['longitude'] as num?)?.toDouble(),
        accuracyM: (json['accuracy_m'] as num?)?.toDouble(),
        status: json['status'] as String? ?? 'unavailable',
      );
}

/// The complete structured mobile report. Saved locally as
/// `reports/<report_id>/report.json` together with the crop image only.
///
/// Disease prediction is intentionally NOT part of this prototype: JSON
/// reports stay local, and only crop images go to Alibaba OSS.
class FarmerReport {
  final String reportId;
  final String cropId;
  final String cropName;
  final ReportImageSource imageSource;

  /// Local path of the saved crop image.
  final String? imagePath;

  /// OSS object key once the image upload has succeeded.
  final String? imageOssKey;

  final List<QuestionAnswer> answers;
  final ReportLocation? location;
  final DateTime capturedAt;

  /// 'pending_sync' | 'pending' | 'uploading' | 'synced' | 'failed'
  /// Covers the sync queue (image + text metadata); reports themselves
  /// stay local. 'pending_sync' = "Pending Sync": saved offline, will be
  /// sent when internet returns. Audio is never part of the sync payload.
  final String syncStatus;
  final int uploadRetries;

  const FarmerReport({
    required this.reportId,
    required this.cropId,
    required this.cropName,
    required this.imageSource,
    this.imagePath,
    this.imageOssKey,
    required this.answers,
    required this.location,
    required this.capturedAt,
    this.syncStatus = 'pending_sync',
    this.uploadRetries = 0,
  });

  FarmerReport copyWith({
    String? syncStatus,
    int? uploadRetries,
    String? imageOssKey,
  }) =>
      FarmerReport(
        reportId: reportId,
        cropId: cropId,
        cropName: cropName,
        imageSource: imageSource,
        imagePath: imagePath,
        imageOssKey: imageOssKey ?? this.imageOssKey,
        answers: answers,
        location: location,
        capturedAt: capturedAt,
        syncStatus: syncStatus ?? this.syncStatus,
        uploadRetries: uploadRetries ?? this.uploadRetries,
      );

  Map<String, dynamic> toJson() => {
        'report_id': reportId,
        'crop': {
          'crop_id': cropId,
          'crop_name': cropName,
          'selection_source': 'visual_crop_selection',
        },
        'image': {
          'source': imageSourceName(imageSource),
          'local_path': imagePath,
          'oss_key': imageOssKey,
        },
        'question_answers': answers.map((a) => a.toJson()).toList(),
        'location': location?.toJson(),
        'captured_at': capturedAt.toIso8601String(),
        'sync_status': syncStatus,
        'upload_retries': uploadRetries,
      };

  factory FarmerReport.fromJson(Map<String, dynamic> json) {
    final crop = json['crop'] as Map<String, dynamic>? ?? {};
    final image = json['image'] as Map<String, dynamic>? ?? {};
    final answersRaw = json['question_answers'] as List<dynamic>? ?? [];
    return FarmerReport(
      reportId: json['report_id'] as String,
      cropId: crop['crop_id'] as String? ?? '',
      cropName: crop['crop_name'] as String? ?? '',
      imageSource: imageSourceFromName(image['source'] as String?),
      imagePath: image['local_path'] as String?,
      imageOssKey: image['oss_key'] as String?,
      answers: answersRaw
          .map((a) => QuestionAnswer.fromJson(a as Map<String, dynamic>))
          .toList(),
      location: json['location'] == null
          ? null
          : ReportLocation.fromJson(json['location'] as Map<String, dynamic>),
      capturedAt: DateTime.tryParse(json['captured_at'] as String? ?? '') ??
          DateTime.now(),
      syncStatus: json['sync_status'] as String? ?? 'pending_sync',
      uploadRetries: json['upload_retries'] as int? ?? 0,
    );
  }
}
