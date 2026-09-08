import "package:flutter/material.dart";

/// Brand palette — yellow / grey / black.
/// Sourced from the "pulsedashboard" HTML prototype (2026-09-06) and
/// `intial_docs/Color Palette _ Yellow _ Grey _ Black.jfif`.
abstract final class AppColors {
  // Core brand accent
  static const Color pulseYellow = Color(0xFFFFEE32);
  static const Color pulseGold = Color(0xFFFFD100);
  static const Color onAccent = Color(0xFF202020);

  // Charcoal surfaces (the app is dark-first, matching the design)
  static const Color charcoalLight = Color(0xFF333533);
  static const Color charcoalDark = Color(0xFF202020);
  static const Color canvasDark = Color(0xFF151515);
  static const Color surfaceRaised = Color(0xFF2A2A2A);
  static const Color black = Color(0xFF000000);

  // Text / greys
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFD6D6D6);
  static const Color textMuted = Color(0xFF8A8A8A);
  static const Color divider = Color(0x0DFFFFFF); // white @ 5%

  // Status
  static const Color success = Color(0xFF10B981); // emerald-500
  static const Color warning = Color(0xFFFB923C); // orange-400
  static const Color critical = Color(0xFFEF4444); // red-500
  static const Color info = Color(0xFF60A5FA); // blue-400
}
