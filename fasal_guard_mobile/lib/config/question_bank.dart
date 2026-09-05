import '../models/question_answer.dart';

/// Plan section 23: the question engine is configuration-driven. No
/// Punjabi question logic lives inside screen widgets.
///
/// Question 01 (crop selection) is handled visually and is NOT part of the
/// audio Q&A; it is played on the crop-selection screen itself.
///
/// The audio Q&A asks 4 questions, one per screen:
/// Q1 what problem/changes are visible -> Q2 when it was first noticed ->
/// Q3 how much of the field/plants is affected -> Q4 is it spreading or
/// getting worse. All 4 answers are required and their raw Punjabi/Urdu
/// transcriptions are stored in the local report.
///
/// `05_symptom_description.mp3` and `06_spreading_status.mp3` are synthetic
/// TTS placeholders (same style as the other dev prompts); replace them
/// with native-speaker recordings under the same filenames if available.
class QuestionBank {
  QuestionBank._();

  static const List<FarmerAudioQuestion> questions = [
    FarmerAudioQuestion(
      id: 'symptom_description',
      audioAsset: 'assets/audio/05_symptom_description.mp3',
      punjabiHint: 'فصل وچ کیا مسئلہ نظر آ رہیا اے؟',
      required: true,
      maxAnswerSeconds: 20,
    ),
    FarmerAudioQuestion(
      id: 'symptom_duration',
      audioAsset: 'assets/audio/03_symptom_duration.m4a',
      punjabiHint: 'مسئلہ کدوں توں اے؟',
      required: true,
      maxAnswerSeconds: 20,
    ),
    FarmerAudioQuestion(
      id: 'affected_spread',
      audioAsset: 'assets/audio/02_affected_spread.m4a',
      punjabiHint: 'کتنا رقبہ متاثر اے؟',
      required: true,
      maxAnswerSeconds: 20,
    ),
    FarmerAudioQuestion(
      id: 'spreading_status',
      audioAsset: 'assets/audio/06_spreading_status.mp3',
      punjabiHint: 'کیہ مسئلہ پھیل رہیا اے؟',
      required: true,
      maxAnswerSeconds: 20,
    ),
  ];
}
