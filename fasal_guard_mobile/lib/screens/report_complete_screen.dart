import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/farmer_report.dart';
import '../widgets/app_buttons.dart';

/// Step 6 of the main flow: report saved confirmation (plan section 32).
class ReportCompleteScreen extends StatelessWidget {
  final FarmerReport report;

  const ReportCompleteScreen({super.key, required this.report});

  @override
  Widget build(BuildContext context) {
    // Reflect the real sync outcome: 'synced' means the report already
    // reached the backend; anything else is still queued for later.
    final bool synced = report.syncStatus == 'synced';
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.softCream,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 110,
                  height: 110,
                  decoration: const BoxDecoration(
                    color: Color(0xFFE3EED0),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.check_rounded,
                    color: AppTheme.darkGreen,
                    size: 64,
                  ),
                ),
                const SizedBox(height: 26),
                const Text(
                  'رپورٹ محفوظ ہو گئی',
                  style: TextStyle(
                    color: AppTheme.darkGreen,
                    fontSize: 26,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  synced
                      ? 'تہاڈی رپورٹ سرور تے کامیابی نال بھیج دتی گئی اے'
                      : 'تہاڈی رپورٹ فون وچ محفوظ اے',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 16,
                    color: Color(0xFF3C4A3E),
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: synced
                        ? const Color(0xFFE3EED0)
                        : const Color(0xFFFFF7E0),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: synced
                          ? const Color(0xFFB7D3A0)
                          : const Color(0xFFEAD9A0),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        synced
                            ? Icons.cloud_done_rounded
                            : Icons.cloud_off_rounded,
                        size: 18,
                        color: synced
                            ? AppTheme.darkGreen
                            : const Color(0xFF8A6D1A),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        synced ? 'رپورٹ سرور تے پہنچ گئی اے' : 'جدوں انٹرنیٹ ملے گا تے سرور نوں بھیج دتی جاوے گی',
                        style: TextStyle(
                          fontSize: 13,
                          color: synced
                              ? AppTheme.darkGreen
                              : const Color(0xFF8A6D1A),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 40),
                PrimaryButton(
                  icon: Icons.add_rounded,
                  text: 'نویں رپورٹ بناؤ',
                  onTap: () => Navigator.of(context)
                      .popUntil(ModalRoute.withName(AppRoutes.cropSelection)),
                ),
                const SizedBox(height: 12),
                SecondaryButton(
                  icon: Icons.home_rounded,
                  text: 'ہوم تے جاؤ',
                  onTap: () =>
                      Navigator.of(context)
                          .popUntil(ModalRoute.withName(AppRoutes.home)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
