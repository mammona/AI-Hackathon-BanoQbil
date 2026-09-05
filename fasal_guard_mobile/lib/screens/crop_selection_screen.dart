import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../config/crop_registry.dart';
import '../services/audio_service.dart';
import '../services/report_session.dart';

/// Step 1 of the main flow: VISUAL crop selection. The chosen crop id is
/// the model-routing parameter for the whole report (plan section 4).
/// Every new selection resets the report session so no stale state from a
/// previous report survives (test TC-M2-05).
class CropSelectionScreen extends StatefulWidget {
  const CropSelectionScreen({super.key});
  @override
  State<CropSelectionScreen> createState() => _CropSelectionScreenState();
}

class _CropSelectionScreenState extends State<CropSelectionScreen> {
  final AudioService _audio = AudioService();
  CropConfig? _selected;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
        (_) => _audio.playAsset('assets/audio/01_crop_selection.m4a'));
  }

  @override
  void dispose() {
    _audio.dispose();
    super.dispose();
  }

  void _tap(CropConfig crop) {
    if (!crop.enabled) {
      ScaffoldMessenger.of(context)
        ..clearSnackBars()
        ..showSnackBar(SnackBar(
            content: Text('کݨک دا ماڈل جلد آ ریہا اے\n${crop.disabledMessage}',
                textAlign: TextAlign.center),
            backgroundColor: AppTheme.darkGreen));
      return;
    }
    setState(() => _selected = crop);
  }

  void _continue() {
    final crop = _selected;
    if (crop == null) return;
    // A fresh session starts with every crop selection.
    ReportSession.current.reset(crop.cropId, crop.nameEn);
    Navigator.of(context).pushNamed(AppRoutes.inputSelection);
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: AppTheme.softCream,
        appBar: AppBar(
          backgroundColor: AppTheme.darkGreen,
          foregroundColor: AppTheme.softCream,
          title: const Text('فصل چُنو',
              style: TextStyle(fontWeight: FontWeight.bold)),
          actions: [
            IconButton(
                icon: const Icon(Icons.replay_outlined),
                onPressed: () =>
                    _audio.playAsset('assets/audio/01_crop_selection.m4a')),
          ],
        ),
        body: SafeArea(
          child: Column(children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 16, 20, 4),
              child: Text('تسی کیہڑی فصل دی رپورٹ کر رہے او؟ تصویراں وچوں اپنی فصل چُنو۔',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16, color: AppTheme.darkGreen)),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final c in CropRegistry.crops)
                    if (c.enabled) _card(c)
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: SizedBox(
                width: double.infinity,
                height: 54,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.darkGreen,
                      foregroundColor: AppTheme.softCream,
                      disabledBackgroundColor: Colors.grey.shade300,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14))),
                  onPressed: _selected == null ? null : _continue,
                  child: const Text('اگے ودھو', style: TextStyle(fontSize: 18)),
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _card(CropConfig crop) {
    final sel = _selected?.cropId == crop.cropId;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        elevation: 2,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => _tap(crop),
          child: Container(
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                    color: sel ? AppTheme.darkGreen : Colors.transparent,
                    width: 3)),
            child: Row(children: [
              ClipRRect(
                borderRadius:
                    const BorderRadius.horizontal(right: Radius.circular(16)),
                child: ColorFiltered(
                  colorFilter: crop.enabled
                      ? const ColorFilter.mode(Colors.white, BlendMode.modulate)
                      : const ColorFilter.mode(Colors.grey, BlendMode.saturation),
                  child: Image.asset(crop.imageAsset,
                      width: 110, height: 110, fit: BoxFit.cover),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(crop.namePunjabi,
                            style: const TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.darkGreen)),
                        Text(crop.nameEn,
                            style: TextStyle(color: Colors.grey.shade700)),
                        if (!crop.enabled)
                          const Text('ماڈل جلد آ ریہا اے',
                              style: TextStyle(
                                  fontSize: 12, color: Colors.orange)),
                      ]),
                ),
              ),
              if (sel)
                const Padding(
                    padding: EdgeInsets.only(left: 14),
                    child: Icon(Icons.check_circle,
                        color: AppTheme.darkGreen, size: 30)),
            ]),
          ),
        ),
      ),
    );
  }
}
