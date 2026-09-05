import 'dart:io';

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../config/crop_registry.dart';
import '../models/farmer_report.dart';
import '../services/report_storage_service.dart';
import '../services/upload_queue_service.dart';
import '../widgets/app_buttons.dart';
import '../widgets/app_top_bar.dart';

/// Reports tab: lists every saved farmer report, newest first. Each card
/// shows the crop, image, speech-to-text answers, GPS, timestamp and the
/// OSS image-upload (sync) status. Opening the tab also retries the
/// offline upload queue.
class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  late Future<List<FarmerReport>> _reports;

  @override
  void initState() {
    super.initState();
    _reload();
    // Retry queued OSS image uploads whenever the tab is opened.
    UploadQueueService.instance.retryPending();
  }

  void _reload() {
    setState(() {
      _reports = ReportStorageService.instance.list();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.cream,
        appBar: const AppTopBar(title: 'رپورٹاں'),
        body: SafeArea(
          child: FutureBuilder<List<FarmerReport>>(
            future: _reports,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(
                  child: CircularProgressIndicator(
                      color: AppTheme.darkGreen),
                );
              }
              final list = snapshot.data ?? const <FarmerReport>[];
              if (list.isEmpty) return _empty();
              return ListView.builder(
                padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
                itemCount: list.length,
                itemBuilder: (context, i) => _card(list[i]),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _empty() {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Container(
          width: 96,
          height: 96,
          decoration: const BoxDecoration(
            color: AppTheme.lightGreenFill,
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.folder_open_rounded,
              size: 48, color: AppTheme.darkGreen),
        ),
        const SizedBox(height: 18),
        const Text('ہالے کوئی رپورٹ نہیں',
            style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: AppTheme.darkGreen)),
        const SizedBox(height: 8),
        const Text('فصل دی رپورٹ بناؤ گا تے اوہ اتھے دِکھے گی',
            style: TextStyle(fontSize: 14, color: Color(0xFF3C4A3E))),
        const SizedBox(height: 24),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 60),
          child: PrimaryButton(
            icon: Icons.add_rounded,
            text: 'نویں رپورٹ بناؤ',
            onTap: () =>
                Navigator.of(context).pushNamed(AppRoutes.cropSelection),
          ),
        ),
      ]),
    );
  }

  Widget _card(FarmerReport report) {
    final crop = CropRegistry.byId(report.cropId);

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: AppTheme.cardWhite,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.borderSoft),
        boxShadow: const [
          BoxShadow(
              color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 2)),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () async {
            await Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => _ReportDetailScreen(report: report)));
            _reload();
          },
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(children: [
              _thumb(report),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      crop?.namePunjabi ?? report.cropName,
                      style: const TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.darkGreen),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${report.answers.where((a) => a.answerText.isNotEmpty).length} جواب',
                      style: const TextStyle(
                          fontSize: 14, color: Color(0xFF3C4A3E)),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatDate(report.capturedAt),
                      style: const TextStyle(
                          fontSize: 12, color: Color(0xFF8B948B)),
                    ),
                  ],
                ),
              ),
              _syncBadge(report.syncStatus),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _thumb(FarmerReport report) {
    const size = 62.0;
    if (report.imagePath != null &&
        File(report.imagePath!).existsSync()) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: Image.file(File(report.imagePath!),
            width: size, height: size, fit: BoxFit.cover),
      );
    }
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: AppTheme.lightGreenFill,
        borderRadius: BorderRadius.circular(14),
      ),
      child: const Icon(Icons.image_outlined,
          color: AppTheme.darkGreen, size: 30),
    );
  }

  Widget _syncBadge(String status) {
    final (color, bg, border, text) = switch (status) {
      'synced' => (
          const Color(0xFF2F6B1E),
          const Color(0xFFE3EED0),
          const Color(0xFFBCD69A),
          'تصویر بھیج دتی گئی'
        ),
      'uploading' => (
          const Color(0xFF1A5276),
          const Color(0xFFE3F0F7),
          const Color(0xFFA8CCE0),
          'بھیجی جا رہی اے'
        ),
      'failed' => (
          const Color(0xFFA93226),
          const Color(0xFFFBE9E7),
          const Color(0xFFE6B0AA),
          'بھیجی نہیں جا سکی'
        ),
      'pending_sync' || 'pending' => (
          const Color(0xFF8A6D1A),
          const Color(0xFFFFF7E0),
          const Color(0xFFEAD9A0),
          'انٹرنیٹ دا انتظار (پینڈنگ سنک)'
        ),
      _ => (
          const Color(0xFF8A6D1A),
          const Color(0xFFFFF7E0),
          const Color(0xFFEAD9A0),
          'فون وچ محفوظ'
        ),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
      ),
      child: Text(text,
          style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w600, color: color)),
    );
  }

  static const _months = [
    'جنوری', 'فروری', 'مارچ', 'اپریل', 'مئی', 'جون',
    'جولائی', 'اگست', 'ستمبر', 'اکتوبر', 'نومبر', 'دسمبر',
  ];

  String _formatDate(DateTime d) =>
      '${d.day} ${_months[d.month - 1]} ${d.year} · '
      '${d.hour.toString().padLeft(2, '0')}:'
      '${d.minute.toString().padLeft(2, '0')}';
}

/// Read-only detail view of one saved report: photo, speech-to-text
/// answers, GPS, timestamp and sync status. Deleting happens here too.
class _ReportDetailScreen extends StatelessWidget {
  final FarmerReport report;

  const _ReportDetailScreen({required this.report});

  @override
  Widget build(BuildContext context) {
    final crop = CropRegistry.byId(report.cropId);
    final hasImage =
        report.imagePath != null && File(report.imagePath!).existsSync();

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.cream,
        appBar: AppTopBar(title: crop?.namePunjabi ?? report.cropName),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(18, 12, 18, 24),
            children: [
              if (hasImage)
                ClipRRect(
                  borderRadius: BorderRadius.circular(18),
                  child: Image.file(File(report.imagePath!),
                      fit: BoxFit.cover, height: 230),
                ),
              const SizedBox(height: 16),
              _section('جواب', [
                if (report.answers.isEmpty)
                  _row(Icons.mic_off_rounded, 'کوئی جواب ریکارڈ نہیں ہویا')
                else
                  for (final a in report.answers)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _row(Icons.question_answer_rounded,
                              _answerTitle(a.questionId)),
                          Padding(
                            padding: const EdgeInsets.only(right: 30),
                            child: Text(
                              a.answerText.isEmpty ? '—' : a.answerText,
                              style: const TextStyle(
                                  fontSize: 15,
                                  height: 1.5,
                                  color: Color(0xFF3C4A3E)),
                            ),
                          ),
                        ],
                      ),
                    ),
              ]),
              const SizedBox(height: 14),
              _section('ہور جاݨکاری', [
                _row(Icons.access_time_rounded,
                    '${report.capturedAt.day}/${report.capturedAt.month}/'
                    '${report.capturedAt.year}'),
                _row(Icons.location_on_rounded, _locationText()),
                _row(Icons.cloud_rounded, _syncText()),
                if (report.imageOssKey != null)
                  _row(Icons.image_rounded, report.imageOssKey!),
              ]),
              const SizedBox(height: 26),
              DangerButton(
                icon: Icons.delete_outline_rounded,
                text: 'رپورٹ مٹاؤ',
                onTap: () => _confirmDelete(context),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _section(String title, List<Widget> children) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardWhite,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.borderSoft),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.darkGreen)),
          const SizedBox(height: 8),
          ...children,
        ],
      ),
    );
  }

  Widget _row(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(children: [
        Icon(icon, size: 20, color: AppTheme.deepGreen),
        const SizedBox(width: 10),
        Expanded(
          child: Text(text,
              style: const TextStyle(fontSize: 14, color: Color(0xFF3C4A3E))),
        ),
      ]),
    );
  }

  String _answerTitle(String questionId) => switch (questionId) {
        'symptom_description' => 'کیہ مسئلہ نظر آیا',
        'symptom_duration' => 'لچھݨ کدوں توں نیں',
        'affected_spread' => 'کتنا رقبہ متاثر اے',
        'spreading_status' => 'کیہ مسئلہ ودھ رہیا اے',
        // Legacy 3-question reports saved before the 4-question flow.
        'additional_details' => 'ہور دسیا',
        _ => 'جواب',
      };

  String _locationText() {
    final loc = report.location;
    if (loc == null || loc.status != 'captured') return 'لوکیشن نہیں ملی';
    return '${loc.latitude?.toStringAsFixed(4)}, '
        '${loc.longitude?.toStringAsFixed(4)}';
  }

  String _syncText() => switch (report.syncStatus) {
        'synced' => 'تصویر کلاؤڈ تے بھیج دتی گئی',
        'uploading' => 'تصویر بھیجی جا رہی اے',
        'failed' => 'تصویر نہیں بھیجی جا سکی (دوبارہ کوشش ہووے گی)',
        'pending_sync' || 'pending' =>
          'جدوں انٹرنیٹ ملے گا تے بھیج دتی جاوے گی',
        _ => 'رپورٹ فون وچ محفوظ اے',
      };

  Future<void> _confirmDelete(BuildContext context) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Text('رپورٹ مٹاؤ؟',
              style: TextStyle(
                  color: AppTheme.darkGreen, fontWeight: FontWeight.w800)),
          content: const Text('ایہہ رپورٹ تے اس دی تصویر فون توں ہمیشا لئی مٹ جاوے گی۔'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('نہیں',
                  style: TextStyle(color: AppTheme.darkGreen)),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child:
                  const Text('ہاں، مٹاؤ', style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
      ),
    );
    if (yes != true || !context.mounted) return;
    await ReportStorageService.instance.delete(report.reportId);
    if (!context.mounted) return;
    Navigator.of(context).pop();
  }
}
