import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:fasal_guard_mobile/config/question_bank.dart';
import 'package:fasal_guard_mobile/models/farmer_report.dart';
import 'package:fasal_guard_mobile/models/question_answer.dart';

/// Frontend tests for the 4-question Punjabi/Urdu audio flow:
/// Image -> Q1 -> Q2 -> Q3 -> Q4 -> GPS -> Save Local Report.
void main() {
  group('QuestionBank (4 questions)', () {
    test('contains exactly 4 questions', () {
      expect(QuestionBank.questions.length, 4);
    });

    test('asks questions in the required order Q1..Q4', () {
      final ids = QuestionBank.questions.map((q) => q.id).toList();
      expect(ids, [
        'symptom_description', // Q1 what problem/changes are visible
        'symptom_duration', // Q2 when it was first noticed
        'affected_spread', // Q3 how much field/plants affected
        'spreading_status', // Q4 is it spreading or getting worse
      ]);
    });

    test('every question is required (all 4 answers are recorded)', () {
      for (final q in QuestionBank.questions) {
        expect(q.required, isTrue, reason: '${q.id} must be required');
        expect(q.maxAnswerSeconds, greaterThan(0));
      }
    });

    test('every question has a unique prerecorded prompt audio', () {
      final assets = QuestionBank.questions.map((q) => q.audioAsset).toList();
      expect(assets.toSet().length, 4);
    });

    // `flutter test` runs with the project root as working directory, so
    // the bundled prompt audios can be checked on disk.
    test('every prompt audio asset exists in assets/audio/', () {
      for (final q in QuestionBank.questions) {
        expect(File(q.audioAsset).existsSync(), isTrue,
            reason: 'missing prompt audio ${q.audioAsset} for ${q.id}');
      }
    });
  });

  group('QuestionAnswer / FarmerReport persistence', () {
    test('raw Punjabi/Urdu transcription survives JSON round-trip', () {
      const qa = QuestionAnswer(
        questionId: 'symptom_description',
        questionAudioAsset: 'assets/audio/05_symptom_description.mp3',
        answerText: 'پتیاں تے دھبے نظر آ رہے نیں',
        sttStatus: 'transcribed',
        answerDurationMs: 7000,
      );
      final decoded =
          QuestionAnswer.fromJson(jsonDecode(jsonEncode(qa.toJson())));
      expect(decoded.questionId, qa.questionId);
      expect(decoded.answerText, qa.answerText);
      expect(decoded.sttStatus, 'transcribed');
    });

    test('local report preserves all 4 question answers', () {
      final answers = QuestionBank.questions
          .map((q) => QuestionAnswer(
                questionId: q.id,
                questionAudioAsset: q.audioAsset,
                answerText: 'جواب ${q.id}',
                sttStatus: 'transcribed',
                answerDurationMs: 5000,
              ))
          .toList();
      final report = FarmerReport(
        reportId: 'rpt_test',
        cropId: 'cotton',
        cropName: 'Cotton',
        imageSource: ReportImageSource.camera,
        answers: answers,
        location: const ReportLocation(
            latitude: 30.2, longitude: 73.0, status: 'captured'),
        capturedAt: DateTime(2026, 8, 28),
      );

      final decoded =
          FarmerReport.fromJson(jsonDecode(jsonEncode(report.toJson())));
      expect(decoded.answers.length, 4);
      expect(decoded.answers.map((a) => a.questionId).toList(),
          ['symptom_description', 'symptom_duration',
              'affected_spread', 'spreading_status']);
      expect(decoded.answers.every((a) => a.answerText.isNotEmpty), isTrue);
    });
  });
}
