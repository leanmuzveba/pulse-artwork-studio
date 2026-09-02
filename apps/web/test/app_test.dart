import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:pulse_artwork_studio/app/app.dart";

void main() {
  testWidgets("App boots to the dashboard", (tester) async {
    await tester.pumpWidget(const ProviderScope(child: PulseApp()));
    await tester.pumpAndSettle();

    expect(find.text("Pulse Artwork Studio"), findsOneWidget);
    expect(find.text("Open editor"), findsOneWidget);
  });
}
