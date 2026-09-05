/// Remote endpoint configuration for the prototype.
///
/// SECURITY: the Alibaba AccessKey / AccessKey Secret must NEVER be stored
/// in the Flutter app. OSS uploads go through a Function Compute endpoint
/// that issues short-lived presigned URLs.
///
/// Speech-to-text runs in the cloud (Groq-hosted Whisper large-v3); the
/// API key is read from the local `.env` file, never from this class.
class RemoteConfig {
  RemoteConfig._();

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
