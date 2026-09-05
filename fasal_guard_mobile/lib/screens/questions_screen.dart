import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

import '../config/app_theme.dart';
import '../config/crop_registry.dart';
import '../config/question_bank.dart';
import '../models/farmer_report.dart';
import '../models/question_answer.dart';
import '../services/audio_service.dart';
import '../services/asr_model_service.dart';
import '../services/device_service.dart';
import '../services/location_service.dart';
import '../services/recorder_service.dart';
import '../services/report_api_service.dart';
import '../services/report_session.dart';
import '../services/report_storage_service.dart';
import '../services/sherpa_stt_service.dart';
import '../services/upload_queue_service.dart';
import '../widgets/app_buttons.dart';
import '../widgets/app_top_bar.dart';

/// Step 4 of the main flow: the Punjabi/Urdu audio question engine.
///
/// Every question is asked by prerecorded audio; the farmer answers with
/// a short recording. Each recording is transcribed LOCALLY by Sherpa ONNX
/// (Omnilingual ASR 300M INT8, no internet needed); the returned text is
/// stored in the report and the temporary audio file is deleted. On a
/// transcription failure the temp audio is kept so the farmer can retry.
class QuestionsScreen extends StatefulWidget {
  const QuestionsScreen({super.key});

  @override
  State<QuestionsScreen> createState() => _QuestionsScreenState();
}

class _QuestionsScreenState extends State<QuestionsScreen> {
  final AudioService _promptPlayer = AudioService();
  final AudioService _answerPlayer = AudioService();
  final RecorderService _recorder = RecorderService();

  final List<FarmerAudioQuestion> _questions = QuestionBank.questions;
  int _index = 0;

  bool _recording = false;
  int _recordSeconds = 0;
  Timer? _recordTimer;
  bool _saving = false;
  bool _transcribing = false;

  /// One-time offline ASR model state (kept out of the APK).
  _ModelState _modelState = _ModelState.checking;
  double _modelProgress = 0;

  FarmerAudioQuestion get _question => _questions[_index];

  /// Temp path of the current answer. Deleted after a SUCCESSFUL
  /// transcription; kept on failure so the farmer can retry.
  String? _recordedPath;
  int get _recordedMs => _recordSeconds * 1000;

  @override
  void initState() {
    super.initState();
    // Rebuild on play/stop flips so the Listen/Prompt buttons show the
    // correct state while audio is playing.
    _promptPlayer.onStateChanged = _answerPlayer.onStateChanged = () {
      if (mounted) setState(() {});
    };
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _playPrompt();
      _ensureModel();
    });
  }

  @override
  void dispose() {
    _recordTimer?.cancel();
    _promptPlayer.dispose();
    _answerPlayer.dispose();
    _recorder.dispose();
    super.dispose();
  }

  // -------------------------------------------------------------
  // Prompt playback
  // -------------------------------------------------------------

  void _playPrompt() {
    _answerPlayer.stop();
    _promptPlayer.playAsset(_question.audioAsset);
  }

  // -------------------------------------------------------------
  // One-time offline ASR model download (kept out of the APK)
  // -------------------------------------------------------------

  Future<void> _ensureModel() async {
    setState(() {
      _modelState = _ModelState.checking;
      _modelProgress = 0;
    });
    try {
      await AsrModelService.instance.ensureModel(
        onProgress: (recv, total, _) {
          if (!mounted) return;
          setState(() {
            _modelState = _ModelState.downloading;
            _modelProgress = total > 0 ? recv / total : 0;
          });
        },
      );
      if (!mounted) return;
      setState(() => _modelState = _ModelState.ready);
      // Warm up the recognizer in the background so the first answer
      // transcribes without an extra wait.
      SherpaSttService.instance.ensureReady().catchError((Object e) {
        debugPrint('[stt] model preload failed: $e');
      });
    } catch (e) {
      debugPrint('[asr] model download failed: $e');
      if (!mounted) return;
      setState(() => _modelState = _ModelState.failed);
    }
  }

  // -------------------------------------------------------------
  // Recording the farmer answer
  // -------------------------------------------------------------

  Future<void> _startRecording() async {
    if (_recording) return;
    final allowed = await _recorder.hasPermission();
    if (!allowed) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..clearSnackBars()
        ..showSnackBar(
          const SnackBar(
            content: Text(
              'مائیکروفون دی اجازت نہیں ملی۔ جواب ریکارڈ کرن لئی اجازت دیو تے دوبارہ کوشش کرو۔',
              textAlign: TextAlign.center,
            ),
            backgroundColor: AppTheme.darkGreen,
          ),
        );
      return;
    }

    try {
      final temp = await getTemporaryDirectory();
      final path =
          '${temp.path}/answer_${_question.id}_${DateTime.now().millisecondsSinceEpoch}.wav';
      await _promptPlayer.stop();
      await _answerPlayer.stop();
      await _recorder.start(path);
      debugPrint('[qa] recorder started for ${_question.id}');
      _recordSeconds = 0;
      _recordTimer?.cancel();
      _recordTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!mounted || !_recording) return;
        setState(() => _recordSeconds++);
        if (_recordSeconds >= _question.maxAnswerSeconds) {
          _stopRecording();
        }
      });
      if (!mounted) return;
      setState(() => _recording = true);
    } catch (e) {
      debugPrint('[qa] recording failed: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..clearSnackBars()
        ..showSnackBar(
          const SnackBar(
            content: Text(
              'ریکارڈنگ شروع نہیں ہو سکی۔ دوبارہ کوشش کرو۔',
              textAlign: TextAlign.center,
            ),
            backgroundColor: AppTheme.darkGreen,
          ),
        );
    }
  }

  Future<void> _stopRecording() async {
    if (!_recording) return;
    _recordTimer?.cancel();
    try {
      final path = await _recorder.stop();
      debugPrint('[qa] stop: seconds=$_recordSeconds path=$path');
      if (!mounted) return;
      // An empty tap (under 1 second) is not a usable required answer.
      if (path == null || _recordSeconds < 1) {
        setState(() => _recording = false);
        ScaffoldMessenger.of(context)
          ..clearSnackBars()
          ..showSnackBar(
            const SnackBar(
              content: Text(
                'پہلاں تھوڑا جیہا بول کے ریکارڈ کرو۔',
                textAlign: TextAlign.center,
              ),
              backgroundColor: AppTheme.darkGreen,
            ),
          );
        return;
      }
      setState(() {
        _recording = false;
        _recordedPath = path;
      });
    } catch (e) {
      debugPrint('[qa] stop recording failed: $e');
      if (!mounted) return;
      setState(() => _recording = false);
    }
  }

  Future<void> _listenAnswer() async {
    // Toggle: stop when already playing so replay works every time.
    if (_answerPlayer.isPlaying) {
      await _answerPlayer.stop();
      if (mounted) setState(() {});
      return;
    }
    final path = _recordedPath;
    if (path == null) return;
    await _promptPlayer.stop();
    if (mounted) setState(() {}); // show "stop" state
    await _answerPlayer.playFile(path);
    if (mounted) setState(() {}); // back to "play" when finished
  }

  Future<void> _reRecord() async {
    await _discardTempAudio();
    setState(() => _recordSeconds = 0);
    await _startRecording();
  }

  /// Deletes the temporary answer file. Called ONLY after a successful
  /// Sherpa transcription and whenever the farmer re-records. On a failed
  /// transcription the temp audio stays so the farmer can retry.
  Future<void> _discardTempAudio() async {
    _answerPlayer.stop();
    final old = _recordedPath;
    setState(() => _recordedPath = null);
    if (old != null) {
      try {
        final f = File(old);
        if (await f.exists()) await f.delete();
      } catch (_) {}
    }
  }

  // -------------------------------------------------------------
  // Offline Sherpa STT + navigation
  // -------------------------------------------------------------

  /// Converts the recorded answer to text locally with Sherpa ONNX, stores
  /// the text, then deletes the temp audio. On failure the temp audio is
  /// kept and the farmer can retry or re-record.
  Future<void> _next() async {
    final path = _recordedPath;
    if (path == null) {
      // Optional question skipped.
      ReportSession.current.answers.remove(_question.id);
      _advance();
      return;
    }

    if (_modelState != _ModelState.ready) {
      await _ensureModel();
      if (_modelState != _ModelState.ready) return;
    }

    setState(() => _transcribing = true);
    _promptPlayer.stop();
    _answerPlayer.stop();
    try {
      final text = await SherpaSttService.instance.transcribe(path);
      if (!mounted) return;
      ReportSession.current.answers[_question.id] = QuestionAnswer(
        questionId: _question.id,
        questionAudioAsset: _question.audioAsset,
        answerText: text,
        sttStatus: text.isEmpty ? 'empty' : 'transcribed',
        answerDurationMs: _recordedMs,
      );
      await _discardTempAudio();
      if (!mounted) return;
      setState(() => _transcribing = false);
      _advance();
    } catch (e) {
      // Temp audio intentionally KEPT here so the farmer can retry.
      debugPrint('[stt] failed for ${_question.id}: $e');
      if (!mounted) return;
      setState(() => _transcribing = false);
      ScaffoldMessenger.of(context)
        ..clearSnackBars()
        ..showSnackBar(
          const SnackBar(
            content: Text(
              'آواز نوں لکھت وچ بدلݨ نہیں ہو سکی۔ دوبارہ کوشش کرو یا جواب دوبارہ ریکارڈ کرو۔',
              textAlign: TextAlign.center,
            ),
            backgroundColor: AppTheme.danger,
          ),
        );
    }
  }

  void _advance() {
    _promptPlayer.stop();
    _answerPlayer.stop();

    if (_index + 1 < _questions.length) {
      setState(() {
        _index++;
        _recordSeconds = 0;
      });
      WidgetsBinding.instance.addPostFrameCallback((_) => _playPrompt());
    } else {
      _finishReport();
    }
  }

  void _skip() {
    // Only offered for optional questions.
    _recordedPath = null;
    _next();
  }

  Future<void> _finishReport() async {
    setState(() => _saving = true);
    try {
      final session = ReportSession.current;
      final location = await LocationService().capture();
      final cropId = session.cropId ?? 'unknown';

      final report = FarmerReport(
        reportId:
            'rpt_${DateTime.now().millisecondsSinceEpoch.toRadixString(36)}',
        cropId: cropId,
        cropName: CropRegistry.byId(cropId)?.nameEn ?? cropId,
        imageSource: session.imageSource,
        answers: session.answers.values.toList(),
        location: location,
        capturedAt: DateTime.now(),
      );

      // Local save always happens first; the OSS image upload is queued.
      final saved = await ReportStorageService.instance.save(
        report,
        imageBytes: session.imageBytes,
      );
      final queued = await UploadQueueService.instance.enqueueAndTry(saved);
      // Also submit to backend API (fire-and-forget alongside OSS upload).
      ReportApiService.instance.submit(
        saved,
        imageBytes: session.imageBytes,
        deviceId: DeviceService.instance.deviceId,
      );
      if (!mounted) return;
      // Replace the whole report flow with the completion screen.
      Navigator.of(context)
          .pushReplacementNamed(AppRoutes.complete, arguments: queued);
    } catch (e) {
      debugPrint('[report] save failed: $e');
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context)
        ..clearSnackBars()
        ..showSnackBar(
          const SnackBar(
            content: Text(
              'رپورٹ محفوظ نہیں ہو سکی۔ دوبارہ کوشش کرو۔',
              textAlign: TextAlign.center,
            ),
            backgroundColor: AppTheme.danger,
          ),
        );
    }
  }

  // -------------------------------------------------------------
  // UI
  // -------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.cream,
        appBar: AppTopBar(title: 'سوال ${_index + 1} / ${_questions.length}'),
        body: SafeArea(
          child: Column(
            children: [
              Expanded(
                child: _saving || _transcribing ? _busyBody() : _questionBody(),
              ),
              if (_modelState != _ModelState.ready) _modelBanner(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _busyBody() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(color: AppTheme.darkGreen),
          const SizedBox(height: 16),
          Text(
            _transcribing
                ? 'جواب لکھت وچ بدلیا جا رہیا اے...'
                : 'رپورٹ محفوظ ہو رہی اے...',
            style: const TextStyle(fontSize: 16, color: AppTheme.darkGreen),
          ),
        ],
      ),
    );
  }

  Widget _modelBanner() {
    final percent = (_modelProgress * 100).toInt();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(22, 12, 22, 16),
      color: const Color(0xFFF3EFE2),
      child: switch (_modelState) {
        _ModelState.failed => Row(
          children: [
            const Expanded(
              child: Text(
                'آواز ماڈل تیار نہیں ہو سکی۔',
                style: TextStyle(fontSize: 13, color: AppTheme.danger),
              ),
            ),
            TextButton(
              onPressed: _ensureModel,
              child: const Text(
                'دوبارہ کوشش',
                style: TextStyle(
                  color: AppTheme.darkGreen,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        _ => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _modelState == _ModelState.downloading
                  ? 'آواز ماڈل تیار ہو رہیا اے (صرف پہلی وار، $percent٪)'
                  : 'آواز ماڈل تیار کیتا جا رہیا اے...',
              style: const TextStyle(fontSize: 13, color: AppTheme.darkGreen),
            ),
            const SizedBox(height: 6),
            LinearProgressIndicator(
              value: _modelState == _ModelState.downloading
                  ? _modelProgress
                  : null,
              minHeight: 6,
              color: AppTheme.darkGreen,
              backgroundColor: const Color(0xFFE5E7DE),
              borderRadius: BorderRadius.circular(3),
            ),
          ],
        ),
      },
    );
  }

  Widget _questionBody() {
    final hasAnswer = _recordedPath != null;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(22, 14, 22, 25),
      child: Column(
        children: [
          LinearProgressIndicator(
            value: (_index) / _questions.length,
            minHeight: 6,
            backgroundColor: const Color(0xFFE5E7DE),
            valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.darkGreen),
            borderRadius: BorderRadius.circular(4),
          ),
          const SizedBox(height: 28),
          Text(
            _question.punjabiHint,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppTheme.darkGreen,
              fontSize: 23,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'سوال سُݨن لئی آواز بٹن دباؤ',
            style: TextStyle(color: Colors.grey.shade700, fontSize: 14),
          ),
          const SizedBox(height: 16),
          IconButton(
            onPressed: _playPrompt,
            iconSize: 54,
            icon: const Icon(
              Icons.volume_up_rounded,
              color: AppTheme.darkGreen,
            ),
            style: IconButton.styleFrom(
              backgroundColor: AppTheme.lightGreenFill,
              minimumSize: const Size(84, 84),
              shape: const CircleBorder(),
            ),
          ),
          const SizedBox(height: 30),
          // Recording indicator reused from the original voice-recording UI.
          AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            width: 145,
            height: 145,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _recording
                  ? const Color(0xFFE3EED0)
                  : AppTheme.lightGreenFill,
              boxShadow: _recording
                  ? const [
                      BoxShadow(
                        color: Color.fromRGBO(23, 126, 56, 0.18),
                        blurRadius: 35,
                        spreadRadius: 12,
                      ),
                    ]
                  : null,
            ),
            child: Icon(
              _recording ? Icons.mic_rounded : Icons.mic_none_rounded,
              color: AppTheme.darkGreen,
              size: 72,
            ),
          ),
          const SizedBox(height: 14),
          Text(
            _recording
                ? 'ریکارڈنگ... ${_formatDuration(_recordSeconds)}'
                : hasAnswer
                ? 'جواب ریکارڈ ہو گیا (${_formatDuration(_recordSeconds)})'
                : 'جواب دیݨ لئی مائیک دباؤ',
            style: const TextStyle(
              color: AppTheme.darkGreen,
              fontSize: 17,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 30),
          if (_recording)
            DangerButton(
              icon: Icons.stop_rounded,
              text: 'ریکارڈنگ روکو',
              onTap: _stopRecording,
            )
          else ...[
            PrimaryButton(
              icon: hasAnswer ? Icons.refresh_rounded : Icons.mic_rounded,
              text: hasAnswer ? 'دوبارہ ریکارڈ کرو' : 'جواب ریکارڈ کرو',
              onTap: hasAnswer ? _reRecord : _startRecording,
            ),
            const SizedBox(height: 12),
            SecondaryButton(
              icon: _answerPlayer.isPlaying
                  ? Icons.stop_circle_outlined
                  : Icons.play_circle_outline_rounded,
              text: _answerPlayer.isPlaying ? 'آواز روکو' : 'میرا جواب سُݨو',
              onTap: hasAnswer ? _listenAnswer : null,
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              icon: Icons.arrow_forward_rounded,
              text: _index + 1 < _questions.length
                  ? 'اگلا سوال'
                  : 'رپورٹ مکمل کرو',
              onTap: (hasAnswer || !_question.required) ? _next : null,
            ),
            if (!_question.required) ...[
              const SizedBox(height: 12),
              TextButton(
                onPressed: _skip,
                child: const Text(
                  'چھڈو',
                  style: TextStyle(
                    color: AppTheme.darkGreen,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }

  String _formatDuration(int seconds) {
    final minutes = seconds ~/ 60;
    final remaining = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:'
        '${remaining.toString().padLeft(2, '0')}';
  }
}

enum _ModelState { checking, downloading, ready, failed }
