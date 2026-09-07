import 'dart:async';

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/farmer_notification.dart';
import '../services/device_service.dart';
import '../services/notification_api_service.dart';
import '../services/notification_cache_service.dart';
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
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  late final AnimationController _controller;

  late final Animation<double> _headerOpacity;
  late final Animation<Offset> _headerSlide;

  late final Animation<double> _welcomeOpacity;
  late final Animation<double> _welcomeScale;

  late final Animation<double> _card1Opacity;
  late final Animation<Offset> _card1Slide;

  late final Animation<double> _card2Opacity;
  late final Animation<Offset> _card2Slide;

  // Notification alerting
  Timer? _notifPollTimer;
  int _unreadCount = 0;
  Set<String> _knownIds = {};

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

    // Notification polling + alerting
    WidgetsBinding.instance.addObserver(this);
    _checkNotifications();
    _notifPollTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _checkNotifications(),
    );
  }

  @override
  void dispose() {
    _notifPollTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _controller.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _checkNotifications();
  }

  /// Fetches notifications and shows an alert if new ones arrived.
  Future<void> _checkNotifications() async {
    try {
      final list = await NotificationApiService.instance.fetchNotifications(
        DeviceService.instance.deviceId,
      );
      if (!mounted) return;

      final newOnes = list
          .where((n) => !_knownIds.contains(n.notificationId))
          .toList();
      setState(() {
        _knownIds = list.map((n) => n.notificationId).toSet();
        _unreadCount = list.where((n) => n.status != 'read').length;
      });

      // Show alert for newly-arrived notifications.
      if (newOnes.isNotEmpty) {
        _showNotificationAlert(newOnes);
      }
    } catch (_) {
      // Offline – just read from cache.
      if (!mounted) return;
      setState(() {
        _unreadCount = NotificationCacheService.instance.unreadCount;
      });
    }
  }

  /// Shows a prominent dialog for new notification(s).
  void _showNotificationAlert(List<FarmerNotification> newOnes) {
    final n = newOnes.first; // Alert for the newest one.
    final title = n.title;
    final message = n.messageLocal ?? n.message;
    final isRedAlert = n.status == 'red' || n.alertId != null;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        backgroundColor: AppTheme.cardWhite,
        icon: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            color: isRedAlert
                ? const Color(0xFFFBE9E7)
                : const Color(0xFFE6EDD5),
            shape: BoxShape.circle,
          ),
          child: Icon(
            isRedAlert
                ? Icons.warning_rounded
                : Icons.notifications_active_rounded,
            color: isRedAlert ? AppTheme.danger : AppTheme.darkGreen,
            size: 30,
          ),
        ),
        title: Text(
          title,
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
            color: AppTheme.darkGreen,
          ),
        ),
        content: Text(
          message,
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 15,
            color: Color(0xFF3C4A3E),
            height: 1.4,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text(
              'بعد وچ',
              style: TextStyle(
                color: AppTheme.darkGreen,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              Navigator.pushNamed(
                context,
                AppRoutes.notificationDetail,
                arguments: n,
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.darkGreen,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text(
              'ویکھو',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
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
      child: Stack(
        children: [
          Row(
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
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            child: Center(
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  IconButton(
                    icon: const Icon(
                      Icons.notifications_outlined,
                      color: AppTheme.darkGreen,
                      size: 28,
                    ),
                    onPressed: () async {
                      await Navigator.of(context)
                          .pushNamed(AppRoutes.notifications);
                      // Refresh badge count when returning.
                      if (mounted) _checkNotifications();
                    },
                  ),
                  if (_unreadCount > 0)
                    Positioned(
                      right: 4,
                      top: 4,
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: const BoxDecoration(
                          color: AppTheme.danger,
                          shape: BoxShape.circle,
                        ),
                        constraints: const BoxConstraints(
                          minWidth: 18,
                          minHeight: 18,
                        ),
                        child: Text(
                          _unreadCount > 9 ? '9+' : '$_unreadCount',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                ],
              ),
            ),
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
  /// Home / Reports instead of Home / Chat.
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
            const SizedBox(width: 22),
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
