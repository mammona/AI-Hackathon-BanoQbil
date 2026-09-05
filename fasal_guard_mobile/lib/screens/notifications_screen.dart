import 'dart:async';

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../config/crop_registry.dart';
import '../models/farmer_notification.dart';
import '../services/device_service.dart';
import '../services/notification_api_service.dart';
import '../services/notification_cache_service.dart';
import '../widgets/app_top_bar.dart';

/// Notifications tab: lists the disease alerts the backend pushed for this
/// device. Data is fetched on open, polled every 45 seconds and refreshed
/// whenever the app resumes. If the backend is unreachable the offline
/// Hive cache is shown instead, so the farmer always sees the last known
/// alerts.
class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen>
    with WidgetsBindingObserver {
  List<FarmerNotification> _notifications = [];
  bool _loading = true;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _refresh();
    // Background poll so new alerts appear without a manual pull.
    _pollTimer = Timer.periodic(const Duration(seconds: 45), (_) => _refresh());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Re-fetch as soon as the farmer comes back to the app.
    if (state == AppLifecycleState.resumed) _refresh();
  }

  Future<void> _refresh() async {
    try {
      final list = await NotificationApiService.instance.fetchNotifications(
        DeviceService.instance.deviceId,
      );
      if (!mounted) return;
      setState(() {
        _notifications = list;
        _loading = false;
      });
    } catch (_) {
      // Backend unreachable: fall back to the locally cached alerts.
      final cached = NotificationCacheService.instance.getAll();
      if (!mounted) return;
      setState(() {
        _notifications = cached;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.cream,
        appBar: const AppTopBar(title: 'اطلاعات'),
        body: SafeArea(
          child: _loading
              ? const Center(
                  child: CircularProgressIndicator(color: AppTheme.darkGreen),
                )
              : _notifications.isEmpty
              ? _empty()
              : RefreshIndicator(
                  onRefresh: _refresh,
                  color: AppTheme.darkGreen,
                  child: ListView.builder(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
                    itemCount: _notifications.length,
                    itemBuilder: (context, i) => _buildCard(_notifications[i]),
                  ),
                ),
        ),
      ),
    );
  }

  Widget _empty() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 96,
            height: 96,
            decoration: const BoxDecoration(
              color: AppTheme.lightGreenFill,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.notifications_none_rounded,
              size: 48,
              color: AppTheme.darkGreen,
            ),
          ),
          const SizedBox(height: 18),
          const Text(
            'کوئی اطلاع نہیں',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              color: AppTheme.darkGreen,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCard(FarmerNotification n) {
    // RED disease alerts get a thick red accent bar on the left edge.
    // (All sides share one colour so the border keeps its rounded
    // corners; only the left side is drawn thick.)
    final isRedAlert = n.status == 'red' || n.alertId != null;
    final unread = n.status != 'read';
    final cropName = CropRegistry.byId(n.crop ?? '')?.nameEn ?? n.crop ?? '';
    final message = n.messageLocal ?? n.message;

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: AppTheme.cardWhite,
        borderRadius: BorderRadius.circular(18),
        border: isRedAlert
            ? const Border(
                top: BorderSide(color: AppTheme.danger),
                right: BorderSide(color: AppTheme.danger),
                bottom: BorderSide(color: AppTheme.danger),
                left: BorderSide(color: AppTheme.danger, width: 5),
              )
            : Border.all(color: AppTheme.borderSoft),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () => Navigator.pushNamed(
            context,
            AppRoutes.notificationDetail,
            arguments: n,
          ).then((_) => _refresh()),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _alertIcon(isRedAlert),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              n.title,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 17,
                                fontWeight: unread
                                    ? FontWeight.w800
                                    : FontWeight.w600,
                                color: AppTheme.darkGreen,
                              ),
                            ),
                          ),
                          if (unread) _unreadDot(),
                        ],
                      ),
                      if (cropName.isNotEmpty || n.distanceKm != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          [
                            if (cropName.isNotEmpty) cropName,
                            if (n.distanceKm != null)
                              '${n.distanceKm!.toStringAsFixed(1)} کلومیٹر',
                          ].join(' · '),
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF3C4A3E),
                          ),
                        ),
                      ],
                      const SizedBox(height: 4),
                      Text(
                        message,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 14,
                          height: 1.4,
                          color: Color(0xFF3C4A3E),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        _timeAgo(n.createdAt),
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF8B948B),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _alertIcon(bool isRedAlert) {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: isRedAlert ? const Color(0xFFFBE9E7) : AppTheme.lightGreenFill,
        shape: BoxShape.circle,
      ),
      child: Icon(
        isRedAlert ? Icons.warning_rounded : Icons.eco_rounded,
        color: isRedAlert ? AppTheme.danger : AppTheme.darkGreen,
        size: 24,
      ),
    );
  }

  /// Small green dot marking notifications that are not read yet.
  Widget _unreadDot() {
    return Container(
      width: 10,
      height: 10,
      margin: const EdgeInsets.only(top: 5),
      decoration: const BoxDecoration(
        color: AppTheme.darkGreen,
        shape: BoxShape.circle,
      ),
    );
  }

  /// Short Punjabi "time ago" label for a notification timestamp.
  String _timeAgo(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 1) return 'ابھی';
    if (diff.inHours < 1) return '${diff.inMinutes} منٹ پہلے';
    if (diff.inDays < 1) return '${diff.inHours} گھنٹے پہلے';
    return '${diff.inDays} دن پہلے';
  }
}
