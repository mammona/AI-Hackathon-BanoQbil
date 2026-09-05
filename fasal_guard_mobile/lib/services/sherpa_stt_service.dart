import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

import 'asr_model_service.dart';

/// Fully offline speech-to-text (no remote STT API, no model training).
///
/// Runs the pretrained Omnilingual ASR 300M INT8 CTC model through
/// Sherpa ONNX, locally on the phone. Input: 16 kHz mono PCM/WAV answer
/// recordings. Output: transcribed text stored in the report.
class SherpaSttService {
  static final SherpaSttService instance = SherpaSttService._();
  SherpaSttService._();

  sherpa.OfflineRecognizer? _recognizer;
  Future<void>? _init;

  /// Loads the model once (a few seconds the first time). Requires the
  /// model files to already exist locally (see AsrModelService).
  Future<void> ensureReady() {
    if (_recognizer != null) return Future.value();
    return _init ??= _load().whenComplete(() => _init = null);
  }

  Future<void> _load() async {
    final dir = await AsrModelService.instance.modelDirPath();
    await sherpa.initBindingsAsync();
    final sw = Stopwatch()..start();
    final model = sherpa.OfflineModelConfig(
      omnilingual: sherpa.OfflineOmnilingualAsrCtcModelConfig(
        model: '$dir/model.int8.onnx',
      ),
      tokens: '$dir/tokens.txt',
      numThreads: 2,
      debug: false,
    );
    _recognizer =
        sherpa.OfflineRecognizer(sherpa.OfflineRecognizerConfig(model: model));
    debugPrint('[stt] sherpa model loaded in ${sw.elapsedMilliseconds} ms');
  }

  /// Transcribes one recorded WAV file locally. Throws on any failure so
  /// the caller can keep the temp audio and offer a retry.
  Future<String> transcribe(String wavPath) async {
    await ensureReady();
    final recognizer = _recognizer!;

    final sw = Stopwatch()..start();
    final wave = _readWav(File(wavPath));
    final stream = recognizer.createStream();
    try {
      stream.acceptWaveform(samples: wave.samples, sampleRate: wave.sampleRate);
      recognizer.decode(stream);
      final text = recognizer.getResult(stream).text.trim();
      debugPrint('[stt] transcribed ${wave.samples.length} samples '
          'in ${sw.elapsedMilliseconds} ms -> "$text"');
      return text;
    } finally {
      stream.free();
    }
  }

  // -------------------------------------------------------------
  // Minimal 16-bit PCM WAV reader (record package output format).
  // -------------------------------------------------------------

  _Wave _readWav(File file) {
    final bytes = file.readAsBytesSync();
    if (bytes.length < 44 || _tag(bytes, 0, 4) != 'RIFF') {
      throw const FormatException('not a WAV file');
    }
    final bd = ByteData.sublistView(bytes);
    var i = 12; // skip RIFF header + WAVE
    var sampleRate = 16000;
    var channels = 1;
    var bits = 16;
    int? dataStart;
    int? dataSize;
    while (i + 8 <= bytes.length) {
      final id = _tag(bytes, i, i + 4);
      final size = bd.getUint32(i + 4, Endian.little);
      final body = i + 8;
      if (body + size > bytes.length) break;
      if (id == 'fmt ') {
        channels = bd.getUint16(body + 2, Endian.little);
        sampleRate = bd.getUint32(body + 4, Endian.little);
        bits = bd.getUint16(body + 14, Endian.little);
      } else if (id == 'data') {
        dataStart = body;
        dataSize = size;
        break;
      }
      i = body + size + (size.isOdd ? 1 : 0);
    }
    if (dataStart == null || dataSize == null) {
      throw const FormatException('WAV data chunk missing');
    }
    if (bits != 16) {
      throw FormatException('expected 16-bit PCM WAV, got $bits-bit');
    }

    final data = ByteData.sublistView(bytes, dataStart, dataStart + dataSize);
    final frames = dataSize ~/ 2;
    final samples = Float32List(channels == 1 ? frames : frames ~/ channels);
    if (channels == 1) {
      for (var k = 0; k < frames; k++) {
        samples[k] = data.getInt16(k * 2, Endian.little) / 32768.0;
      }
    } else {
      // Recordings are always mono; defensively mix extra channels down.
      for (var f = 0; f < frames ~/ channels; f++) {
        var sum = 0.0;
        for (var c = 0; c < channels; c++) {
          sum += data.getInt16((f * channels + c) * 2, Endian.little) /
              32768.0;
        }
        samples[f] = sum / channels;
      }
    }
    return _Wave(samples: samples, sampleRate: sampleRate);
  }

  String _tag(Uint8List bytes, int start, int end) =>
      String.fromCharCodes(bytes.sublist(start, end));
}

class _Wave {
  final Float32List samples;
  final int sampleRate;
  const _Wave({required this.samples, required this.sampleRate});
}
