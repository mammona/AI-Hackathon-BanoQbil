// Temporary diagnostic: measure plant-pixel ratio of test assets under
// several hue-floor candidates so the notACropLeaf gate can be tuned.
// Run: dart run tool/check_plant_ratio.dart
import 'dart:io';
import 'dart:math' as math;

import 'package:image/image.dart' as img;

double plantRatio(img.Image image, double hueFloor) {
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
    if (h >= hueFloor && h <= 170) plant++;
  }
  return plant / n;
}

void main() {
  final paths = [
    'assets/images/test/cotton_bb.jpg',
    'assets/images/test/cotton_cv.jpg',
    'assets/images/test/cotton_fw.jpg',
    'assets/images/test/cotton_h.jpg',
    'assets/images/test/rice_bb.jpg',
    'assets/images/test/rice_blast.jpg',
    'assets/images/test/rice_bs.jpg',
    '../../../c1.png',
    '../../../m1_app_running.png',
  ];
  const floors = [20.0, 25.0, 30.0, 35.0];
  for (final path in paths) {
    final f = File(path);
    if (!f.existsSync()) {
      print('${path.padRight(40)} MISSING');
      continue;
    }
    final decoded = img.decodeImage(f.readAsBytesSync());
    if (decoded == null) {
      print('${path.padRight(40)} decode-fail');
      continue;
    }
    final resized = img.copyResize(decoded.convert(numChannels: 3),
        width: 224, height: 224, interpolation: img.Interpolation.average);
    final grey = img.grayscale(resized);
    final ratios = floors
        .map((fl) => plantRatio(resized, fl).toStringAsFixed(2))
        .join(' / ');
    print('${path.padRight(40)} after-grayscale h>=20/25/30/35: $ratios  (grey0=${grey.getPixel(0, 0).r})');
  }
}
