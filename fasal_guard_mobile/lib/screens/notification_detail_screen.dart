import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../config/crop_registry.dart';
import '../models/farmer_notification.dart';
import '../services/notification_api_service.dart';
import '../services/report_session.dart';
import '../widgets/app_buttons.dart';
import '../widgets/app_top_bar.dart';

/// Full detail view of one backend notification (disease alert). Opening
/// the screen marks the notification as read (local cache + backend). The
/// bottom button starts the normal report flow with the alert's crop
/// already preselected.
class NotificationDetailScreen extends StatefulWidget {
  final FarmerNotification notification;

  const NotificationDetailScreen({super.key, required this.notification});

  @override
  State<NotificationDetailScreen> createState() =>
      _NotificationDetailScreenState();
}

class _NotificationDetailScreenState extends State<NotificationDetailScreen> {
  @override
  void initState() {
    super.initState();
    // Fire-and-forget: opening the alert marks it as read.
    NotificationApiService.instance.markRead(
      widget.notification.notificationId,
    );
  }

  @override
  Widget build(BuildContext context) {
    final n = widget.notification;
    // RED disease alerts show a prominent warning banner on top.
    final isRedAlert = n.status == 'red' || n.alertId != null;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.cream,
        appBar: const AppTopBar(title: 'تفصیلات'),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (isRedAlert) _redAlertBanner(),
                const SizedBox(height: 14),
                _detailsCard(),
                const SizedBox(height: 24),
                if (n.crop != null)
                  PrimaryButton(
                    icon: Icons.camera_alt_rounded,
                    text: 'اپنی فصل دی رپورٹ کرو',
                    onTap: _startReport,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Prominent red banner for RED alerts.
  Widget _redAlertBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0xFFFBE9E7),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE6B0AA)),
      ),
      child: const Row(
        children: [
          Icon(Icons.warning_rounded, color: AppTheme.danger, size: 32),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'ریڈ الرٹ',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w800,
                color: AppTheme.danger,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _detailsCard() {
    final n = widget.notification;
    final message = n.messageLocal ?? n.message;
    final cropName = n.crop == null
        ? ''
        : CropRegistry.byId(n.crop!)?.nameEn ?? n.crop!;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardWhite,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.borderSoft),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            n.title,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              height: 1.35,
              color: AppTheme.darkGreen,
            ),
          ),
          const SizedBox(height: 10),
          if (cropName.isNotEmpty) _row(Icons.grass_rounded, cropName),
          const SizedBox(height: 6),
          Text(
            message,
            style: const TextStyle(
              fontSize: 15,
              height: 1.6,
              color: Color(0xFF3C4A3E),
            ),
          ),
          const SizedBox(height: 12),
          if (n.distanceKm != null)
            _row(
              Icons.near_me_rounded,
              'فاصلہ: ${n.distanceKm!.toStringAsFixed(1)} کلومیٹر',
            ),
          _row(Icons.access_time_rounded, _formatDate(n.createdAt)),
          const SizedBox(height: 12),
          _statusBadge(),
        ],
      ),
    );
  }

  Widget _row(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Icon(icon, size: 20, color: AppTheme.deepGreen),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 14, color: Color(0xFF3C4A3E)),
            ),
          ),
        ],
      ),
    );
  }

  /// Read / unread chip (same badge style as the reports sync badges).
  Widget _statusBadge() {
    final read = widget.notification.status == 'read';
    final (color, bg, border, text) = read
        ? (
            const Color(0xFF2F6B1E),
            const Color(0xFFE3EED0),
            const Color(0xFFBCD69A),
            'پڑھی گئی',
          )
        : (
            AppTheme.darkGreen,
            AppTheme.lightGreenFill,
            AppTheme.borderSoft,
            'نئی',
          );
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  /// Starts the normal report flow with the alert's crop preselected, so
  /// the farmer goes straight to image input (crop selection is skipped).
  void _startReport() {
    final crop = widget.notification.crop;
    if (crop == null) return;
    final cropConfig = CropRegistry.byId(crop);
    ReportSession.current.reset(crop, cropConfig?.nameEn ?? crop);
    Navigator.pushNamed(context, AppRoutes.inputSelection);
  }

  static const _months = [
    'جنوری',
    'فروری',
    'مارچ',
    'اپریل',
    'مئی',
    'جون',
    'جولائی',
    'اگست',
    'ستمبر',
    'اکتوبر',
    'نومبر',
    'دسمبر',
  ];

  String _formatDate(DateTime d) =>
      '${d.day} ${_months[d.month - 1]} ${d.year} · '
      '${d.hour.toString().padLeft(2, '0')}:'
      '${d.minute.toString().padLeft(2, '0')}';
}
