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

  /// Transcribes one recorded WAV file.
  Future<String> transcribe(String wavPath, {String? questionId}) async {
    final key = dotenv.env['GROQ_API_KEY'] ?? '';
    if (key.isEmpty) {
      throw StateError('GROQ_API_KEY missing from .env');
    }

    // Question-specific prompts help Whisper understand the context (numbers, symptoms, time).
    // The prompt is updated to use "Theth" (authentic rural) Punjabi vocabulary.
    final prompts = {
      'symptom_description': 'ایہ کسان دی فصل دے روگ دے بارے اے۔ کیہ تکلیف نظر آئی؟ پتے پیلے نیں، کیڑا لگا اے یا کیہ روگ اے؟',
      'symptom_duration': 'ایہ وقت دے بارے اے۔ ایہ روگ کدوں توں لگا اے؟ چار دن، اک ہفتہ یا کنا چِرا؟',
      'affected_spread': 'ایہ رقبے دے بارے اے۔ کِنا پیلی خراب ہویا اے؟ کِنے بوٹے مِڑے نیں؟',
      'spreading_status': 'ایہ روگ دے ودھن دے بارے اے۔ کیہ ایہ ہور ودھ رہیا اے؟ ہاں یا نئیں؟',
    };

    final basePrompt = 'ایہ ٹھیٹھ دیسی پنجابی شاہ مکھی وچ اے۔ لہجہ پنڈاں والا اے۔ ';
    final specificPrompt = prompts[questionId] ?? 'پنجابی شاہ مکھی وچ جواب دیو۔';

    final sw = Stopwatch()..start();
    final request = http.MultipartRequest('POST', Uri.parse(_endpoint))
      ..headers['Authorization'] = 'Bearer $key'
      ..fields['model'] = 'whisper-large-v3'
      ..fields['language'] = 'pa'
      ..fields['prompt'] = '$basePrompt$specificPrompt'
      ..files.add(await http.MultipartFile.fromPath('file', wavPath));

    final streamed =
        await request.send().timeout(const Duration(seconds: 60));
    final body = await streamed.stream.bytesToString();
    if (streamed.statusCode != 200) {
      throw HttpException('whisper HTTP ${streamed.statusCode}: $body');
    }

    final rawText = (jsonDecode(body)['text'] as String? ?? '').trim();
    
    // Arabic script range starts at 0x0600.
    final hasArabicScript = rawText.runes.any((r) => r >= 0x0600 && r <= 0x06FF);

    String text = hasArabicScript ? rawText : ScriptNormalizer.toShahmukhi(rawText);

    // Advanced Punjabi Dialect & Orthography Refinement.
    final corrections = {
      ' ہے': ' اے', 
      ' ہیں': ' نیں', 
      ' وہ': ' او',   
      ' کیا': ' کیہ', 
      'نہیں': ' نئیں',
      'کیوں': ' کیوں',
      'کتنا': ' کِنا',
      'پودا': ' بوٹا',
      'پودے': ' بوٹے',
      'کب سے': ' کدوں توں',
      'سے': ' توں',
      'بتاؤ': ' دسو',  
      'دیکھیں': ' دیکھو',
      'دکھائیں': ' وکھاؤ',
      'کب': ' کدوں',
      'کدھر': ' کتھے',
      'کہاں': ' کتھے',
      'ادھر': ' ایتھے',
      'گئی': ' گئی',
      'ہوگا': ' ہووے گا',
      'ہوئی': ' ہوئی',
      'تھا': ' سی',
      'تھے': ' سن',
      'یاد': ' چیتے',
      'پھیل': ' ودھ',
      'متاثر': ' خراب',
    };
    
    corrections.forEach((urdu, punjabi) {
      text = text.replaceAll(urdu, punjabi);
    });

    debugPrint('[stt] whisper transcribed ($questionId) in ${sw.elapsedMilliseconds} ms '
        '-> "$text"');
    return text;
  }
}
