// Local diagnostic backend for the Fasal Guard app.
//
// This is NOT part of the Flutter app; it is a developer tool that mimics
// the real backend so you can verify — end to end — that the app actually
// sends data (device registration, GPS, report answers + image, OSS sync).
//
// It listens on BOTH host ports the app talks to:
//   * :8000  -> ApiConfig  (register / location / reports/process / notifications)
//   * :8787  -> RemoteConfig (oss/presign -> PUT upload -> /report metadata)
//
// From inside the Android emulator the host machine is reachable as
// 10.0.2.2, which is exactly what the app's config already uses.
//
// Run with the Flutter-bundled Dart SDK:
//   D:\flutter\bin\dart.bat run tool/mock_backend.dart

import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

void main() async {
  final api = await HttpServer.bind(InternetAddress.anyIPv4, 8000);
  final oss = await HttpServer.bind(InternetAddress.anyIPv4, 8787);
  _log('listening on :8000 (ApiConfig) and :8787 (RemoteConfig/OSS)');
  _log('emulator reaches this PC as http://10.0.2.2:8000 and :8787');

  api.listen((req) => _handle(req, 'API'));
  oss.listen((req) => _handle(req, 'OSS'));
}

String _ts() => DateTime.now().toIso8601String().substring(11, 23);

void _log(String msg) => stdout.writeln('[${_ts()}] $msg');

Future<void> _handle(HttpRequest req, String tag) async {
  final method = req.method;
  final path = req.uri.path;
  final ct = req.headers.contentType?.mimeType ?? 'none';
  _log('==> [$tag] $method $path  (content-type: $ct)');

  try {
    // ---- OSS presign: hand back a PUT URL that loops back to this mock ----
    if (tag == 'OSS' && method == 'POST' && path == '/oss/presign') {
      final body = await _readText(req);
      _log('    presign request body: $body');
      Map<String, dynamic> json = {};
      try {
        json = jsonDecode(body) as Map<String, dynamic>;
      } catch (_) {}
      final filename = (json['filename'] as String?) ?? 'upload/crop_image.jpg';
      final objectKey = 'mock-oss/$filename';
      final uploadUrl =
          'http://10.0.2.2:8787/oss/upload/${Uri.encodeComponent(objectKey)}';
      _replyJson(req, 200, {'upload_url': uploadUrl, 'object_key': objectKey});
      _log('    <-- issued presigned upload_url for $objectKey');
      return;
    }

    // ---- OSS direct PUT of image bytes ----
    if (tag == 'OSS' && method == 'PUT' && path.startsWith('/oss/upload')) {
      final bytes = await _readBytes(req);
      _log('    <<< RECEIVED OSS IMAGE: ${bytes.length} bytes');
      _replyJson(req, 200, {'status': 'stored', 'bytes': bytes.length});
      return;
    }

    // ---- Report metadata sync (JSON, text answers + crop + gps) ----
    if (tag == 'OSS' && method == 'POST' && path == '/report') {
      final body = await _readText(req);
      _log('    <<< RECEIVED REPORT METADATA (JSON):');
      _logIndented(_prettyJson(body));
      _replyJson(req, 200, {'status': 'received'});
      return;
    }

    // ---- Main report submission (multipart: answers + image) ----
    if (method == 'POST' && path == '/api/v1/reports/process') {
      await _handleMultipartReport(req);
      _replyJson(req, 200, {'status': 'received', 'diagnosis': 'mock'});
      return;
    }

    // ---- Notifications list ----
    if (method == 'GET' && path.contains('/notifications')) {
      _replyJson(req, 200, {'notifications': <dynamic>[]});
      _log('    <-- returned empty notifications list');
      return;
    }

    // ---- Everything else: read + echo the body so you can see it ----
    if (ct.contains('json') || ct == 'none') {
      final body = await _readText(req);
      if (body.isNotEmpty) {
        _log('    body: ${_prettyJson(body)}');
      }
    } else {
      final bytes = await _readBytes(req);
      _log('    body: ${bytes.length} bytes ($ct)');
    }
    _replyJson(req, 200, {'status': 'ok', 'path': path});
  } catch (e) {
    _log('    !! handler error: $e');
    try {
      _replyJson(req, 500, {'error': e.toString()});
    } catch (_) {}
  }
}

Future<void> _handleMultipartReport(HttpRequest req) async {
  final bytes = await _readBytes(req);
  final boundary = req.headers.contentType?.parameters['boundary'];
  _log('    <<< RECEIVED REPORT (multipart, ${bytes.length} bytes total)');
  if (boundary == null) {
    _log('    (no boundary header; cannot parse fields)');
    return;
  }
  final parts = _parseMultipart(bytes, boundary);
  for (final p in parts) {
    if (p.isImage) {
      _log(
        '    [image] name="${p.name}" filename="${p.filename}" '
        '-> ${p.data.length} bytes',
      );
    } else {
      final value = utf8.decode(p.data, allowMalformed: true);
      _log('    [field] ${p.name} = $value');
    }
  }
}

class _Part {
  final String name;
  final String? filename;
  final Uint8List data;
  _Part(this.name, this.filename, this.data);
  bool get isImage => filename != null && filename!.isNotEmpty;
}

List<_Part> _parseMultipart(Uint8List bytes, String boundary) {
  final parts = <_Part>[];
  final delim = utf8.encode('--$boundary');
  final chunks = _splitBy(bytes, delim);
  for (final chunk in chunks) {
    // Skip preamble/epilogue and empty segments.
    final headerEnd = _indexOf(chunk, utf8.encode('\r\n\r\n'));
    if (headerEnd < 0) continue;
    final headerStr = utf8.decode(
      chunk.sublist(0, headerEnd),
      allowMalformed: true,
    );
    if (!headerStr.contains('Content-Disposition')) continue;
    final nameMatch = RegExp('name="([^"]*)"').firstMatch(headerStr);
    final fileMatch = RegExp('filename="([^"]*)"').firstMatch(headerStr);
    final name = nameMatch?.group(1) ?? '';
    final filename = fileMatch?.group(1);
    // Body starts after \r\n\r\n and ends before the trailing \r\n.
    var body = chunk.sublist(headerEnd + 4);
    if (body.length >= 2 &&
        body[body.length - 2] == 0x0d &&
        body[body.length - 1] == 0x0a) {
      body = body.sublist(0, body.length - 2);
    }
    parts.add(_Part(name, filename, body));
  }
  return parts;
}

List<Uint8List> _splitBy(Uint8List data, List<int> sep) {
  final out = <Uint8List>[];
  var start = 0;
  var i = 0;
  while (i <= data.length - sep.length) {
    var match = true;
    for (var j = 0; j < sep.length; j++) {
      if (data[i + j] != sep[j]) {
        match = false;
        break;
      }
    }
    if (match) {
      out.add(Uint8List.sublistView(data, start, i));
      i += sep.length;
      start = i;
    } else {
      i++;
    }
  }
  out.add(Uint8List.sublistView(data, start));
  return out;
}

int _indexOf(Uint8List data, List<int> needle) {
  for (var i = 0; i <= data.length - needle.length; i++) {
    var match = true;
    for (var j = 0; j < needle.length; j++) {
      if (data[i + j] != needle[j]) {
        match = false;
        break;
      }
    }
    if (match) return i;
  }
  return -1;
}

Future<String> _readText(HttpRequest req) async {
  final bytes = await _readBytes(req);
  return utf8.decode(bytes, allowMalformed: true);
}

Future<Uint8List> _readBytes(HttpRequest req) async {
  final builder = BytesBuilder(copy: false);
  await for (final chunk in req) {
    builder.add(chunk);
  }
  return builder.toBytes();
}

String _prettyJson(String body) {
  try {
    return const JsonEncoder.withIndent('  ').convert(jsonDecode(body));
  } catch (_) {
    return body;
  }
}

void _logIndented(String text) {
  for (final line in text.split('\n')) {
    _log('      $line');
  }
}

void _replyJson(HttpRequest req, int status, Object body) {
  req.response
    ..statusCode = status
    ..headers.contentType = ContentType.json
    ..write(jsonEncode(body));
  req.response.close();
}
