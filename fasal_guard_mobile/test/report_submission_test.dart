import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import 'package:fasal_guard_mobile/config/question_bank.dart';
import 'package:fasal_guard_mobile/models/farmer_report.dart';
import 'package:fasal_guard_mobile/models/question_answer.dart';
import 'package:fasal_guard_mobile/services/report_api_service.dart';

/// Tests for the symptom-only (no image) report path of
/// [ReportApiService.submit].
///
/// `submit()` is fire-and-forget: it validates the report and then performs
/// the HTTP multipart POST internally. These tests therefore verify the
/// validation guard clause and the payload data mapping — they never
/// exercise a live network call.
void main() {
  group('ReportApiService.submit guard clause (validation)', () {
    test(
      'returns without throwing when the report has no answers and no image',
      () async {
        final emptyReport = FarmerReport(
          reportId: 'rpt_no_content',
          cropId: 'cotton',
          cropName: 'Cotton',
          imageSource: ReportImageSource.camera,
          answers: const [],
          location: null,
          capturedAt: DateTime(2026, 9, 4, 9, 0),
        );

        // The guard clause (`!hasAnswer && imageBytes == null`) must
        // short-circuit BEFORE any HttpClient work. The 5s timeout proves
        // submit() returned without attempting a connection to the backend
        // (a real attempt would block for the 10s connection timeout).
        await expectLater(
          ReportApiService.instance
              .submit(emptyReport, imageBytes: null, deviceId: 'test-device')
              .timeout(const Duration(seconds: 5)),
          completes,
        );
      },
    );

    test('whitespace-only answers do not count as content', () async {
      final blankReport = FarmerReport(
        reportId: 'rpt_blank_answers',
        cropId: 'cotton',
        cropName: 'Cotton',
        imageSource: ReportImageSource.camera,
        answers: const [
          QuestionAnswer(
            questionId: 'symptom_description',
            questionAudioAsset: 'assets/audio/05_symptom_description.mp3',
            answerText: '    ', // STT produced nothing but whitespace
            sttStatus: 'empty',
            answerDurationMs: 1500,
          ),
        ],
        location: null,
        capturedAt: DateTime(2026, 9, 4, 9, 5),
      );

      // Exactly the predicate used inside submit().
      final hasAnswer = blankReport.answers.any(
        (a) => a.answerText.trim().isNotEmpty,
      );
      expect(
        hasAnswer,
        isFalse,
        reason: 'whitespace-only transcripts must not count as answers',
      );

      // Guard clause still short-circuits: no answers, no image.
      await expectLater(
        ReportApiService.instance
            .submit(blankReport, imageBytes: null, deviceId: 'test-device')
            .timeout(const Duration(seconds: 5)),
        completes,
      );
    });
  });

  group('symptom-only report (no image) submission data', () {
    const symptomTranscript = 'پتیاں تے پیلیاں دھبے نیں';

    final symptomOnlyReport = FarmerReport(
      reportId: 'rpt_symptom_only',
      cropId: 'cotton',
      cropName: 'Cotton',
      imageSource: ReportImageSource.camera,
      imagePath: null,
      answers: const [
        QuestionAnswer(
          questionId: 'symptom_description',
          questionAudioAsset: 'assets/audio/05_symptom_description.mp3',
          answerText: symptomTranscript,
          sttStatus: 'transcribed',
          answerDurationMs: 6500,
        ),
      ],
      location: null,
      capturedAt: DateTime(2026, 9, 4, 10, 30),
    );

    test('has valid reportId, cropId and capturedAt', () {
      expect(symptomOnlyReport.reportId, 'rpt_symptom_only');
      expect(symptomOnlyReport.reportId, isNotEmpty);
      expect(symptomOnlyReport.cropId, 'cotton');
      expect(symptomOnlyReport.capturedAt, DateTime(2026, 9, 4, 10, 30));
      // A symptom-only report carries no image anywhere.
      expect(symptomOnlyReport.imagePath, isNull);
      expect(symptomOnlyReport.imageOssKey, isNull);
    });

    test('answer_1 carries the transcribed symptom text', () {
      expect(symptomOnlyReport.answers, hasLength(1));
      final answer = symptomOnlyReport.answers.first;
      expect(answer.questionId, 'symptom_description');
      expect(answer.answerText, symptomTranscript);
      expect(answer.sttStatus, 'transcribed');
    });

    test('serializes to JSON correctly', () {
      final json = symptomOnlyReport.toJson();

      expect(json['report_id'], 'rpt_symptom_only');
      expect(json['crop'], {
        'crop_id': 'cotton',
        'crop_name': 'Cotton',
        'selection_source': 'visual_crop_selection',
      });
      expect(json['image'], {
        'source': 'camera',
        'local_path': null,
        'oss_key': null,
      });
      expect(json['location'], isNull);

      final answersJson = json['question_answers'] as List<dynamic>;
      expect(answersJson, hasLength(1));
      expect(answersJson.first['question_id'], 'symptom_description');
      expect(answersJson.first['answer_text'], symptomTranscript);

      // The Punjabi transcript must survive a real UTF-8 encode.
      expect(() => jsonEncode(json), returnsNormally);
    });

    test('passes the submit() validation gate without an image', () {
      // Exactly the gate used by ReportApiService.submit(): submission
      // proceeds when at least one answer has non-empty trimmed text,
      // even with imageBytes == null.
      final hasAnswer = symptomOnlyReport.answers.any(
        (a) => a.answerText.trim().isNotEmpty,
      );
      expect(
        hasAnswer,
        isTrue,
        reason: 'a symptom-only report must be submittable without an image',
      );
    });
  });

  group('multipart answer-field mapping (answer_1 .. answer_4)', () {
    test('answers map in order, blanks are skipped, max 4 are sent', () {
      // Mirrors the field-writing loop inside ReportApiService.submit():
      // only `answer_${i + 1}` of the first 4 answers is written, and only
      // when the trimmed text is non-empty.
      Map<String, String> answerFields(FarmerReport report) {
        final fields = <String, String>{};
        for (var i = 0; i < report.answers.length && i < 4; i++) {
          final text = report.answers[i].answerText.trim();
          if (text.isNotEmpty) {
            fields['answer_${i + 1}'] = text;
          }
        }
        return fields;
      }

      final report = FarmerReport(
        reportId: 'rpt_mapping',
        cropId: 'wheat',
        cropName: 'Wheat',
        imageSource: ReportImageSource.camera,
        answers: const [
          QuestionAnswer(
            questionId: 'symptom_description',
            questionAudioAsset: 'assets/audio/05_symptom_description.mp3',
            answerText: '  پہلا جواب  ', // trimmed before sending
            sttStatus: 'transcribed',
            answerDurationMs: 3000,
          ),
          QuestionAnswer(
            questionId: 'symptom_duration',
            questionAudioAsset: 'assets/audio/03_symptom_duration.m4a',
            answerText: '', // skipped entirely
            sttStatus: 'empty',
            answerDurationMs: 0,
          ),
          QuestionAnswer(
            questionId: 'affected_spread',
            questionAudioAsset: 'assets/audio/02_affected_spread.m4a',
            answerText: 'تیجا جواب',
            sttStatus: 'transcribed',
            answerDurationMs: 4000,
          ),
          QuestionAnswer(
            questionId: 'spreading_status',
            questionAudioAsset: 'assets/audio/06_spreading_status.mp3',
            answerText: '   ', // skipped entirely
            sttStatus: 'empty',
            answerDurationMs: 0,
          ),
          QuestionAnswer(
            questionId: 'extra_question',
            questionAudioAsset: 'assets/audio/extra.mp3',
            answerText: 'پنجواں جواب', // beyond answer_4: never sent
            sttStatus: 'transcribed',
            answerDurationMs: 1000,
          ),
        ],
        location: null,
        capturedAt: DateTime(2026, 9, 4, 11, 0),
      );

      expect(answerFields(report), {
        'answer_1': 'پہلا جواب',
        'answer_3': 'تیجا جواب',
      });
    });
  });

  group('FarmerReport JSON round-trip (full 4-answer report)', () {
    test('preserves all 4 answer texts for submission', () {
      final answers = QuestionBank.questions
          .map(
            (q) => QuestionAnswer(
              questionId: q.id,
              questionAudioAsset: q.audioAsset,
              answerText: 'جواب ${q.id}',
              sttStatus: 'transcribed',
              answerDurationMs: 4000,
            ),
          )
          .toList();

      final report = FarmerReport(
        reportId: 'rpt_full_round_trip',
        cropId: 'wheat',
        cropName: 'Wheat',
        imageSource: ReportImageSource.gallery,
        imagePath: '/data/reports/rpt_full_round_trip/crop.jpg',
        answers: answers,
        location: const ReportLocation(
          latitude: 30.1575,
          longitude: 71.5249,
          accuracyM: 8.5,
          status: 'captured',
        ),
        capturedAt: DateTime(2026, 9, 3, 16, 45),
      );

      final decoded = FarmerReport.fromJson(
        jsonDecode(jsonEncode(report.toJson())),
      );

      // All 4 transcribed answers survive verbatim.
      expect(decoded.answers, hasLength(4));
      expect(
        decoded.answers.map((a) => a.answerText).toList(),
        answers.map((a) => a.answerText).toList(),
      );
      expect(
        decoded.answers.map((a) => a.questionId).toList(),
        QuestionBank.questions.map((q) => q.id).toList(),
      );

      // Location feeds the latitude/longitude form fields — it must
      // survive too.
      expect(decoded.location?.latitude, 30.1575);
      expect(decoded.location?.longitude, 71.5249);
      expect(decoded.location?.status, 'captured');

      expect(decoded.reportId, 'rpt_full_round_trip');
      expect(decoded.cropId, 'wheat');
      expect(decoded.capturedAt, DateTime(2026, 9, 3, 16, 45));
    });
  });
}
