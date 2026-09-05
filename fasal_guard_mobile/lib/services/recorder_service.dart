import 'package:record/record.dart';

/// Records the farmer's short Punjabi/Urdu audio answers.
/// 16 kHz mono PCM/WAV — the preferred input format of the offline
/// Sherpa ONNX recognizer.
class RecorderService {
  final AudioRecorder _recorder = AudioRecorder();

  Future<bool> hasPermission() {
    try {
      return _recorder.hasPermission();
    } catch (_) {
      return Future.value(false);
    }
  }

  Future<void> start(String path) => _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
        ),
        path: path,
      );

  /// Returns the recorded file path, or null when nothing was recorded.
  Future<String?> stop() => _recorder.stop();

  Future<void> cancel() async {
    try {
      await _recorder.cancel();
    } catch (_) {
      // Cancel is best-effort; a leftover temp file is harmless.
    }
  }

  Future<void> dispose() => _recorder.dispose();
}
