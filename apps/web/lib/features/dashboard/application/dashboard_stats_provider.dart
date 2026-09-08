import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/models/artwork.dart";
import "../../artworks/data/artwork_repository.dart";
import "../../projects/application/projects_controller.dart";

class DashboardStats {
  const DashboardStats(
      {required this.totalProjects, required this.readyArtworks});
  final int totalProjects;
  final int readyArtworks;
}

/// Aggregates real counts across the user's projects — no fabricated numbers.
final dashboardStatsProvider =
    FutureProvider.autoDispose<DashboardStats>((ref) async {
  final projects = await ref.watch(projectsProvider.future);
  final repo = ref.watch(artworkRepositoryProvider);
  final artworkLists = await Future.wait(projects.map((p) => repo.list(p.id)));
  final readyArtworks = artworkLists
      .expand((list) => list)
      .where((a) => a.status == ArtworkStatus.ready)
      .length;
  return DashboardStats(
      totalProjects: projects.length, readyArtworks: readyArtworks);
});
