import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "router/app_router.dart";
import "theme/app_theme.dart";

/// Root widget. The editor and feature modules are kept isolated from
/// backend-specific implementation so they can evolve independently.
class PulseApp extends ConsumerWidget {
  const PulseApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: "Pulse Artwork Studio",
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
