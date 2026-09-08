import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/models/processing_job.dart";
import "../data/processing_repository.dart";

/// Creates a processing job and polls it to a terminal state. Screens key
/// this provider by an arbitrary, stable tag (e.g. "editor-enhance") so
/// unrelated jobs on the same screen don't share state.
final processingRunControllerProvider = AsyncNotifierProvider.autoDispose
    .family<ProcessingRunController, ProcessingJob?, String>(
        ProcessingRunController.new);

class ProcessingRunController
    extends AutoDisposeFamilyAsyncNotifier<ProcessingJob?, String> {
  @override
  Future<ProcessingJob?> build(String arg) async => null;

  Future<ProcessingJob> run({
    required String projectId,
    required String artworkId,
    required JobOperation operation,
    Map<String, dynamic> parameters = const {},
  }) async {
    state = const AsyncLoading();
    final repo = ref.read(processingRepositoryProvider);
    try {
      var job = await repo.createJob(
        projectId: projectId,
        artworkId: artworkId,
        operation: operation,
        parameters: parameters,
      );
      state = AsyncData(job);

      while (!job.status.isTerminal) {
        await Future<void>.delayed(const Duration(milliseconds: 1200));
        job = await repo.getJob(job.id);
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
