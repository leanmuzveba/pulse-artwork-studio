import "package:flutter/material.dart";
import "package:google_fonts/google_fonts.dart";

import "app_colors.dart";

/// Dark, charcoal/yellow theme matching the Pulse design system.
/// The product is designed dark-first (production workspace, not a document
/// app), so there is a single theme rather than light/dark variants.
abstract final class AppTheme {
  static ThemeData get dark {
    final base = GoogleFonts.interTextTheme(ThemeData.dark().textTheme);
    final scheme = const ColorScheme.dark().copyWith(
      primary: AppColors.pulseYellow,
      onPrimary: AppColors.onAccent,
      secondary: AppColors.pulseGold,
      onSecondary: AppColors.onAccent,
      surface: AppColors.charcoalLight,
      onSurface: AppColors.textPrimary,
      error: AppColors.critical,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.charcoalDark,
      textTheme: base.apply(
        bodyColor: AppColors.textSecondary,
        displayColor: AppColors.textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.charcoalLight,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        centerTitle: false,
      ),
      dividerColor: AppColors.divider,
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.pulseYellow,
          foregroundColor: AppColors.onAccent,
          textStyle: const TextStyle(fontWeight: FontWeight.bold),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.textPrimary,
          side: const BorderSide(color: Colors.white24),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: AppColors.pulseYellow),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.black.withValues(alpha: 0.3),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Colors.white10),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Colors.white10),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.pulseYellow),
        ),
        hintStyle: const TextStyle(color: AppColors.textMuted),
        labelStyle: const TextStyle(color: AppColors.textMuted),
      ),
      cardTheme: CardThemeData(
        color: AppColors.charcoalLight,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Colors.white10),
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? AppColors.pulseYellow
              : Colors.transparent,
        ),
        checkColor: const WidgetStatePropertyAll(AppColors.onAccent),
      ),
      sliderTheme: const SliderThemeData(
        activeTrackColor: AppColors.pulseYellow,
        thumbColor: AppColors.pulseYellow,
        inactiveTrackColor: Colors.white24,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.surfaceRaised,
        contentTextStyle: const TextStyle(color: AppColors.textPrimary),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }
}
