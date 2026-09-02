import "package:flutter/material.dart";

/// Brand palette — yellow / grey / black.
/// (Reference: intial_docs/"Color Palette _ Yellow _ Grey _ Black".)
abstract final class AppColors {
  // Core brand
  static const Color pulseYellow = Color(0xFFE8A80C); // primary accent (on light)
  static const Color pulseYellowBright = Color(0xFFF5C518); // accent on dark
  static const Color ink = Color(0xFF1A1815); // near-black, warm
  static const Color onAccent = Color(0xFF1A1815);

  // Warm grey scale (biased slightly toward the yellow)
  static const Color grey900 = Color(0xFF201E1A);
  static const Color grey700 = Color(0xFF57544C);
  static const Color grey500 = Color(0xFF8A867B);
  static const Color grey300 = Color(0xFFD3CFC1);
  static const Color grey100 = Color(0xFFF1EFE8);
  static const Color paper = Color(0xFFF7F6F1);
  static const Color surfaceDark = Color(0xFF1E1C17);
  static const Color bgDark = Color(0xFF141310);
}
