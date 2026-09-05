import 'dart:typed_data';

import '../models/farmer_report.dart';
import '../models/question_answer.dart';

/// One in-progress report session (plan section 33). Screens read and fill
/// this single object instead of passing many unrelated values around.
///
/// `reset()` is called the moment the farmer picks a crop, so a previous
/// report can never leak stale state into a new one (test TC-M2-05).
class ReportSession {
  static ReportSession current = ReportSession._();

  ReportSession._();

  String? cropId;
  String? cropName;
  ReportImageSource imageSource = ReportImageSource.camera;
  Uint8List? imageBytes;
  final Map<String, QuestionAnswer> answers = {};

  void reset(String newCropId, String newCropName) {
    cropId = newCropId;
    cropName = newCropName;
    imageSource = ReportImageSource.camera;
    imageBytes = null;
    answers.clear();
  }
}
