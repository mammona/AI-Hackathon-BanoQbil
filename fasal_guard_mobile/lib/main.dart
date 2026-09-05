import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

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

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Groq API key for Whisper speech-to-text (local .env, gitignored).
  await dotenv.load(fileName: '.env');

  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
  ]);

  // Offline queue: retry any OSS image uploads left over from last run.
  UploadQueueService.instance.retryPending();

  runApp(const FasalGuardApp());
}

class FasalGuardApp extends StatelessWidget {
  const FasalGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AI Fasal Shield',
      theme: ThemeData(
        useMaterial3: true,
        fontFamily: 'Arial',
      ),
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
      AppRoutes.inputSelection => _route(settings, const InputSelectionScreen()),
      AppRoutes.capture =>
        _route(settings, ImageCaptureScreen(source: (args as CaptureArgs).source)),
      AppRoutes.questions => _route(settings, const QuestionsScreen()),
      AppRoutes.complete =>
        _route(settings, ReportCompleteScreen(report: args as FarmerReport)),
      AppRoutes.reports => _route(settings, const ReportsScreen()),
      _ => null,
    };
  }

  // Keep the RouteSettings name on every route so
  // popUntil(ModalRoute.withName(...)) can find its target instead of
  // popping the whole stack (which leaves a black, route-less screen).
  MaterialPageRoute<dynamic> _route(RouteSettings settings, Widget page) =>
      MaterialPageRoute<dynamic>(builder: (_) => page, settings: settings);
}
