/// Remote endpoint configuration for the prototype.
///
/// SECURITY: the Alibaba AccessKey / AccessKey Secret must NEVER be stored
/// in the Flutter app. OSS uploads go through a Function Compute endpoint
/// that issues short-lived presigned URLs.
///
/// Speech-to-text is fully OFFLINE (Sherpa ONNX, Omnilingual ASR 300M INT8)
/// — there is NO remote STT endpoint anywhere in this app.
class RemoteConfig {
  RemoteConfig._();

  /// Omnilingual ASR 300M INT8 (sherpa-onnx) model source. The model is
  /// downloaded ONCE into app storage and reused fully offline — it is
  /// deliberately NOT bundled in the APK (~365 MB).
  static const String asrModelBase =
      'https://huggingface.co/csukuangfj2/'
      'sherpa-onnx-omnilingual-asr-1600-languages-300M-ctc-int8-2025-11-12/'
      'resolve/main/';

  /// Files that make up the local ASR model, with minimum valid sizes
  /// (used to detect truncated downloads and re-fetch them).
  static const Map<String, int> asrModelFiles = {
    'model.int8.onnx': 340 * 1024 * 1024, // actual ≈365,352,120 B (348.5 MiB)
    'tokens.txt': 80 * 1024, // actual 86,423 B
  };

  /// Folder (inside app documents) where the ASR model lives.
  static const String asrModelDir = 'asr_model';

  /// Function Compute endpoint that returns a presigned OSS upload URL.
  /// Request: POST {"filename": "...", "content_type": "..."}
  /// Response: {"upload_url": "...", "object_key": "..."}
  /// M8 test value: local mock backend. Replace with the real FC URL.
  static const String fcPresignUrl = 'http://10.0.2.2:8787/oss/presign';

  /// Endpoint that receives the report metadata when internet returns:
  /// transcribed text answers + crop + GPS + timestamp (+ OSS image key).
  /// Audio is NEVER part of the sync payload.
  /// M8/M10 test value: local mock backend. Replace with the real URL.
  static const String reportSyncUrl = 'http://10.0.2.2:8787/report';

  /// Upload attempts before a report is left in the retry queue.
  static const int maxUploadRetries = 3;
}
