import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../widgets/action_card.dart';

/// Home screen. Built from the ORIGINAL chat landing page design
/// (assistant badge, greeting, animated action cards, bottom navigation)
/// but wired to the new flow: start a report or open report history.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  late final Animation<double> _headerOpacity;
  late final Animation<Offset> _headerSlide;

  late final Animation<double> _welcomeOpacity;
  late final Animation<double> _welcomeScale;

  late final Animation<double> _card1Opacity;
  late final Animation<Offset> _card1Slide;

  late final Animation<double> _card2Opacity;
  late final Animation<Offset> _card2Slide;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1450),
    );

    _headerOpacity = _fade(0.00, 0.28);
    _headerSlide = _slide(0.00, 0.30);

    _welcomeOpacity = _fade(0.16, 0.46);
    _welcomeScale = Tween<double>(begin: 0.82, end: 1).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.12, 0.48, curve: Curves.easeOutBack),
      ),
    );

    _card1Opacity = _fade(0.34, 0.68);
    _card1Slide = _slide(0.34, 0.68);

    _card2Opacity = _fade(0.54, 0.92);
    _card2Slide = _slide(0.54, 0.92);

    _controller.forward();
  }

  Animation<double> _fade(double start, double end) {
    return Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Interval(start, end, curve: Curves.easeOut),
      ),
    );
  }

  Animation<Offset> _slide(double start, double end) {
    return Tween<Offset>(
      begin: const Offset(0, 0.15),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Interval(start, end, curve: Curves.easeOutCubic),
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.cream,
        body: SafeArea(
          child: Column(
            children: [
              Expanded(
                child: SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(20, 14, 20, 18),
                  child: Column(
                    children: [
                      FadeTransition(
                        opacity: _headerOpacity,
                        child: SlideTransition(
                          position: _headerSlide,
                          child: _buildTopBar(),
                        ),
                      ),
                      const SizedBox(height: 36),
                      FadeTransition(
                        opacity: _welcomeOpacity,
                        child: ScaleTransition(
                          scale: _welcomeScale,
                          child: _buildAssistantBadge(),
                        ),
                      ),
                      const SizedBox(height: 23),
                      FadeTransition(
                        opacity: _welcomeOpacity,
                        child: const Column(
                          children: [
                            Text(
                              'السلام علیکم!',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: AppTheme.darkGreen,
                                fontSize: 27,
                                fontWeight: FontWeight.w800,
                                height: 1.25,
                              ),
                            ),
                            SizedBox(height: 8),
                            Text(
                              'اپنی فصل دا مسئلہ دسو',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Color(0xFF173E24),
                                fontSize: 22,
                                fontWeight: FontWeight.w700,
                                height: 1.35,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 32),
                      FadeTransition(
                        opacity: _card1Opacity,
                        child: SlideTransition(
                          position: _card1Slide,
                          child: ActionCard(
                            icon: Icons.camera_alt_rounded,
                            title: 'فصل دی رپورٹ کرو',
                            iconSize: 51,
                            lines: const [
                              'فصل چُنو، تصویر کھچو،',
                              'بیماری دی پہچان کرو',
                              'تے رپورٹ محفوظ کرو۔',
                            ],
                            onTap: () =>
                                Navigator.of(context)
                                    .pushNamed(AppRoutes.cropSelection),
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      FadeTransition(
                        opacity: _card2Opacity,
                        child: SlideTransition(
                          position: _card2Slide,
                          child: ActionCard(
                            icon: Icons.history_rounded,
                            title: 'پراݨیاں رپورٹاں',
                            iconSize: 51,
                            lines: const ['محفوظ شدہ رپورٹاں ویکھو', 'تے سنو۔'],
                            onTap: () =>
                                Navigator.of(context)
                                    .pushNamed(AppRoutes.reports),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              _buildBottomNavigation(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return SizedBox(
      height: 58,
      width: double.infinity,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text(
            'زرعی مددگار',
            style: TextStyle(
              color: AppTheme.darkGreen,
              fontSize: 21,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(width: 10),
          Image.asset(
            'assets/images/logo.png',
            width: 46,
            height: 46,
            fit: BoxFit.contain,
          ),
        ],
      ),
    );
  }

  Widget _buildAssistantBadge() {
    const size = 78.0;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Container(
            width: size,
            height: size * 0.90,
            decoration: const BoxDecoration(
              color: Color(0xFFE6EDD5),
              shape: BoxShape.circle,
            ),
          ),
          Positioned(
            bottom: 2,
            left: 6,
            child: Transform.rotate(
              angle: 0.65,
              child: Container(
                width: 18,
                height: 18,
                decoration: const BoxDecoration(
                  color: Color(0xFFE6EDD5),
                  borderRadius: BorderRadius.only(
                    bottomRight: Radius.circular(4),
                  ),
                ),
              ),
            ),
          ),
          const Icon(Icons.eco_rounded, color: Color(0xFF268532), size: 43),
        ],
      ),
    );
  }

  /// Bottom navigation reused from the original chat UI, now wired to
  /// Home / Alerts / Reports instead of Home / Chat.
  Widget _buildBottomNavigation() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 9, 20, 13),
      decoration: const BoxDecoration(
        color: Color(0xFFFFFEFA),
        border: Border(top: BorderSide(color: Color(0xFFE5E5DE))),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: _NavButton(
                icon: Icons.home_rounded,
                label: 'ہوم',
                selected: true,
                onTap: () {},
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _NavButton(
                icon: Icons.notifications_rounded,
                label: 'الرٹ',
                selected: false,
                onTap: () =>
                    Navigator.of(context).pushNamed(AppRoutes.notifications),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _NavButton(
                icon: Icons.history_rounded,
                label: 'رپورٹاں',
                selected: false,
                onTap: () => Navigator.of(context).pushNamed(AppRoutes.reports),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _NavButton({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? const Color(0xFFF2F3E8) : Colors.transparent,
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 9),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: AppTheme.deepGreen, size: 27),
              const SizedBox(height: 3),
              Text(
                label,
                style: TextStyle(
                  color: const Color(0xFF075B29),
                  fontSize: 13,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
