import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;

import '../models/farmer_report.dart';
import 'device_service.dart';
import 'report_api_service.dart';
import 'report_storage_service.dart';

/// Offline queue + retry mechanism for report syncing.
///
/// Connects to the backend via ReportApiService.
class UploadQueueService {
  static final UploadQueueService instance = UploadQueueService._();
  UploadQueueService._();

  bool _busy = false;

  /// Tries to sync one report right after saving.
  Future<FarmerReport> enqueueAndTry(FarmerReport report) async {
    try {
      return await _upload(report);
    } catch (e) {
      debugPrint('[upload] ${report.reportId} queued: $e');
      return report;
    }
  }

  /// Retries pending reports.
  Future<void> retryPending() async {
    if (_busy) return;
    _busy = true;
    try {
      final reports = await ReportStorageService.instance.list();
      for (final report in reports) {
        if (report.syncStatus == 'synced') continue;
        
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
    var current = report.copyWith(syncStatus: 'uploading');
    await ReportStorageService.instance.update(current);

    try {
      final imagePath = report.imagePath;
      final imageFile = imagePath == null ? null : File(imagePath);
      final bytes = (imageFile != null && await imageFile.exists())
          ? await imageFile.readAsBytes()
          : null;

      // Submit to backend using the new unified multipart API.
      await ReportApiService.instance.submit(
        report,
        imageBytes: bytes,
        deviceId: DeviceService.instance.deviceId,
      );

      current = current.copyWith(syncStatus: 'synced');
      await ReportStorageService.instance.update(current);
      
      debugPrint('[upload] ${report.reportId} synced successfully');
      return current;
    } catch (_) {
      current = current.copyWith(syncStatus: 'failed');
      await ReportStorageService.instance.update(current);
      rethrow;
    }
  }
}
