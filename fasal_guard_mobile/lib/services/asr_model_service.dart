import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter/services.dart' show MethodChannel, rootBundle;
import 'package:path_provider/path_provider.dart';

import '../config/remote_config.dart';

/// One-time storage management for the offline ASR model.
///
/// The Omnilingual ASR 300M INT8 model ships INSIDE the APK
/// (`assets/asr_model/`). On first use the bundled files are copied into
/// app storage (`<docs>/asr_model/`), which takes a few seconds and needs
/// NO internet. The HuggingFace download is kept only as a fallback for
/// builds where the bundled assets are missing. Truncated files are
/// detected via minimum sizes and re-created automatically.
class AsrModelService {
  static final AsrModelService instance = AsrModelService._();
  AsrModelService._();

  /// Native streaming unpacker (MainActivity) — keeps the UI responsive
  /// while the 365 MB model is copied out of the APK.
  static const MethodChannel _unpackChannel =
      MethodChannel('fasal_guard/asr_model');

  Future<void>? _pending;

  /// Absolute path of the folder holding the model files.
  Future<String> modelDirPath() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory('${docs.path}/${RemoteConfig.asrModelDir}');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir.path;
  }

  /// True when every model file exists locally with a plausible size.
  Future<bool> isReady() async {
    final dir = await modelDirPath();
    for (final entry in RemoteConfig.asrModelFiles.entries) {
      final file = File('$dir/${entry.key}');
      if (!await file.exists()) return false;
      if (await file.length() < entry.value) return false;
    }
    return true;
  }

  /// Makes sure the model is present locally. Copies the files bundled in
  /// the APK first; only if an asset is missing does it fall back to the
  /// HuggingFace download. [onProgress] reports per-file byte counts.
  /// Concurrent callers share the same in-flight work. Throws on any
  /// failure so callers can offer a retry.
  Future<void> ensureModel({
    void Function(int receivedBytes, int totalBytes, String fileName)?
        onProgress,
  }) {
    final pending = _pending;
    if (pending != null) return pending;
    return _pending = _doEnsure(onProgress).whenComplete(() {
      _pending = null;
    });
  }

  Future<void> _doEnsure(
    void Function(int receivedBytes, int totalBytes, String fileName)?
        onProgress,
  ) async {
    if (await isReady()) return;
    final dir = await modelDirPath();
    for (final entry in RemoteConfig.asrModelFiles.entries) {
      final target = File('$dir/${entry.key}');
      if (await _copyBundledAsset(entry.key, target, entry.value,
          onProgress)) {
        continue;
      }
      await _downloadFile(
        '${RemoteConfig.asrModelBase}${entry.key}',
        target,
        entry.value,
        onProgress,
      );
    }
    debugPrint('[asr] model ready at $dir');
  }

  /// Copies one model file out of the APK assets into app storage.
  /// Prefers the native background-thread streamer; falls back to a Dart
  /// rootBundle copy when the channel is unavailable (non-Android hosts).
  /// Returns false when the asset is not bundled in this build, so the
  /// caller can fall back to the network download.
  Future<bool> _copyBundledAsset(
    String name,
    File target,
    int minBytes,
    void Function(int, int, String)? onProgress,
  ) async {
    if (await target.exists() && await target.length() >= minBytes) {
      return true; // already unpacked
    }
    final sw = Stopwatch()..start();
    if (await _unpackNative(name, target, minBytes)) {
      onProgress?.call(minBytes, minBytes, name);
      debugPrint('[asr] unpacked bundled $name natively '
          'in ${sw.elapsedMilliseconds} ms');
      return true;
    }
    try {
      final bd = await rootBundle.load('assets/asr_model/$name');
      final bytes = bd.buffer.asUint8List(bd.offsetInBytes, bd.lengthInBytes);
      final tmp = File('${target.path}.part');
      if (await tmp.exists()) await tmp.delete();
      await tmp.writeAsBytes(bytes, flush: true);
      if (bytes.length < minBytes) {
        await tmp.delete();
        throw const FileSystemException('bundled ASR asset truncated');
      }
      await tmp.rename(target.path);
      // Free the cached asset copy so the 365 MB do not stay pinned.
      rootBundle.evict('assets/asr_model/$name');
      onProgress?.call(bytes.length, bytes.length, name);
      debugPrint('[asr] unpacked bundled $name (${bytes.length} bytes) '
          'in ${sw.elapsedMilliseconds} ms');
      return true;
    } catch (e) {
      debugPrint('[asr] bundled asset $name unavailable ($e); '
          'falling back to download');
      return false;
    }
  }

  /// Asks MainActivity to stream `flutter_assets/assets/asr_model/<name>`
  /// into [target] on a background thread. Returns false when the channel
  /// or the bundled asset is unavailable.
  Future<bool> _unpackNative(String name, File target, int minBytes) async {
    try {
      final written = await _unpackChannel.invokeMethod<int>('unpackAsset', {
        'asset': 'flutter_assets/assets/asr_model/$name',
        'target': target.path,
      });
      return (written ?? 0) >= minBytes;
    } catch (e) {
      debugPrint('[asr] native unpack unavailable for $name: $e');
      return false;
    }
  }

  Future<void> _downloadFile(
    String url,
    File target,
    int minBytes,
    void Function(int, int, String)? onProgress,
  ) async {
    if (await target.exists()) {
      if (await target.length() >= minBytes) return; // already complete
      await target.delete(); // truncated previous attempt
    }

    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 20);
    try {
      final uri = Uri.parse(url);
      final req = await client.getUrl(uri);
      final res = await req.close().timeout(const Duration(minutes: 30));
      if (res.statusCode != 200) {
        throw HttpException('ASR model HTTP ${res.statusCode}', uri: uri);
      }

      final total = res.contentLength > 0 ? res.contentLength : 0;
      final tmp = File('${target.path}.part');
      if (await tmp.exists()) await tmp.delete();
      final sink = tmp.openWrite();
      var received = 0;
      try {
        await for (final chunk in res) {
          received += chunk.length;
          sink.add(chunk);
          onProgress?.call(received, total, target.uri.pathSegments.last);
        }
        await sink.flush();
      } finally {
        await sink.close();
      }

      if (received < minBytes) {
        throw HttpException(
            'ASR model download truncated ($received < $minBytes bytes)',
            uri: uri);
      }
      await tmp.rename(target.path);
      debugPrint('[asr] downloaded ${target.path} ($received bytes)');
    } finally {
      client.close(force: true);
    }
  }
}
