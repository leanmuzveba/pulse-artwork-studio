import "package:file_picker/file_picker.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../app/theme/app_colors.dart";
import "../../../app/widgets/common_widgets.dart";
import "../../../core/api/api_exception.dart";
import "../../../core/models/artwork.dart";
import "../../artworks/application/artwork_controllers.dart";
import "../../artworks/data/artwork_repository.dart";
import "../data/project_repository.dart";

const _allowedUploadExtensions = ["png", "jpg", "jpeg", "webp"];

/// A project's artworks. Selecting one opens it in the workspace (Editor);
/// projects can hold multiple artworks, so this sits between Dashboard and
/// the single-artwork Editor/Inspector/DTF/Export screens.
class ProjectDetailScreen extends ConsumerStatefulWidget {
  const ProjectDetailScreen({required this.projectId, super.key});
  final String projectId;

  @override
  ConsumerState<ProjectDetailScreen> createState() =>
      _ProjectDetailScreenState();
}

class _ProjectDetailScreenState extends ConsumerState<ProjectDetailScreen> {
  bool _uploading = false;
  String? _error;

  Future<void> _uploadMore() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: _allowedUploadExtensions,
      withData: true,
    );
    final file = result?.files.singleOrNull;
    if (file == null || file.bytes == null) return;

    setState(() {
      _uploading = true;
      _error = null;
    });
    try {
      final repo = ref.read(artworkRepositoryProvider);
      final extension = (file.extension ?? "png").toLowerCase();
      const mimeByExtension = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
      };
      final ticket = await repo.requestUploadUrl(
        projectId: widget.projectId,
        filename: file.name,
        contentType: mimeByExtension[extension] ?? "image/png",
        sizeBytes: file.bytes!.length,
      );
      await repo.uploadBytes(
        uploadUrl: ticket.uploadUrl,
        bytes: file.bytes!,
        headers: ticket.requiredHeaders,
      );
      await repo.confirm(
          projectId: widget.projectId, artworkId: ticket.artworkId);
      ref.invalidate(projectArtworksProvider(widget.projectId));
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final projectAsync = ref.watch(_projectProvider(widget.projectId));
    final artworksAsync = ref.watch(projectArtworksProvider(widget.projectId));

    return SingleChildScrollView(
      padding: const EdgeInsets.all(40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(
                onPressed: () => context.goNamed("dashboard"),
                icon: const Icon(Icons.arrow_back, color: AppColors.textMuted),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  projectAsync.valueOrNull?.name ?? "Project",
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              FilledButton.icon(
                onPressed: _uploading ? null : _uploadMore,
                icon: _uploading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: AppColors.onAccent),
                      )
                    : const Icon(Icons.add, size: 18),
                label: const Text("Upload Artwork"),
              ),
            ],
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppColors.critical)),
          ],
          const SizedBox(height: 32),
          artworksAsync.when(
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: 60),
              child: LoadingPanel(),
            ),
            error: (error, stackTrace) => ErrorPanel(
              message: "Couldn't load artworks. $error",
              onRetry: () =>
                  ref.invalidate(projectArtworksProvider(widget.projectId)),
            ),
            data: (artworks) {
              if (artworks.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 60),
                  child: Center(
                    child: Text(
                      "No artworks uploaded to this project yet.",
                      style: TextStyle(color: AppColors.textMuted),
                    ),
                  ),
                );
              }
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: artworks.length,
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 4,
                  mainAxisSpacing: 20,
                  crossAxisSpacing: 20,
                  childAspectRatio: 0.85,
                ),
                itemBuilder: (context, index) => _ArtworkCard(
                  artwork: artworks[index],
                  projectId: widget.projectId,
                  projectName: projectAsync.valueOrNull?.name ?? "Project",
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

final _projectProvider =
    FutureProvider.family.autoDispose((ref, String projectId) {
  return ref.watch(projectRepositoryProvider).get(projectId);
});

class _ArtworkCard extends ConsumerWidget {
  const _ArtworkCard(
      {required this.artwork,
      required this.projectId,
      required this.projectName});
  final Artwork artwork;
  final String projectId;
  final String projectName;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isReady = artwork.status == ArtworkStatus.ready;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: isReady
            ? () {
                ref.read(workspaceContextProvider.notifier).state =
                    WorkspaceRef(
                  projectId: projectId,
                  artworkId: artwork.id,
                  projectName: projectName,
                );
                context.goNamed(
                  "editor",
                  pathParameters: {
                    "projectId": projectId,
                    "artworkId": artwork.id
                  },
                );
              }
            : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Container(
                color: AppColors.surfaceRaised,
                child: Center(
                  child: Icon(
                    artwork.kind == ArtworkKind.derived
                        ? Icons.auto_awesome
                        : Icons.image_outlined,
                    color: AppColors.textMuted,
                    size: 32,
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    artwork.originalFilename ?? "Untitled",
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                        fontSize: 13),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    isReady ? artwork.dimensionsLabel : artwork.status.name,
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
