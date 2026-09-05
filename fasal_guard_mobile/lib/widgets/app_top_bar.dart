import 'package:flutter/material.dart';

import '../config/app_theme.dart';

/// App header bar reused from the original chat UI: centered title with
/// the logo and an optional back button.
class AppTopBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final bool showBack;
  final List<Widget> actions;

  const AppTopBar({
    super.key,
    required this.title,
    this.showBack = true,
    this.actions = const [],
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: AppTheme.softCream,
      elevation: 0,
      automaticallyImplyLeading: false,
      titleSpacing: 0,
      title: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            title,
            textDirection: TextDirection.rtl,
            style: const TextStyle(
              color: AppTheme.darkGreen,
              fontSize: 21,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(width: 10),
          Image.asset(
            'assets/images/logo.png',
            width: 42,
            height: 42,
            fit: BoxFit.contain,
          ),
        ],
      ),
      centerTitle: true,
      leading: showBack
          ? IconButton(
              onPressed: () => Navigator.maybePop(context),
              splashRadius: 22,
              icon: const Icon(
                Icons.arrow_back_ios_new_rounded,
                color: AppTheme.darkGreen,
                size: 23,
              ),
            )
          : null,
      actions: actions,
    );
  }
}
