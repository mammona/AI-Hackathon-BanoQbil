import 'package:flutter/material.dart';

/// Shared app palette (dark green / cream) used by every screen.
/// Kept in one place so screens stop redeclaring their own constants.
class AppTheme {
  AppTheme._();

  static const Color darkGreen = Color(0xFF0D5C2B);
  static const Color deepGreen = Color(0xFF08652D);
  static const Color softCream = Color(0xFFF9F6EA);
  static const Color cream = Color(0xFFFCFAF3);
  static const Color cardWhite = Color(0xFFFFFEFB);
  static const Color lightGreenFill = Color(0xFFF0F3E6);
  static const Color borderSoft = Color(0xFFE8E6DD);
  static const Color danger = Color(0xFFD93B35);

  static ThemeData material() {
    return ThemeData(
      useMaterial3: true,
      fontFamily: 'Arial',
      colorScheme: ColorScheme.fromSeed(seedColor: darkGreen),
    );
  }
}

/// Central route names so `popUntil` redirects never rely on magic
/// strings in screens.
class AppRoutes {
  AppRoutes._();

  static const welcome = '/';
  static const home = '/home';
  static const cropSelection = '/crops';
  static const inputSelection = '/input';
  static const capture = '/capture';
  static const questions = '/questions';
  static const complete = '/complete';
  static const reports = '/reports';
  static const notifications = '/notifications';
  static const notificationDetail = '/notification-detail';
}
