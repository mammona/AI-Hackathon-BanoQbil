import 'dart:typed_data';

import 'package:flutter/foundation.dart' show kDebugMode, debugPrint;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:image_picker/image_picker.dart';

import '../config/app_theme.dart';
import 'input_selection_screen.dart';
import '../services/image_validation_service.dart';
import '../services/report_session.dart';
import '../widgets/app_buttons.dart';

/// Step 3 of the main flow: take or choose the crop photo, preview it,
/// then run basic image validation and continue to the Punjabi questions.
/// Disease prediction is not part of this prototype.
///
/// The picker opens automatically for the source chosen on the input
/// selection screen. In debug builds a small harness row lets test gates
/// run known and invalid images on-device.
class ImageCaptureScreen extends StatefulWidget {
  final ImageSourceChoice source;

  const ImageCaptureScreen({super.key, required this.source});

  @override
  State<ImageCaptureScreen> createState() => _ImageCaptureScreenState();
}

class _ImageCaptureScreenState extends State<ImageCaptureScreen> {
  final ImagePicker _picker = ImagePicker();
  Uint8List? _bytes;
  bool _pickerLaunched = false;

  ImageSource get _imageSource => widget.source == ImageSourceChoice.camera
      ? ImageSource.camera
      : ImageSource.gallery;

  @override
  void initState() {
    super.initState();
    // In case Android killed the Activity while the picker was open,
    // try to recover the selected image first.
    _recoverLostImage();
  }

  Future<void> _recoverLostImage() async {
    try {
      final response = await _picker.retrieveLostData();
      if (!response.isEmpty && response.file != null) {
        final b = await response.file!.readAsBytes();
        if (!mounted) return;
        setState(() => _bytes = b);
        return;
      }
    } catch (_) {
      // Nothing to recover.
    }
    _openPicker();
  }

  Future<void> _openPicker() async {
    if (_pickerLaunched) return;
    _pickerLaunched = true;
    await _pick();
    _pickerLaunched = false;
  }

  Future<void> _pick() async {
    try {
      final x = await _picker.pickImage(
          source: _imageSource,
          imageQuality: 85,
          maxWidth: 1280,
          maxHeight: 1280);
      if (x == null) {
        // Farmer cancelled the picker: go back to input selection.
        if (mounted && _bytes == null) {
          Navigator.of(context).maybePop();
        }
        return;
      }
      final b = await x.readAsBytes();
      if (!mounted) return;
      setState(() => _bytes = b);
    } catch (e) {
      debugPrint('[image] pick failed: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('تصویر نہیں مل سکی۔ دوبارہ کوشش کرو۔',
              textAlign: TextAlign.center),
          backgroundColor: AppTheme.darkGreen));
    }
  }

  Future<void> _usePhoto(Uint8List bytes,
      {String? cropOverride}) async {
    // Basic image validation gates the photo before the report continues.
    final validation = ImageValidationService.validate(bytes);
    if (!validation.valid) {
      debugPrint('[image] rejected: ${validation.reason}');
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..clearSnackBars()
        ..showSnackBar(SnackBar(
            content: Text(_reasonText(validation.reason!),
                textAlign: TextAlign.center),
            backgroundColor: AppTheme.danger));
      return;
    }
    ReportSession.current.imageBytes = bytes;
    if (cropOverride != null) {
      ReportSession.current.cropId = cropOverride;
    }
    if (!mounted) return;
    Navigator.of(context).pushReplacementNamed(AppRoutes.questions);
  }

  String _reasonText(ImageInvalidReason reason) => switch (reason) {
        ImageInvalidReason.corruptedFile => 'تصویر پڑھی نہیں جا سکی۔ دوبارہ کھچو۔',
        ImageInvalidReason.fileTooLarge => 'تصویر بہت وڈی اے۔ دوبارہ کھچو۔',
        ImageInvalidReason.imageTooSmall => 'تصویر بہت چھوٹی اے۔ دوبارہ کھچو۔',
        ImageInvalidReason.tooBlurry => 'تصویر دھندلی اے۔ صاف تصویر کھچو۔',
        ImageInvalidReason.tooDark => 'تصویر بہت تاریک اے۔ روشنی وچ کھچو۔',
        ImageInvalidReason.tooBright => 'تصویر بہت روشن اے۔ دوبارہ کھچو۔',
        ImageInvalidReason.noDetail => 'تصویر وچ تفصیل نہیں۔ دوبارہ کھچو۔',
        ImageInvalidReason.notACropLeaf =>
          'ایہہ فصل دا پتا نہیں لگدا۔ پتے دی نیڑیوں تصویر کھچو۔',
      };

  /// Debug-only harness (never in release builds) so the test gates can
  /// run known and invalid images on-device.
  Future<void> _debugAsset(String path, {required String crop}) async {
    final b = (await rootBundle.load(path)).buffer.asUint8List();
    if (!mounted) return;
    _usePhoto(b, cropOverride: crop);
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.softCream,
        appBar: AppBar(
          backgroundColor: AppTheme.darkGreen,
          foregroundColor: AppTheme.softCream,
          title: const Text('فصل دی تصویر',
              style: TextStyle(fontWeight: FontWeight.bold)),
        ),
        body: SafeArea(
          child: Column(children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Text('فصل دے متاثرہ پتے دی صاف تصویر کھچو یا گیلری چوں چُنو',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16, color: AppTheme.darkGreen)),
            ),
            Expanded(
              child: _bytes == null ? _waiting() : _preview(),
            ),
            if (kDebugMode) _debugRow(),
          ]),
        ),
      ),
    );
  }

  Widget _waiting() {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const CircularProgressIndicator(color: AppTheme.darkGreen),
        const SizedBox(height: 16),
        TextButton.icon(
          onPressed: () {
            _pickerLaunched = false;
            _openPicker();
          },
          icon: const Icon(Icons.camera_alt, color: AppTheme.darkGreen),
          label: const Text('تصویر کھچو یا چُنو',
              style: TextStyle(color: AppTheme.darkGreen, fontSize: 16)),
        ),
      ]),
    );
  }

  Widget _preview() {
    return Column(children: [
      Expanded(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Image.memory(_bytes!, fit: BoxFit.contain),
          ),
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Column(children: [
          PrimaryButton(
            icon: Icons.check_rounded,
            text: 'ایہہ تصویر ورتو',
            onTap: () => _usePhoto(_bytes!),
          ),
          const SizedBox(height: 12),
          SecondaryButton(
            icon: Icons.refresh_rounded,
            text: 'دوبارہ کھچو',
            onTap: () {
              setState(() => _bytes = null);
              _pickerLaunched = false;
              _openPicker();
            },
          ),
        ]),
      ),
    ]);
  }

  Widget _debugRow() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
      child: Wrap(
        alignment: WrapAlignment.center,
        spacing: 6,
        runSpacing: 6,
        children: [
          _dbg('DBG cotton', () => _debugAsset(
              'assets/images/test/cotton_bb.jpg', crop: 'cotton')),
          _dbg('DBG rice', () => _debugAsset(
              'assets/images/test/rice_bb.jpg', crop: 'rice')),
          _dbg('DBG 3 cotton', () => _debugAsset(
              'assets/images/test/cotton_cv.jpg', crop: 'cotton')),
          _dbg('DBG invalid', () => _usePhoto(
              Uint8List.fromList(List<int>.generate(300, (i) => i % 256)))),
        ],
      ),
    );
  }

  Widget _dbg(String label, VoidCallback onTap) {
    return ActionChip(
      label: Text(label, style: const TextStyle(fontSize: 11)),
      onPressed: onTap,
    );
  }
}
