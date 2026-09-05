/// One prerecorded Punjabi audio question and the farmer's answer.
class FarmerAudioQuestion {
  final String id;
  final String audioAsset;

  /// Required questions cannot be skipped; the farmer must record an answer.
  final bool required;

  /// Recording stops automatically after this many seconds.
  final int maxAnswerSeconds;

  /// Short Shahmukhi hint shown under the mic (the question itself is
  /// asked by audio; the farmer never has to read it).
  final String punjabiHint;

  const FarmerAudioQuestion({
    required this.id,
    required this.audioAsset,
    required this.punjabiHint,
    this.required = true,
    this.maxAnswerSeconds = 20,
  });
}

/// A farmer's answer attached to its question id. The recorded audio is
/// transcribed locally by Sherpa ONNX and then discarded; only the text
/// is stored.
class QuestionAnswer {
  final String questionId;
  final String questionAudioAsset;

  /// Offline Sherpa ONNX transcript of the farmer's answer.
  final String answerText;

  /// 'transcribed' | 'empty' (skipped optional question)
  final String sttStatus;

  final int answerDurationMs;

  const QuestionAnswer({
    required this.questionId,
    required this.questionAudioAsset,
    required this.answerText,
    required this.sttStatus,
    required this.answerDurationMs,
  });

  Map<String, dynamic> toJson() => {
        'question_id': questionId,
        'question_audio_asset': questionAudioAsset,
        'answer_text': answerText,
        'stt_status': sttStatus,
        'answer_duration_ms': answerDurationMs,
      };

  factory QuestionAnswer.fromJson(Map<String, dynamic> json) => QuestionAnswer(
        questionId: json['question_id'] as String,
        questionAudioAsset: json['question_audio_asset'] as String,
        answerText: json['answer_text'] as String? ?? '',
        sttStatus: json['stt_status'] as String? ??
            ((json['answer_text'] as String? ?? '').isEmpty
                ? 'empty'
                : 'transcribed'),
        answerDurationMs: json['answer_duration_ms'] as int? ?? 0,
      );
}
