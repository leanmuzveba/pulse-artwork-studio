import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:pulse_artwork_studio/app/app.dart";
import "package:pulse_artwork_studio/core/storage/token_storage.dart";
import "package:shared_preferences/shared_preferences.dart";

void main() {
  testWidgets("Unauthenticated app boots to the sign-in screen",
      (tester) async {
    SharedPreferences.setMockInitialValues({});
    final tokenStorage = await TokenStorage.create();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [tokenStorageProvider.overrideWithValue(tokenStorage)],
        child: const PulseApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("Sign in"), findsWidgets);
  });
}
