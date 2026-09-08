import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/models/project.dart";
import "../data/project_repository.dart";

/// The current user's projects, sorted newest-first by the API.
final projectsProvider =
    AsyncNotifierProvider<ProjectsController, List<Project>>(
  ProjectsController.new,
);

class ProjectsController extends AsyncNotifier<List<Project>> {
  @override
  Future<List<Project>> build() => ref.read(projectRepositoryProvider).list();

  Future<Project> createProject(String name) async {
    final project = await ref.read(projectRepositoryProvider).create(name);
    state = AsyncData([project, ...await future]);
    return project;
  }

  Future<void> refresh() async {
    state = const AsyncLoading<List<Project>>().copyWithPrevious(state);
    state = await AsyncValue.guard(
        () => ref.read(projectRepositoryProvider).list());
  }
}
