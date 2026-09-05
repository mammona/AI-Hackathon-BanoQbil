// Temporary diagnostic: replicate ImageValidationService gates on known
// files to find which gate lets random images/screenshots through.
// Run: dart run tool/diag_validate.dart
import 'dart:io';
import 'dart:math' as math;

import 'package:image/image.dart' as img;

const double minSharpness = 4.0;
const double minBrightness = 16.0;
const double maxBrightness = 246.0;
const double minContrast = 6.0;
const double minPlantRatio = 0.25;

double plantRatio(img.Image image) {
  var plant = 0;
  final n = image.width * image.height;
  for (final p in image) {
    final r = p.r / 255.0;
    final g = p.g / 255.0;
    final b = p.b / 255.0;
    final mx = math.max(r, math.max(g, b));
    final mn = math.min(r, math.min(g, b));
    final d = mx - mn;
    if (mx < 0.12) continue;
    if (mx > 0 && d / mx < 0.15) continue;
    var h = 0.0;
    if (d > 0) {
      if (mx == r) {
        h = 60 * (((g - b) / d) % 6);
      } else if (mx == g) {
        h = 60 * ((b - r) / d + 2);
      } else {
        h = 60 * ((r - g) / d + 4);
      }
    }
    if (h < 0) h += 360;
    if (h >= 35 && h <= 170) plant++;
  }
  return plant / n;
}

void check(String path) {
  final f = File(path);
  if (!f.existsSync()) {
    print('${path.padRight(52)} MISSING');
    return;
  }
  final decoded = img.decodeImage(f.readAsBytesSync());
  if (decoded == null) {
    print('${path.padRight(52)} decode-fail');
    return;
  }
  final resized = img.copyResize(decoded.convert(numChannels: 3),
      width: 224, height: 224, interpolation: img.Interpolation.average);
  final plant = plantRatio(resized); // before grayscale (production order)
  final grey = img.grayscale(resized);
  var sum = 0.0;
  for (final p in grey) {
    sum += p.r;
  }
  final n = grey.width * grey.height;
  final mean = sum / n;
  var sq = 0.0;
  for (final p in grey) {
    final d = p.r - mean;
    sq += d * d;
  }
  final contrast = math.sqrt(sq / n);
  var lapSq = 0.0;
  var count = 0;
  var lapSum = 0.0;
  for (var y = 1; y < grey.height - 1; y++) {
    for (var x = 1; x < grey.width - 1; x++) {
      final v = -4.0 * grey.getPixel(x, y).r +
          grey.getPixel(x - 1, y).r +
          grey.getPixel(x + 1, y).r +
          grey.getPixel(x, y - 1).r +
          grey.getPixel(x, y + 1).r;
      lapSum += v;
      lapSq += v * v;
      count++;
    }
  }
  final lapMean = lapSum / count;
  final lapVar = lapSq / count - lapMean * lapMean;

  String? reject;
  if (lapVar < minSharpness) reject = 'tooBlurry';
  if (mean < minBrightness) reject = 'tooDark';
  if (mean > maxBrightness) reject = 'tooBright';
  if (contrast < minContrast) reject = 'noDetail';
  if (plant < minPlantRatio) reject = 'notACropLeaf';

  print('${path.padRight(52)} '
      'sharp=${lapVar.toStringAsFixed(1).padLeft(9)} '
      'bright=${mean.toStringAsFixed(1).padLeft(6)} '
      'contrast=${contrast.toStringAsFixed(1).padLeft(6)} '
      'plant=${plant.toStringAsFixed(2).padLeft(5)} '
      '=> ${reject ?? "VALID (reaches model)"}');
}

void main() {
  final paths = [
    // real leaf photos (should be VALID)
    'assets/images/test/cotton_bb.jpg',
    'assets/images/test/cotton_cv.jpg',
    'assets/images/test/cotton_fw.jpg',
    'assets/images/test/cotton_h.jpg',
    'assets/images/test/rice_bb.jpg',
    'assets/images/test/rice_blast.jpg',
    'assets/images/test/rice_bs.jpg',
    // app UI screenshots (green theme!) - should be REJECTED
    'd:/Faisal-shield/m1_app_running.png',
    'd:/Faisal-shield/s_home.png',
    'd:/Faisal-shield/j_picker.png',
    'd:/Faisal-shield/c1.png',
    'd:/Faisal-shield/home_check.png',
    'd:/Faisal-shield/p1.png',
    'd:/Faisal-shield/t_probe.png',
    'd:/Faisal-shield/i_home.png',
    // random unrelated images - should be REJECTED
    'assets/images/welcome_bg.jpg',
    'assets/images/logo.png',
    'assets/images/crops/wheat.jpg',
  ];
  for (final p in paths) {
    check(p);
  }
}
