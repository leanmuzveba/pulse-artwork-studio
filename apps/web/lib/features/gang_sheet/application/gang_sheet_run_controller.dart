import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/models/gang_sheet.dart";
import "../data/gang_sheet_repository.dart";

final gangSheetRunControllerProvider =
    AsyncNotifierProvider.autoDispose<GangSheetRunController, GangSheet?>(
        GangSheetRunController.new);

class GangSheetRunController extends AutoDisposeAsyncNotifier<GangSheet?> {
  @override
  Future<GangSheet?> build() async => null;

  Future<GangSheet> run({
    required String projectId,
    required int sheetWidthMm,
    required int spacingMm,
    required int dpi,
    required List<GangSheetItem> items,
  }) async {
    state = const AsyncLoading();
    final repo = ref.read(gangSheetRepositoryProvider);
    try {
      var gangSheet = await repo.create(
        projectId: projectId,
        sheetWidthMm: sheetWidthMm,
        spacingMm: spacingMm,
        dpi: dpi,
        items: items,
      );
      state = AsyncData(gangSheet);

      while (!gangSheet.status.isTerminal) {
        await Future<void>.delayed(const Duration(milliseconds: 1200));
        gangSheet = await repo.get(gangSheet.id);
        state = AsyncData(gangSheet);
      }
      return gangSheet;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }

  void reset() => state = const AsyncData(null);
}
