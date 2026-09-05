import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;

import '../config/remote_config.dart';
import '../models/farmer_report.dart';
import 'oss_upload_service.dart';
import 'report_storage_service.dart';

/// Offline queue + retry mechanism for report syncing.
///
/// Sync payload = crop image + transcribed TEXT answers + crop + GPS +
/// timestamp. Audio is NEVER uploaded (it is deleted after transcription).
///
/// ```text
/// Report saved locally (always first, works with zero internet)
///        ↓
/// tryUploadNow()  ── online ──> OSS image + report metadata → synced
///        ↓ offline / failure
/// sync_status = pending_sync (retries counted)   ← "Pending Sync"
///        ↓ app start / reports tab open
/// retryPending() processes the queue again
///        ↓ retries exhausted
/// sync_status = failed (manual retry still possible)
/// ```
class UploadQueueService {
  static final UploadQueueService instance = UploadQueueService._();
  UploadQueueService._();

  bool _busy = false;

  /// Tries to sync one report right after saving. Failures are
  /// non-blocking: the report stays pending_sync in the local queue.
  Future<FarmerReport> enqueueAndTry(FarmerReport report) async {
    try {
      return await _upload(report);
    } catch (e) {
      debugPrint('[upload] ${report.reportId} queued: $e');
      return report; // still 'pending_sync'
    }
  }

  /// Retries every pending report that has not exhausted its retry
  /// budget. Call on app start and whenever the reports tab is opened.
  Future<void> retryPending() async {
    if (_busy) return;
    _busy = true;
    try {
      final reports = await ReportStorageService.instance.list();
      for (final report in reports) {
        final queued = report.syncStatus == 'pending' ||
            report.syncStatus == 'pending_sync' ||
            report.syncStatus == 'failed';
        if (!queued) continue;
        if (report.imagePath == null) continue;
        if (report.uploadRetries >= RemoteConfig.maxUploadRetries &&
            report.syncStatus == 'failed') {
          continue; // manual retry only
        }
        try {
          await _upload(report);
        } catch (e) {
          debugPrint('[upload] retry ${report.reportId} failed: $e');
        }
      }
    } finally {
      _busy = false;
    }
  }

  Future<FarmerReport> _upload(FarmerReport report) async {
    final imagePath = report.imagePath;
    final imageFile = imagePath == null ? null : File(imagePath);
    if (imageFile == null || !await imageFile.exists()) {
      debugPrint('[upload] ${report.reportId} has no local image');
      return report;
    }

    var current = report.copyWith(syncStatus: 'uploading');
    await ReportStorageService.instance.update(current);

    try {
      // 1. Crop image → OSS via Function Compute presigned URL.
      final bytes = await imageFile.readAsBytes();
      final result = await OssUploadService.instance
          .uploadImage(bytes, reportId: report.reportId);

      // 2. Report metadata: transcribed text answers + crop + GPS +
      //    timestamp. Audio is never part of this payload.
      await _postReportMetadata(report, objectKey: result.objectKey);

      current =
          current.copyWith(syncStatus: 'synced', imageOssKey: result.objectKey);
      await ReportStorageService.instance.update(current);
      return current;
    } catch (_) {
      current = current.copyWith(
        syncStatus: 'pending_sync',
        uploadRetries: report.uploadRetries + 1,
      );
      if (current.uploadRetries >= RemoteConfig.maxUploadRetries) {
        current = current.copyWith(syncStatus: 'failed');
      }
      await ReportStorageService.instance.update(current);
      rethrow;
    }
  }

  /// Sends ONLY the report metadata (text answers + crop + GPS + timestamp).
  Future<void> _postReportMetadata(FarmerReport report,
      {required String objectKey}) async {
    final payload = report.toJson()
      ..['image'] = {
        'source': imageSourceName(report.imageSource),
        'oss_key': objectKey,
      }
      ..remove('sync_status')
      ..remove('upload_retries');

    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 10);
    try {
      final uri = Uri.parse(RemoteConfig.reportSyncUrl);
      final req = await client.postUrl(uri);
      req.headers.contentType = ContentType.json;
      req.write(jsonEncode(payload));
      final res = await req.close().timeout(const Duration(seconds: 20));
      await res.drain<void>();
      if (res.statusCode != 200) {
        throw HttpException('report sync HTTP ${res.statusCode}', uri: uri);
      }
      debugPrint('[upload] ${report.reportId} metadata synced (text only)');
    } finally {
      client.close(force: true);
    }
  }
}
