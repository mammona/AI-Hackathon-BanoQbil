import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

import 'script_normalizer.dart';

/// Cloud speech-to-text: OpenAI Whisper large-v3 hosted on Groq (free tier).
///
/// Replaces the removed on-device Omnilingual ASR model: much higher
/// Punjabi accuracy at zero APK weight, at the cost of needing internet
/// while transcribing. The Groq API key is read from `.env`
/// (see flutter_dotenv); on failure the caller keeps the temp audio so
/// the farmer can retry.
///
/// Whisper returns Punjabi in Gurmukhi, so every transcript passes through
/// [ScriptNormalizer] to keep the app fully Shahmukhi.
class WhisperSttService {
  static final WhisperSttService instance = WhisperSttService._();
  WhisperSttService._();

  static const _endpoint =
      'https://api.groq.com/openai/v1/audio/transcriptions';

  /// Transcribes one recorded WAV file. Throws on any failure (missing
  /// key, network, HTTP) so the caller can keep the temp audio and retry.
  Future<String> transcribe(String wavPath) async {
    final key = dotenv.env['GROQ_API_KEY'] ?? '';
    if (key.isEmpty) {
      throw StateError('GROQ_API_KEY missing from .env');
    }

    final sw = Stopwatch()..start();
    final request = http.MultipartRequest('POST', Uri.parse(_endpoint))
      ..headers['Authorization'] = 'Bearer $key'
      ..fields['model'] = 'whisper-large-v3'
      // Farmers speak Punjabi; pinning the language stops Whisper from
      // drifting into Hindi on short field recordings.
      ..fields['language'] = 'pa'
      ..files.add(await http.MultipartFile.fromPath('file', wavPath));

    final streamed =
        await request.send().timeout(const Duration(seconds: 60));
    final body = await streamed.stream.bytesToString();
    if (streamed.statusCode != 200) {
      throw HttpException('whisper HTTP ${streamed.statusCode}: $body');
    }

    final text = ScriptNormalizer.toShahmukhi(
        (jsonDecode(body)['text'] as String? ?? '').trim());
    debugPrint('[stt] whisper transcribed in ${sw.elapsedMilliseconds} ms '
        '-> "$text"');
    return text;
  }
}
