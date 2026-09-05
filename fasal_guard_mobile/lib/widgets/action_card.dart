import 'package:flutter/material.dart';

import '../config/app_theme.dart';

/// Farmer-facing action card reused from the original chat landing page.
/// Large tap area + icon + title + description lines (RTL Shahmukhi).
class ActionCard extends StatefulWidget {
  final IconData icon;
  final String title;
  final List<String> lines;
  final double iconSize;
  final bool enabled;
  final VoidCallback onTap;

  const ActionCard({
    super.key,
    required this.icon,
    required this.title,
    required this.lines,
    required this.onTap,
    this.iconSize = 51,
    this.enabled = true,
  });

  @override
  State<ActionCard> createState() => _ActionCardState();
}

class _ActionCardState extends State<ActionCard> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return AnimatedScale(
      scale: _pressed ? 0.98 : 1,
      duration: const Duration(milliseconds: 130),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: widget.enabled ? widget.onTap : null,
          onHighlightChanged: (value) {
            setState(() {
              _pressed = value;
            });
          },
          borderRadius: BorderRadius.circular(27),
          child: Ink(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(
              horizontal: 25,
              vertical: 28,
            ),
            decoration: BoxDecoration(
              color: widget.enabled
                  ? AppTheme.cardWhite
                  : const Color(0xFFF1F1EA),
              borderRadius: BorderRadius.circular(27),
              border: Border.all(color: AppTheme.borderSoft),
              boxShadow: const [
                BoxShadow(
                  color: Color.fromRGBO(45, 55, 38, 0.08),
                  blurRadius: 20,
                  offset: Offset(0, 8),
                ),
              ],
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Container(
                  width: 105,
                  height: 105,
                  decoration: BoxDecoration(
                    color: AppTheme.lightGreenFill,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    widget.icon,
                    color: widget.enabled
                        ? AppTheme.deepGreen
                        : Colors.grey.shade500,
                    size: widget.iconSize,
                  ),
                ),
                const SizedBox(width: 24),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        widget.title,
                        textDirection: TextDirection.rtl,
                        textAlign: TextAlign.right,
                        style: TextStyle(
                          color: widget.enabled
                              ? const Color(0xFF075E29)
                              : Colors.grey.shade600,
                          fontSize: 23,
                          fontWeight: FontWeight.w800,
                          height: 1.25,
                        ),
                      ),
                      const SizedBox(height: 11),
                      for (final line in widget.lines)
                        SizedBox(
                          width: double.infinity,
                          child: Text(
                            line,
                            textDirection: TextDirection.rtl,
                            textAlign: TextAlign.right,
                            style: TextStyle(
                              color: widget.enabled
                                  ? const Color(0xFF17251B)
                                  : Colors.grey.shade500,
                              fontSize: 16,
                              height: 1.48,
                              fontWeight: FontWeight.w500,
                            ),
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
}
