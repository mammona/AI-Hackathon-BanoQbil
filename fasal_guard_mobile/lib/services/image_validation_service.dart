import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:image/image.dart' as img;

/// Why an image was rejected before it ever reaches the model. The codes
/// mirror the backend ImageValidator (src/services/image_validator.py) so
/// mobile and server reject the same inputs.
enum ImageInvalidReason {
  corruptedFile,
  fileTooLarge,
  imageTooSmall,
  tooBlurry,
  tooDark,
  tooBright,
  noDetail,
  notACropLeaf,
}

class ImageValidation {
  final bool valid;
  final ImageInvalidReason? reason;

  /// Decoded image, kept so inference does not decode twice.
  final img.Image? decoded;

  const ImageValidation._(this.valid, this.reason, this.decoded);

  const ImageValidation.invalid(ImageInvalidReason reason)
      : this._(false, reason, null);

  ImageValidation.ok(this.decoded)
      : valid = true,
        reason = null;
}

/// Thrown by the report pipeline when the captured bytes are not a
/// usable crop photo. Screens redirect the farmer back to Select Crop.
class InvalidImageException implements Exception {
  final ImageInvalidReason reason;
  InvalidImageException(this.reason);

  @override
  String toString() => 'Invalid image: ${reason.name}';
}

/// Validates camera/gallery bytes BEFORE inference. This is the first gate
/// against the old "100% confidence on every garbage image" problem: no
/// decodable, reasonably sized, reasonably sharp photo ever reaches the
/// model silently.
class ImageValidationService {
  static const int maxBytes = 15 * 1024 * 1024;
  static const int minDimension = 128;

  /// Quality thresholds measured on a 224x224 grayscale copy of the photo.
  /// Values are deliberately conservative so real leaf photos are never
  /// rejected by mistake; only clearly unusable frames are.
  static const double minSharpness = 4.0; // Laplacian variance
  static const double minBrightness = 16.0;
  static const double maxBrightness = 246.0;
  static const double minContrast = 6.0; // luminance std deviation

  /// Minimum fraction of leaf-like (green/yellow-green) pixels. A closed-set
  /// softmax model reports ~100% confidence for ANY sharp photo (a face, a
  /// keyboard...), so without this gate random objects would "predict" as a
  /// disease. Real leaf photos always score far above it.
  static const double minPlantRatio = 0.25;

  static ImageValidation validate(Uint8List bytes) {
    if (bytes.length > maxBytes) {
      return const ImageValidation.invalid(ImageInvalidReason.fileTooLarge);
    }

    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      return const ImageValidation.invalid(ImageInvalidReason.corruptedFile);
    }

    if (decoded.width < minDimension || decoded.height < minDimension) {
      return const ImageValidation.invalid(ImageInvalidReason.imageTooSmall);
    }

    final quality = _analyze(decoded);
    debugPrint('[validate] bytes=${bytes.length} '
        'sharp=${quality.sharpness.toStringAsFixed(1)} '
        'bright=${quality.brightness.toStringAsFixed(1)} '
        'contrast=${quality.contrast.toStringAsFixed(1)} '
        'plant=${quality.plantRatio.toStringAsFixed(2)}');
    if (quality.sharpness < minSharpness) {
      return const ImageValidation.invalid(ImageInvalidReason.tooBlurry);
    }
    if (quality.brightness < minBrightness) {
      return const ImageValidation.invalid(ImageInvalidReason.tooDark);
    }
    if (quality.brightness > maxBrightness) {
      return const ImageValidation.invalid(ImageInvalidReason.tooBright);
    }
    if (quality.contrast < minContrast) {
      return const ImageValidation.invalid(ImageInvalidReason.noDetail);
    }
    if (quality.plantRatio < minPlantRatio) {
      return const ImageValidation.invalid(ImageInvalidReason.notACropLeaf);
    }

    return ImageValidation.ok(decoded);
  }

  static _QualityStats _analyze(img.Image source) {
    final resized = img.copyResize(source,
        width: 224,
        height: 224,
        interpolation: img.Interpolation.average);
    // Plant ratio MUST be measured on the colour image, and BEFORE the
    // grayscale conversion below: img.grayscale mutates its input in this
    // package version, which would zero every hue and reject all photos.
    final plant = _plantRatio(resized);
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

    // Laplacian variance: the standard blur measure. A sharp leaf photo
    // scores far above the threshold; an out-of-focus or solid frame
    // collapses toward zero.
    var lapSq = 0.0;
    var count = 0;
    final lapValues = <double>[];
    for (var y = 1; y < grey.height - 1; y++) {
      for (var x = 1; x < grey.width - 1; x++) {
        final v = -4.0 * grey.getPixel(x, y).r +
            grey.getPixel(x - 1, y).r +
            grey.getPixel(x + 1, y).r +
            grey.getPixel(x, y - 1).r +
            grey.getPixel(x, y + 1).r;
        lapValues.add(v);
        lapSq += v * v;
        count++;
      }
    }
    final lapMean = lapValues.fold<double>(0, (a, b) => a + b) / count;
    final lapVar = lapSq / count - lapMean * lapMean;

    return _QualityStats(mean, contrast, lapVar, plant);
  }

  /// Fraction of leaf-like pixels (green to yellow-green hue, not grey and
  /// not black). This is the crop-likeness gate: it rejects random objects
  /// that the closed-set model would otherwise label with ~100% confidence.
  static double _plantRatio(img.Image image) {
    var plant = 0;
    final n = image.width * image.height;
    for (final p in image) {
      final r = p.r / 255.0;
      final g = p.g / 255.0;
      final b = p.b / 255.0;
      final mx = math.max(r, math.max(g, b));
      final mn = math.min(r, math.min(g, b));
      final d = mx - mn;
      if (mx < 0.12) continue; // too dark to be a leaf
      if (mx > 0 && d / mx < 0.15) continue; // grey/white, no colour
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
}

class _QualityStats {
  final double brightness;
  final double contrast;
  final double sharpness;
  final double plantRatio;
  const _QualityStats(
      this.brightness, this.contrast, this.sharpness, this.plantRatio);
}
