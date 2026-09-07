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
                const Text(
                  'تہاڈی رپورٹ فون وچ محفوظ اے',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16, color: Color(0xFF3C4A3E)),
                ),
                const SizedBox(height: 8),
                if (report.syncStatus == 'synced')
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE3EED0),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: const Color(0xFFBCD69A)),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.cloud_done_rounded,
                            size: 18, color: AppTheme.darkGreen),
                        SizedBox(width: 8),
                        Text(
                          'رپورٹ سرور نوں کامیابی نال بھیج دتی گئی اے',
                          style: TextStyle(
                              fontSize: 13, color: AppTheme.darkGreen),
                        ),
                      ],
                    ),
                  )
                else
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE3F2FD),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: const Color(0xFFBBDEFB)),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.sync_rounded,
                            size: 18, color: Color(0xFF1976D2)),
                        SizedBox(width: 8),
                        Text(
                          'رپورٹ محفوظ اے، انٹرنیٹ ملدے ہی بھیج دتی جاوے گی',
                          style: TextStyle(
                              fontSize: 13, color: Color(0xFF1976D2)),
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
                  onTap: () => Navigator.of(context)
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
