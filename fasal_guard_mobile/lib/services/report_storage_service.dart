import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:path_provider/path_provider.dart';

import '../models/farmer_report.dart';

/// Local report persistence. Every completed report lives in its own
/// folder containing ONLY the JSON report and the crop image:
///
/// ```text
/// <app docs>/reports/<report_id>/
/// ├── report.json
/// └── crop_image.jpg
/// ```
///
/// Farmer answers are transcribed locally by Sherpa ONNX and never stored
/// as audio. JSON reports stay local in this prototype; only the crop
/// image + text metadata are synced (see UploadQueueService).
class ReportStorageService {
  static final ReportStorageService instance = ReportStorageService._();
  ReportStorageService._();

  Future<Directory> _reportsDir() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory('${docs.path}/reports');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  /// Saves the crop image into the report folder, then writes report.json.
  Future<FarmerReport> save(FarmerReport report,
      {Uint8List? imageBytes}) async {
    final base = await _reportsDir();
    final dir = Directory('${base.path}/${report.reportId}');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }

    // 1. Crop image.
    String? imagePath;
    if (imageBytes != null) {
      final file = File('${dir.path}/crop_image.jpg');
      await file.writeAsBytes(imageBytes);
      imagePath = file.path;
    }

    // 2. report.json (answers already carry STT text, not audio paths).
    final json = report.toJson();
    json['image'] = {
      'source': json['image']['source'],
      'local_path': imagePath,
      'oss_key': report.imageOssKey,
    };
    final reportFile = File('${dir.path}/report.json');
    await reportFile.writeAsString(jsonEncode(json));
    debugPrint('[report] saved ${report.reportId} at ${dir.path}');

    return FarmerReport.fromJson(json);
  }

  /// Rewrites report.json after a sync-status/OSS-key update.
  Future<void> update(FarmerReport report) async {
    final base = await _reportsDir();
    final file = File('${base.path}/${report.reportId}/report.json');
    if (!await file.exists()) {
      debugPrint('[report] update skipped, missing ${report.reportId}');
      return;
    }
    await file.writeAsString(jsonEncode(report.toJson()));
  }

  /// All saved reports, newest first. Broken folders are skipped, never
  /// allowed to crash the reports tab.
  Future<List<FarmerReport>> list() async {
    final base = await _reportsDir();
    final reports = <FarmerReport>[];
    if (!await base.exists()) return reports;
    await for (final entry in base.list()) {
      if (entry is! Directory) continue;
      final file = File('${entry.path}/report.json');
      if (!await file.exists()) continue;
      try {
        final json = jsonDecode(await file.readAsString());
        reports.add(FarmerReport.fromJson(json as Map<String, dynamic>));
      } catch (e) {
        debugPrint('[report] skipping broken report ${entry.path}: $e');
      }
    }
    reports.sort((a, b) => b.capturedAt.compareTo(a.capturedAt));
    return reports;
  }

  /// Removes the whole report folder (json + image).
  Future<void> delete(String reportId) async {
    final base = await _reportsDir();
    final dir = Directory('${base.path}/$reportId');
    if (await dir.exists()) {
      await dir.delete(recursive: true);
      debugPrint('[report] deleted $reportId');
    }
  }
}
