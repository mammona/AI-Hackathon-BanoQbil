import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

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
    final baseTheme = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: darkGreen),
    );

    return baseTheme.copyWith(
      textTheme: GoogleFonts.notoNastaliqUrduTextTheme(baseTheme.textTheme).copyWith(
        // Force extra height for all text to prevent Urdu dots from clipping.
        // Increased font size for better readability of Punjabi Shahmukhi.
        bodyLarge: GoogleFonts.notoNastaliqUrdu(height: 2.0, fontSize: 20),
        bodyMedium: GoogleFonts.notoNastaliqUrdu(height: 2.0, fontSize: 18),
        titleLarge: GoogleFonts.notoNastaliqUrdu(height: 2.0, fontWeight: FontWeight.bold, fontSize: 22),
      ),
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
  static const notificationDetail = '/notifications/detail';
}
