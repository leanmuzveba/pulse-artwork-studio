import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "app/app.dart";
import "core/storage/token_storage.dart";

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final tokenStorage = await TokenStorage.create();
  runApp(
    ProviderScope(
      overrides: [tokenStorageProvider.overrideWithValue(tokenStorage)],
      child: const PulseApp(),
    ),
  );
}
