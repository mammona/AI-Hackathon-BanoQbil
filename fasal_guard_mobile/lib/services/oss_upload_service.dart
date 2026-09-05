import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;

import '../config/remote_config.dart';

/// Result of one successful OSS image upload.
class OssUploadResult {
  /// Object key stored in OSS (kept in report.json for traceability).
  final String objectKey;
  const OssUploadResult(this.objectKey);
}

/// Uploads crop images to Alibaba OSS through a Function Compute presign
/// endpoint. The app NEVER holds an Alibaba AccessKey/AccessKey Secret:
///
/// ```text
/// Flutter ──POST filename──> Function Compute (holds credentials)
///        <──presigned PUT URL + object key──
/// Flutter ──PUT image bytes──> Alibaba OSS (direct, presigned)
/// ```
///
/// JSON reports stay local; only the crop image is uploaded.
class OssUploadService {
  static final OssUploadService instance = OssUploadService._();
  OssUploadService._();

  /// Uploads one crop image. Throws on any failure; callers drive retries.
  Future<OssUploadResult> uploadImage(Uint8List imageBytes,
      {required String reportId}) async {
    final presign = await _requestPresignedUrl(reportId);
    await _putToPresignedUrl(
        presign['upload_url'] as String, imageBytes);
    debugPrint('[oss] uploaded $reportId -> ${presign['object_key']}');
    return OssUploadResult(presign['object_key'] as String);
  }

  /// Step 1: ask Function Compute for a short-lived presigned upload URL.
  Future<Map<String, dynamic>> _requestPresignedUrl(String reportId) async {
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 10);
    try {
      final uri = Uri.parse(RemoteConfig.fcPresignUrl);
      final req = await client.postUrl(uri);
      req.headers.contentType = ContentType.json;
      req.write(jsonEncode({
        'filename': '$reportId/crop_image.jpg',
        'content_type': 'image/jpeg',
      }));
      final res = await req.close().timeout(const Duration(seconds: 20));
      final body = await res.transform(utf8.decoder).join();
      if (res.statusCode != 200) {
        throw HttpException('presign HTTP ${res.statusCode}: $body', uri: uri);
      }
      final json = jsonDecode(body) as Map<String, dynamic>;
      if ((json['upload_url'] as String? ?? '').isEmpty ||
          (json['object_key'] as String? ?? '').isEmpty) {
        throw const FormatException('presign response missing url/object_key');
      }
      return json;
    } finally {
      client.close(force: true);
    }
  }

  /// Step 2: PUT the image bytes directly to OSS with the presigned URL.
  Future<void> _putToPresignedUrl(String uploadUrl, Uint8List bytes) async {
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 15);
    try {
      final uri = Uri.parse(uploadUrl);
      final req = await client.putUrl(uri);
      req.headers.contentType = ContentType('image', 'jpeg');
      req.headers.contentLength = bytes.length;
      req.add(bytes);
      final res = await req.close().timeout(const Duration(minutes: 2));
      // Drain the response body so the socket is released.
      await res.drain<void>();
      if (res.statusCode < 200 || res.statusCode >= 300) {
        throw HttpException('OSS PUT HTTP ${res.statusCode}', uri: uri);
      }
    } finally {
      client.close(force: true);
    }
  }
}
