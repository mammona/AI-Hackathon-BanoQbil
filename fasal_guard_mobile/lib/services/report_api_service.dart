import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;

import '../config/api_config.dart';
import '../models/farmer_report.dart';

/// Submits farmer reports to the backend via multipart POST.
///
/// Uses manual multipart/form-data encoding with `dart:io HttpClient`
/// since we do not depend on the `http` or `dio` packages.
class ReportApiService {
  static final ReportApiService instance = ReportApiService._();
  ReportApiService._();

  /// Submits a report with optional image bytes (fire-and-forget).
  ///
  /// At least one answer with non-empty text OR [imageBytes] must be
  /// present; otherwise the call returns immediately.
  Future<void> submit(
    FarmerReport report, {
    Uint8List? imageBytes,
    required String deviceId,
  }) async {
    // Validate: need at least one non-empty answer or an image.
    final hasAnswer = report.answers.any((a) => a.answerText.trim().isNotEmpty);
    if (!hasAnswer && imageBytes == null) return;

    final boundary = '----FasalGuard${DateTime.now().microsecondsSinceEpoch}';

    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 10);
    try {
      final uri = Uri.parse(ApiConfig.reportProcessUrl);
      final req = await client.postUrl(uri);
      req.headers.contentType = ContentType(
        'multipart',
        'form-data',
        parameters: {'boundary': boundary},
      );

      final body = StringBuffer();

      // Helper: write a text field using strict RFC 2046 framing.
      void writeField(String name, String value) {
        body.write('--$boundary\r\n');
        body.write('Content-Disposition: form-data; name="$name"\r\n');
        body.write('\r\n'); // Blank line separating headers from body.
        body.write('$value\r\n');
      }

      // Required scalar fields.
      writeField('report_id', report.reportId);
      writeField('device_id', deviceId);
      writeField('selected_crop', report.cropId);
      writeField('language', 'pa');
      writeField('timestamp', report.capturedAt.toIso8601String());

      // Answer fields: answer_1 … answer_4.
      for (var i = 0; i < report.answers.length && i < 4; i++) {
        final text = report.answers[i].answerText.trim();
        if (text.isNotEmpty) {
          writeField('answer_${i + 1}', text);
        }
      }

      // Location.
      final loc = report.location;
      if (loc != null) {
        if (loc.latitude != null) {
          writeField('latitude', loc.latitude.toString());
        }
        if (loc.longitude != null) {
          writeField('longitude', loc.longitude.toString());
        }
      }

      // Build byte payload.
      final List<int> payload = [];
      payload.addAll(utf8.encode(body.toString()));

      // Image file part (only if imageBytes present).
      if (imageBytes != null) {
        final imagePart = StringBuffer();
        imagePart.write('--$boundary\r\n');
        imagePart.write(
          'Content-Disposition: form-data; name="image"; filename="crop.jpg"\r\n',
        );
        imagePart.write('Content-Type: image/jpeg\r\n');
        imagePart.write('\r\n'); // Blank line separating headers from body.
        payload.addAll(utf8.encode(imagePart.toString()));
        payload.addAll(imageBytes);
        payload.addAll(utf8.encode('\r\n'));
      }

      // Closing boundary.
      payload.addAll(utf8.encode('--$boundary--\r\n'));

      req.headers.contentLength = payload.length;
      req.add(payload);

      final res = await req.close().timeout(const Duration(seconds: 30));
      await res.drain<void>();
      debugPrint('[report-api] submit status ${res.statusCode}');
    } catch (e) {
      debugPrint('[report-api] submit error: $e');
    } finally {
      client.close(force: true);
    }
  }
}
