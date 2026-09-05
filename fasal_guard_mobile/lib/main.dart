import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'config/app_theme.dart';
import 'models/farmer_report.dart';
import 'screens/crop_selection_screen.dart';
import 'screens/home_screen.dart';
import 'screens/image_capture_screen.dart';
import 'screens/input_selection_screen.dart';
import 'screens/questions_screen.dart';
import 'screens/report_complete_screen.dart';
import 'screens/reports_screen.dart';
import 'screens/welcome_screen.dart';
import 'services/upload_queue_service.dart';
import 'models/farmer_notification.dart';
import 'screens/notification_detail_screen.dart';
import 'screens/notifications_screen.dart';
import 'services/device_service.dart';
import 'services/notification_cache_service.dart';
import 'config/api_config.dart';
import 'services/location_service.dart';

import 'dart:convert';
import 'dart:io';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);

  // Initialize device identity (UUID from SharedPreferences).
  await DeviceService.instance.init();

  // Initialize Hive notification cache.
  await NotificationCacheService.instance.init();

  // Offline queue: retry any OSS image uploads left over from last run.
  UploadQueueService.instance.retryPending();

  // Fire-and-forget: push GPS location to backend.
  _pushLocationOnOpen();

  // Fire-and-forget: register device with backend.
  _registerDevice();

  runApp(const FasalGuardApp());
}

/// Pushes current GPS to the backend when the app opens.
/// Completely non-blocking; failures are silently logged.
void _pushLocationOnOpen() async {
  try {
    final location = await LocationService().capture();
    if (location.status != 'captured') return;
    final deviceId = DeviceService.instance.deviceId;
    final uri = Uri.parse(ApiConfig.locationUpdateUrl(deviceId));
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 10);
    try {
      final req = await client.putUrl(uri);
      req.headers.contentType = ContentType.json;
      req.write(
        jsonEncode({
          'latitude': location.latitude,
          'longitude': location.longitude,
        }),
      );
      final res = await req.close().timeout(const Duration(seconds: 20));
      await res.drain<void>();
    } finally {
      client.close(force: true);
    }
  } catch (e) {
    // Non-blocking: GPS or network failure must never block app start.
    debugPrint('[location] push on open failed: $e');
  }
}

/// Registers device with backend (fire-and-forget).
void _registerDevice() async {
  try {
    await DeviceService.instance.register(
      crops: ['cotton', 'rice'],
      language: 'pa',
    );
  } catch (e) {
    debugPrint('[device] registration failed: $e');
  }
}

class FasalGuardApp extends StatelessWidget {
  const FasalGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AI Fasal Shield',
      theme: ThemeData(useMaterial3: true, fontFamily: 'Arial'),
      initialRoute: AppRoutes.welcome,
      onGenerateRoute: _onGenerateRoute,
    );
  }

  /// Single routing table for the whole flow. Named routes let the
  /// failure paths jump back with popUntil(ModalRoute.withName(...)).
  Route<dynamic>? _onGenerateRoute(RouteSettings settings) {
    final args = settings.arguments;
    return switch (settings.name) {
      AppRoutes.welcome => _route(settings, const WelcomeScreen()),
      AppRoutes.home => _route(settings, const HomeScreen()),
      AppRoutes.cropSelection => _route(settings, const CropSelectionScreen()),
      AppRoutes.inputSelection => _route(
        settings,
        const InputSelectionScreen(),
      ),
      AppRoutes.capture => _route(
        settings,
        ImageCaptureScreen(source: (args as CaptureArgs).source),
      ),
      AppRoutes.questions => _route(settings, const QuestionsScreen()),
      AppRoutes.complete => _route(
        settings,
        ReportCompleteScreen(report: args as FarmerReport),
      ),
      AppRoutes.reports => _route(settings, const ReportsScreen()),
      AppRoutes.notifications => _route(settings, const NotificationsScreen()),
      AppRoutes.notificationDetail => _route(
        settings,
        NotificationDetailScreen(notification: args as FarmerNotification),
      ),
      _ => null,
    };
  }

  // Keep the RouteSettings name on every route so
  // popUntil(ModalRoute.withName(...)) can find its target instead of
  // popping the whole stack (which leaves a black, route-less screen).
  MaterialPageRoute<dynamic> _route(RouteSettings settings, Widget page) =>
      MaterialPageRoute<dynamic>(builder: (_) => page, settings: settings);
}
