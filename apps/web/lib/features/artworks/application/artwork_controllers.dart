import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/models/artwork.dart";
import "../data/artwork_repository.dart";

/// Identifies the artwork currently open in the workspace (Editor, AI
/// Inspector, DTF Preparation, Export & Finish all key off this). `null`
/// means nothing has been opened yet this session.
class WorkspaceRef {
  const WorkspaceRef(
      {required this.projectId,
      required this.artworkId,
      required this.projectName});
  final String projectId;
  final String artworkId;
  final String projectName;
}

final workspaceContextProvider = StateProvider<WorkspaceRef?>((ref) => null);

/// A project's artworks, newest first.
final projectArtworksProvider =
    FutureProvider.family.autoDispose<List<Artwork>, String>((ref, projectId) {
  return ref.watch(artworkRepositoryProvider).list(projectId);
});

/// A single artwork's live detail (including a signed download URL once ready).
/// `autoDispose` + `keepAlive` isn't used deliberately: callers should
/// `ref.invalidate` this after a processing job completes to refetch.
final artworkDetailProvider = FutureProvider.family
    .autoDispose<Artwork, ({String projectId, String artworkId})>((ref, args) {
  return ref
      .watch(artworkRepositoryProvider)
      .get(projectId: args.projectId, artworkId: args.artworkId);
});
