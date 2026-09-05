import 'dart:async';

import 'package:flutter/material.dart';

import '../config/app_theme.dart';

/// Splash screen. Auto-opens the home screen after 5 seconds.

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen>
    with TickerProviderStateMixin {
  static const Color darkGreen = Color(0xFF0D5C2B);
  static const Color softCream = Color(0xFFF9F6EA);

  late final AnimationController _introController;

  late final Animation<double> _logoScale;
  late final Animation<double> _logoOpacity;

  late final Animation<Offset> _titleSlide;
  late final Animation<double> _titleOpacity;

  late final Animation<Offset> _card1Slide;
  late final Animation<double> _card1Opacity;

  late final Animation<Offset> _card2Slide;
  late final Animation<double> _card2Opacity;

  late final Animation<Offset> _card3Slide;
  late final Animation<double> _card3Opacity;

  late final Animation<Offset> _bottomSlide;
  late final Animation<double> _bottomOpacity;

  Timer? _navigationTimer;

  @override
  void initState() {
    super.initState();

    _introController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2300),
    );

    _logoScale = Tween<double>(
      begin: 0.72,
      end: 1,
    ).animate(
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(
          0.00,
          0.28,
          curve: Curves.easeOutBack,
        ),
      ),
    );

    _logoOpacity = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(
          0.00,
          0.22,
          curve: Curves.easeOut,
        ),
      ),
    );

    _titleSlide = Tween<Offset>(
      begin: const Offset(0, 0.22),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(
          0.12,
          0.40,
          curve: Curves.easeOutCubic,
        ),
      ),
    );

    _titleOpacity = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(
      CurvedAnimation(
        parent: _introController,
        curve: const Interval(
          0.12,
          0.38,
          curve: Curves.easeOut,
        ),
      ),
    );

    _card1Slide = _slideAnimation(0.28, 0.54);
    _card1Opacity = _fadeAnimation(0.28, 0.52);

    _card2Slide = _slideAnimation(0.40, 0.68);
    _card2Opacity = _fadeAnimation(0.40, 0.66);

    _card3Slide = _slideAnimation(0.54, 0.82);
    _card3Opacity = _fadeAnimation(0.54, 0.80);

    _bottomSlide = _slideAnimation(0.68, 1.00);
    _bottomOpacity = _fadeAnimation(0.68, 0.96);

    _introController.forward();

    // Welcome page stays visible for 5 seconds,
    // then automatically opens the home screen.
    _navigationTimer = Timer(
      const Duration(seconds: 5),
      () {
        if (!mounted) return;

        Navigator.of(context).pushReplacementNamed(
          AppRoutes.home,
        );
      },
    );
  }

  Animation<Offset> _slideAnimation(
    double begin,
    double end,
  ) {
    return Tween<Offset>(
      begin: const Offset(0, 0.22),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _introController,
        curve: Interval(
          begin,
          end,
          curve: Curves.easeOutCubic,
        ),
      ),
    );
  }

  Animation<double> _fadeAnimation(
    double begin,
    double end,
  ) {
    return Tween<double>(
      begin: 0,
      end: 1,
    ).animate(
      CurvedAnimation(
        parent: _introController,
        curve: Interval(
          begin,
          end,
          curve: Curves.easeOut,
        ),
      ),
    );
  }

  @override
  void dispose() {
    _navigationTimer?.cancel();
    _introController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: softCream,
      body: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          final height = constraints.maxHeight;

          final horizontalPadding =
              (width * 0.085).clamp(22.0, 42.0);

          return Stack(
            fit: StackFit.expand,
            children: [
              Image.asset(
                'assets/images/welcome_bg.jpg',
                fit: BoxFit.cover,
                alignment: Alignment.center,
              ),

              Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Color.fromRGBO(255, 252, 241, 0.14),
                      Color.fromRGBO(255, 250, 232, 0.00),
                      Color.fromRGBO(24, 74, 22, 0.12),
                    ],
                  ),
                ),
              ),

              SafeArea(
                child: Padding(
                  padding: EdgeInsets.fromLTRB(
                    horizontalPadding,
                    height * 0.035,
                    horizontalPadding,
                    height * 0.022,
                  ),
                  child: Column(
                    children: [
                      _buildBrandHeader(width),

                      const Spacer(),

                      _animatedCard(
                        opacity: _card1Opacity,
                        slide: _card1Slide,
                        child: const _FeatureCard(
                          icon: Icons.local_florist_rounded,
                          title: 'بیماری پچھانو',
                          firstLine: 'پتے دی تصویر بھیجو،',
                          secondLine: 'AI بیماری دسے گا',
                        ),
                      ),

                      SizedBox(height: height * 0.016),

                      _animatedCard(
                        opacity: _card2Opacity,
                        slide: _card2Slide,
                        child: const _FeatureCard(
                          icon: Icons.mic_rounded,
                          title: 'آواز نال دسو',
                          firstLine: 'پنجابی وچ سوالاں دے جواب',
                          secondLine: 'آواز نال ریکارڈ کرو',
                        ),
                      ),

                      SizedBox(height: height * 0.016),

                      _animatedCard(
                        opacity: _card3Opacity,
                        slide: _card3Slide,
                        child: const _ServiceCard(),
                      ),

                      SizedBox(height: height * 0.016),

                      FadeTransition(
                        opacity: _bottomOpacity,
                        child: SlideTransition(
                          position: _bottomSlide,
                          child: const _BottomLanguagePanel(),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildBrandHeader(double width) {
    final logoSize = (width * 0.145).clamp(54.0, 78.0);

    return Column(
      children: [
        FadeTransition(
          opacity: _logoOpacity,
          child: ScaleTransition(
            scale: _logoScale,
            child: Image.asset(
              'assets/images/logo.png',
              width: logoSize,
              height: logoSize,
              fit: BoxFit.contain,
            ),
          ),
        ),

        SizedBox(height: width * 0.016),

        FadeTransition(
          opacity: _titleOpacity,
          child: SlideTransition(
            position: _titleSlide,
            child: Column(
              children: [
                const Text(
                  'AI',
                  textDirection: TextDirection.ltr,
                  style: TextStyle(
                    color: darkGreen,
                    fontSize: 27,
                    fontWeight: FontWeight.w800,
                    height: 1,
                  ),
                ),

                const SizedBox(height: 3),

                Text(
                  'فصل شیلڈ',
                  textDirection: TextDirection.rtl,
                  style: TextStyle(
                    color: darkGreen,
                    fontSize:
                        (width * 0.095).clamp(34.0, 43.0),
                    fontWeight: FontWeight.w800,
                    height: 1.15,
                  ),
                ),

                const SizedBox(height: 8),

                Text(
                  'آپ دا زرعی ساتھی',
                  textDirection: TextDirection.rtl,
                  style: TextStyle(
                    color: const Color(0xFF183E27),
                    fontSize:
                        (width * 0.047).clamp(17.0, 21.0),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _animatedCard({
    required Animation<double> opacity,
    required Animation<Offset> slide,
    required Widget child,
  }) {
    return FadeTransition(
      opacity: opacity,
      child: SlideTransition(
        position: slide,
        child: child,
      ),
    );
  }
}

class _FeatureCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String firstLine;
  final String secondLine;

  const _FeatureCard({
    required this.icon,
    required this.title,
    required this.firstLine,
    required this.secondLine,
  });

  static const Color darkGreen = Color(0xFF0D5C2B);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: 22,
        vertical: 18,
      ),
      decoration: BoxDecoration(
        color: const Color.fromRGBO(
          255,
          255,
          250,
          0.94,
        ),
        borderRadius: BorderRadius.circular(23),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(0, 0, 0, 0.12),
            blurRadius: 18,
            offset: Offset(0, 7),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 68,
            height: 68,
            decoration: const BoxDecoration(
              color: Color(0xFFEAF0DA),
              shape: BoxShape.circle,
            ),
            child: Icon(
              icon,
              color: darkGreen,
              size: 42,
            ),
          ),

          const SizedBox(width: 22),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  title,
                  textDirection: TextDirection.rtl,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    color: darkGreen,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),

                const SizedBox(height: 7),

                SizedBox(
                  width: double.infinity,
                  child: Text(
                    firstLine,
                    textDirection: TextDirection.rtl,
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                      color: Color(0xFF1D2D24),
                      fontSize: 15,
                      height: 1.35,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),

                const SizedBox(height: 2),

                SizedBox(
                  width: double.infinity,
                  child: Text(
                    secondLine,
                    textDirection: TextDirection.rtl,
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                      color: Color(0xFF1D2D24),
                      fontSize: 15,
                      height: 1.35,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ServiceCard extends StatelessWidget {
  const _ServiceCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: 21,
        vertical: 14,
      ),
      decoration: BoxDecoration(
        color: const Color.fromRGBO(
          232,
          240,
          199,
          0.90,
        ),
        borderRadius: BorderRadius.circular(21),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: const BoxDecoration(
              color: Color(0xFFD6E6AE),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.eco_rounded,
              color: Color(0xFF358E36),
              size: 30,
            ),
          ),

          const SizedBox(width: 15),

          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  'بیماری خدمت',
                  textDirection: TextDirection.rtl,
                  textAlign: TextAlign.right,
                  style: TextStyle(
                    color: Color(0xFF153F24),
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),

                SizedBox(height: 5),

                SizedBox(
                  width: double.infinity,
                  child: Text(
                    'فصل دی بیماری دی پہچان، مشورہ',
                    textDirection: TextDirection.rtl,
                    textAlign: TextAlign.right,
                    style: TextStyle(
                      color: Color(0xFF24372A),
                      fontSize: 13,
                      height: 1.35,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),

                SizedBox(height: 2),

                SizedBox(
                  width: double.infinity,
                  child: Text(
                    'اور آسان حل - بالکل مفت',
                    textDirection: TextDirection.rtl,
                    textAlign: TextAlign.right,
                    style: TextStyle(
                      color: Color(0xFF24372A),
                      fontSize: 13,
                      height: 1.35,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BottomLanguagePanel extends StatelessWidget {
  const _BottomLanguagePanel();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: 17,
        vertical: 11,
      ),
      decoration: BoxDecoration(
        color: const Color.fromRGBO(
          255,
          255,
          250,
          0.96,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(0, 0, 0, 0.08),
            blurRadius: 10,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: const Row(
        children: [
          Expanded(
            child: _LanguageItem(
              icon: Icons.language_rounded,
              title: 'زبان',
              value: 'پنجابی',
            ),
          ),

          SizedBox(
            height: 43,
            child: VerticalDivider(
              width: 1,
              thickness: 1,
              color: Color(0xFF4C7258),
            ),
          ),

          Expanded(
            child: _LanguageItem(
              icon: Icons.volume_up_rounded,
              title: 'سنو گا',
              value: 'پنجابی وچ',
            ),
          ),
        ],
      ),
    );
  }
}

class _LanguageItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _LanguageItem({
    required this.icon,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(
          icon,
          color: const Color(0xFF0C6630),
          size: 27,
        ),

        const SizedBox(width: 10),

        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              title,
              textDirection: TextDirection.rtl,
              style: const TextStyle(
                color: Color(0xFF24382A),
                fontSize: 12,
              ),
            ),

            Text(
              value,
              textDirection: TextDirection.rtl,
              style: const TextStyle(
                color: Color(0xFF0B5D2A),
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ],
    );
  }
}