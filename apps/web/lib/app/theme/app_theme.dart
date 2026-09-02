import "package:flutter/material.dart";

import "app_colors.dart";

/// Light and dark themes built on the yellow / grey / black brand palette.
abstract final class AppTheme {
  static ThemeData get light {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.pulseYellow,
      brightness: Brightness.light,
    ).copyWith(
      primary: AppColors.pulseYellow,
      onPrimary: AppColors.onAccent,
      surface: AppColors.paper,
      onSurface: AppColors.ink,
    );
    return _base(scheme);
  }

  static ThemeData get dark {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.pulseYellowBright,
      brightness: Brightness.dark,
    ).copyWith(
      primary: AppColors.pulseYellowBright,
      onPrimary: AppColors.onAccent,
      surface: AppColors.surfaceDark,
      onSurface: const Color(0xFFF5F2E9),
    );
    return _base(scheme).copyWith(
      scaffoldBackgroundColor: AppColors.bgDark,
    );
  }

  static ThemeData _base(ColorScheme scheme) {
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: scheme.surface,
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        centerTitle: false,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
    );
  }
}
