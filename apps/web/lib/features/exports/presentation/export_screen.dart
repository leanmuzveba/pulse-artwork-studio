import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:url_launcher/url_launcher.dart";

import "../../../app/theme/app_colors.dart";
import "../../../app/widgets/common_widgets.dart";
import "../../../core/models/export_job.dart";
import "../../artworks/application/artwork_controllers.dart";
import "../application/export_run_controller.dart";

class ExportScreen extends ConsumerStatefulWidget {
  const ExportScreen(
      {required this.projectId, required this.artworkId, super.key});
  final String projectId;
  final String artworkId;

  @override
  ConsumerState<ExportScreen> createState() => _ExportScreenState();
}

class _ExportScreenState extends ConsumerState<ExportScreen> {
  ExportFormat _format = ExportFormat.png;
  int _dpi = 300;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(workspaceContextProvider.notifier).state = WorkspaceRef(
        projectId: widget.projectId,
        artworkId: widget.artworkId,
        projectName:
            ref.read(workspaceContextProvider)?.projectName ?? "Project",
      );
    });
  }

  Future<void> _startExport() async {
    ref.read(exportRunControllerProvider.notifier).reset();
    final job = await ref.read(exportRunControllerProvider.notifier).run(
          projectId: widget.projectId,
          artworkId: widget.artworkId,
          format: _format,
          parameters: _format == ExportFormat.svg ? const {} : {"dpi": _dpi},
        );
    if (job.status == ExportStatus.ready && job.downloadUrl != null) {
      await launchUrl(Uri.parse(job.downloadUrl!));
    }
  }

  @override
  Widget build(BuildContext context) {
    final artworkAsync = ref.watch(
      artworkDetailProvider(
          (projectId: widget.projectId, artworkId: widget.artworkId)),
    );
    final exportState = ref.watch(exportRunControllerProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  "Finalize & Export",
                  style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                      color: AppColors.textPrimary),
                ),
              ),
              TextButton.icon(
                onPressed: () => context.goNamed(
                  "editor",
                  pathParameters: {
                    "projectId": widget.projectId,
                    "artworkId": widget.artworkId
                  },
                ),
                icon: const Icon(Icons.arrow_back, size: 16),
                label: const Text("Back to Editor"),
              ),
            ],
          ),
          const SizedBox(height: 32),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: AspectRatio(
                      aspectRatio: 1,
                      child: artworkAsync.when(
                        loading: () => const LoadingPanel(),
                        error: (error, _) => ErrorPanel(message: "$error"),
                        data: (artwork) =>
                            artwork.downloadUrl != null && !artwork.isSvg
                                ? Image.network(artwork.downloadUrl!,
                                    fit: BoxFit.contain)
                                : Container(
                                    color: AppColors.surfaceRaised,
                                    child: const Icon(Icons.image,
                                        color: AppColors.textMuted, size: 48),
                                  ),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 32),
              Expanded(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          "Export Settings",
                          style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: AppColors.textPrimary),
                        ),
                        const SizedBox(height: 20),
                        const Text("FORMAT",
                            style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: AppColors.textMuted,
                                letterSpacing: 0.6)),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            for (final format in ExportFormat.values)
                              Expanded(
                                child: Padding(
                                  padding: const EdgeInsets.only(right: 8),
                                  child: _FormatButton(
                                    format: format,
                                    selected: _format == format,
                                    onTap: () =>
                                        setState(() => _format = format),
                                  ),
                                ),
                              ),
                          ],
                        ),
                        if (_format != ExportFormat.svg) ...[
                          const SizedBox(height: 20),
                          const Text("OUTPUT RESOLUTION",
                              style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.textMuted,
                                  letterSpacing: 0.6)),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: _DpiOption(
                                  label: "Standard Print",
                                  dpi: 300,
                                  selected: _dpi == 300,
                                  onTap: () => setState(() => _dpi = 300),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: _DpiOption(
                                  label: "Fine Art",
                                  dpi: 600,
                                  selected: _dpi == 600,
                                  onTap: () => setState(() => _dpi = 600),
                                ),
                              ),
                            ],
                          ),
                        ],
                        const SizedBox(height: 24),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed:
                                exportState.isLoading ? null : _startExport,
                            icon: exportState.isLoading
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: AppColors.onAccent),
                                  )
                                : const Icon(Icons.download_rounded, size: 18),
                            label: Text(exportState.isLoading
                                ? "Exporting..."
                                : "Export & Download"),
                          ),
                        ),
                        exportState.when(
                          loading: () => const SizedBox.shrink(),
                          error: (error, _) => Padding(
                            padding: const EdgeInsets.only(top: 12),
                            child: Text("$error",
                                style: const TextStyle(
                                    color: AppColors.critical, fontSize: 12)),
                          ),
                          data: (job) {
                            if (job == null ||
                                job.status != ExportStatus.ready) {
                              return const SizedBox.shrink();
                            }
                            return Padding(
                              padding: const EdgeInsets.only(top: 12),
                              child: Row(
                                children: [
                                  const Icon(Icons.check_circle,
                                      color: AppColors.success, size: 16),
                                  const SizedBox(width: 8),
                                  const Expanded(
                                    child: Text(
                                      "Ready — opened in a new tab.",
                                      style: TextStyle(
                                          color: AppColors.success,
                                          fontSize: 12),
                                    ),
                                  ),
                                  if (job.downloadUrl != null)
                                    TextButton(
                                      onPressed: () => launchUrl(
                                          Uri.parse(job.downloadUrl!)),
                                      child: const Text("Open again"),
                                    ),
                                ],
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _FormatButton extends StatelessWidget {
  const _FormatButton(
      {required this.format, required this.selected, required this.onTap});
  final ExportFormat format;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? AppColors.pulseYellow : Colors.black26,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
              color: selected ? AppColors.pulseYellow : Colors.white10),
        ),
        child: Text(
          format.label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: selected ? AppColors.onAccent : AppColors.textMuted,
          ),
        ),
      ),
    );
  }
}

class _DpiOption extends StatelessWidget {
  const _DpiOption(
      {required this.label,
      required this.dpi,
      required this.selected,
      required this.onTap});
  final String label;
  final int dpi;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.black26,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
              color: selected
                  ? AppColors.pulseYellow.withValues(alpha: 0.6)
                  : Colors.white10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label,
                style: TextStyle(
                    fontSize: 10,
                    color: selected
                        ? AppColors.pulseYellow
                        : AppColors.textMuted)),
            Text("$dpi DPI",
                style: const TextStyle(
                    fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
          ],
        ),
      ),
    );
  }
}
