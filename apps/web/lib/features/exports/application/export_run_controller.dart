import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/models/export_job.dart";
import "../data/export_repository.dart";

final exportRunControllerProvider =
    AsyncNotifierProvider.autoDispose<ExportRunController, ExportJob?>(
        ExportRunController.new);

class ExportRunController extends AutoDisposeAsyncNotifier<ExportJob?> {
  @override
  Future<ExportJob?> build() async => null;

  static const _terminal = {ExportStatus.ready, ExportStatus.failed};

  Future<ExportJob> run({
    required String projectId,
    required String artworkId,
    required ExportFormat format,
    Map<String, dynamic> parameters = const {},
  }) async {
    state = const AsyncLoading();
    final repo = ref.read(exportRepositoryProvider);
    try {
      var job = await repo.create(
        projectId: projectId,
        artworkId: artworkId,
        format: format,
        parameters: parameters,
      );
      state = AsyncData(job);

      while (!_terminal.contains(job.status)) {
        await Future<void>.delayed(const Duration(milliseconds: 1200));
        job = await repo.get(job.id);
        state = AsyncData(job);
      }
      return job;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }

  void reset() => state = const AsyncData(null);
}
