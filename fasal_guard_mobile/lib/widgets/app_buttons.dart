import 'package:flutter/material.dart';

import '../config/app_theme.dart';

/// Full-width farmer buttons reused from the original chat UI.
class PrimaryButton extends StatelessWidget {
  final IconData icon;
  final String text;
  final VoidCallback? onTap;

  const PrimaryButton({
    super.key,
    required this.icon,
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 57,
      child: FilledButton.icon(
        onPressed: onTap,
        icon: Icon(icon),
        label: Text(
          text,
          textDirection: TextDirection.rtl,
          style: const TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w800,
          ),
        ),
        style: FilledButton.styleFrom(
          backgroundColor: AppTheme.darkGreen,
          disabledBackgroundColor: Colors.grey.shade300,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(17),
          ),
        ),
      ),
    );
  }
}

class SecondaryButton extends StatelessWidget {
  final IconData icon;
  final String text;
  final VoidCallback? onTap;

  const SecondaryButton({
    super.key,
    required this.icon,
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 55,
      child: OutlinedButton.icon(
        onPressed: onTap,
        icon: Icon(icon),
        label: Text(
          text,
          textDirection: TextDirection.rtl,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        style: OutlinedButton.styleFrom(
          foregroundColor: AppTheme.darkGreen,
          side: const BorderSide(color: Color(0xFFD9DED2)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(17),
          ),
        ),
      ),
    );
  }
}

class DangerButton extends StatelessWidget {
  final IconData icon;
  final String text;
  final VoidCallback? onTap;

  const DangerButton({
    super.key,
    required this.icon,
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 57,
      child: FilledButton.icon(
        onPressed: onTap,
        icon: Icon(icon),
        label: Text(
          text,
          textDirection: TextDirection.rtl,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        style: FilledButton.styleFrom(
          backgroundColor: AppTheme.danger,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(17),
          ),
        ),
      ),
    );
  }
}
