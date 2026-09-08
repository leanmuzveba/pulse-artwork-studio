import "dart:async";

import "package:file_picker/file_picker.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../app/theme/app_colors.dart";
import "../../../core/api/api_exception.dart";
import "../../../core/models/processing_job.dart";
import "../../artworks/application/artwork_controllers.dart";
import "../../artworks/data/artwork_repository.dart";
import "../../processing/data/processing_repository.dart";
import "../application/projects_controller.dart";

const _allowedExtensions = ["png", "jpg", "jpeg", "webp"];
const _mimeByExtension = {
  "png": "image/png",
  "jpg": "image/jpeg",
  "jpeg": "image/jpeg",
  "webp": "image/webp",
};

class NewProjectScreen extends ConsumerStatefulWidget {
  const NewProjectScreen({super.key});

  @override
  ConsumerState<NewProjectScreen> createState() => _NewProjectScreenState();
}

class _NewProjectScreenState extends ConsumerState<NewProjectScreen> {
  final _nameController = TextEditingController();
  PlatformFile? _pickedFile;
  bool _autoInspect = true;
  bool _submitting = false;
  String? _error;
  String _stage = "";

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: _allowedExtensions,
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    setState(() {
      _pickedFile = result.files.single;
      if (_nameController.text.trim().isEmpty) {
        final filename = _pickedFile!.name;
        final dot = filename.lastIndexOf(".");
        _nameController.text = dot > 0 ? filename.substring(0, dot) : filename;
      }
    });
  }

  Future<void> _submit() async {
    final file = _pickedFile;
    final name = _nameController.text.trim();
    if (file == null || file.bytes == null) {
      setState(() => _error = "Choose an artwork file first.");
      return;
    }
    if (name.isEmpty) {
      setState(() => _error = "Give the project a name.");
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      setState(() => _stage = "Creating project...");
      final project =
          await ref.read(projectsProvider.notifier).createProject(name);

      setState(() => _stage = "Requesting upload slot...");
      final extension = (file.extension ?? "png").toLowerCase();
      final contentType = _mimeByExtension[extension] ?? "image/png";
      final artworkRepo = ref.read(artworkRepositoryProvider);
      final ticket = await artworkRepo.requestUploadUrl(
        projectId: project.id,
        filename: file.name,
        contentType: contentType,
        sizeBytes: file.bytes!.length,
      );

      setState(() => _stage = "Uploading artwork...");
      await artworkRepo.uploadBytes(
        uploadUrl: ticket.uploadUrl,
        bytes: file.bytes!,
        headers: ticket.requiredHeaders,
      );

      setState(() => _stage = "Confirming upload...");
      await artworkRepo.confirm(
          projectId: project.id, artworkId: ticket.artworkId);

      ref.read(workspaceContextProvider.notifier).state = WorkspaceRef(
        projectId: project.id,
        artworkId: ticket.artworkId,
        projectName: project.name,
      );

      if (_autoInspect) {
        setState(() => _stage = "Running AI Inspector...");
        // Fire-and-forget: the Inspector screen itself polls this job to
        // completion, so we only need to kick it off here.
        unawaited(
          ref.read(processingRepositoryProvider).createJob(
                projectId: project.id,
                artworkId: ticket.artworkId,
                operation: JobOperation.dtfCheck,
              ),
        );
        if (mounted) {
          context.goNamed(
            "inspector",
            pathParameters: {
              "projectId": project.id,
              "artworkId": ticket.artworkId
            },
          );
        }
      } else if (mounted) {
        context.goNamed(
          "editor",
          pathParameters: {
            "projectId": project.id,
            "artworkId": ticket.artworkId
          },
        );
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(40),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(48),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Container(
                    width: 84,
                    height: 84,
                    decoration: BoxDecoration(
                      color: AppColors.pulseYellow.withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.cloud_upload_rounded,
                      color: AppColors.pulseYellow,
                      size: 40,
                    ),
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    "Start New Project",
                    style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    "Upload your artwork to begin the AI preparation flow.",
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.textMuted),
                  ),
                  const SizedBox(height: 32),
                  InkWell(
                    onTap: _submitting ? null : _pickFile,
                    borderRadius: BorderRadius.circular(16),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(32),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: _pickedFile != null
                              ? AppColors.pulseYellow
                              : Colors.white24,
                        ),
                      ),
                      child: Column(
                        children: [
                          Icon(
                            _pickedFile != null
                                ? Icons.image_rounded
                                : Icons.upload_rounded,
                            color: _pickedFile != null
                                ? AppColors.pulseYellow
                                : AppColors.textMuted,
                            size: 28,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _pickedFile?.name ??
                                "Click to choose a PNG, JPG, or WEBP file",
                            textAlign: TextAlign.center,
                            style:
                                const TextStyle(color: AppColors.textSecondary),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            "Maximum file size: 100 MB",
                            style: TextStyle(
                                fontSize: 11, color: AppColors.textMuted),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _nameController,
                    style: const TextStyle(color: AppColors.textPrimary),
                    decoration: const InputDecoration(
                      labelText: "Project Name",
                      hintText: "e.g. Vintage Rock Tee - Back Print",
                    ),
                  ),
                  const SizedBox(height: 12),
                  CheckboxListTile(
                    value: _autoInspect,
                    onChanged: (value) =>
                        setState(() => _autoInspect = value ?? true),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                    title: const Text(
                      "Auto-run AI Artwork Inspector after upload",
                      style: TextStyle(
                          color: AppColors.textSecondary, fontSize: 13),
                    ),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 8),
                    Text(_error!,
                        style: const TextStyle(color: AppColors.critical)),
                  ],
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _submitting ? null : _submit,
                      child: _submitting
                          ? Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: AppColors.onAccent,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Text(_stage),
                              ],
                            )
                          : const Text("Continue to Workspace"),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
