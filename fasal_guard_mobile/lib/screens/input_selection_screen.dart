import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../config/crop_registry.dart';
import '../models/farmer_report.dart';
import '../services/report_session.dart';
import '../widgets/action_card.dart';
import '../widgets/app_top_bar.dart';

/// Step 2 of the main flow: choose how the farmer provides the crop image.
/// Camera / Gallery continue to photo capture + validation + questions.
class InputSelectionScreen extends StatelessWidget {
  const InputSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final cropId = ReportSession.current.cropId ?? '';
    final crop = CropRegistry.byId(cropId);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.cream,
        appBar: const AppTopBar(title: 'ان پٹ چُنو'),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 6, 20, 20),
            child: Column(
              children: [
                Text(
                  crop == null
                      ? 'تصویر کھچو یا گیلری چوں چُنو'
                      : '${crop.namePunjabi} - تصویر کھچو یا گیلری چوں چُنو',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppTheme.darkGreen,
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 24),
                ActionCard(
                  icon: Icons.camera_alt_rounded,
                  title: 'تصویر کھچو',
                  iconSize: 51,
                  lines: const [
                    'فصل دے متاثرہ پتے دی',
                    'صاف تصویر کھچو۔',
                  ],
                  onTap: () {
                    ReportSession.current.imageSource =
                        ReportImageSource.camera;
                    Navigator.of(context).pushNamed(AppRoutes.capture,
                        arguments: CaptureArgs(source: ImageSourceChoice.camera));
                  },
                ),
                const SizedBox(height: 16),
                ActionCard(
                  icon: Icons.photo_library_rounded,
                  title: 'گیلری چوں چُنو',
                  iconSize: 48,
                  lines: const [
                    'پہلے توں موجود تصویر',
                    'چُنو۔',
                  ],
                  onTap: () {
                    ReportSession.current.imageSource =
                        ReportImageSource.gallery;
                    Navigator.of(context).pushNamed(AppRoutes.capture,
                        arguments:
                            CaptureArgs(source: ImageSourceChoice.gallery));
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Route arguments for the capture screen.
enum ImageSourceChoice { camera, gallery }

class CaptureArgs {
  final ImageSourceChoice source;
  const CaptureArgs({required this.source});
}
