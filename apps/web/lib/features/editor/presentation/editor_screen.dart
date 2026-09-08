import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:url_launcher/url_launcher.dart";

import "../../../app/theme/app_colors.dart";
import "../../../app/widgets/common_widgets.dart";
import "../../../core/models/artwork.dart";
import "../../../core/models/processing_job.dart";
import "../../artworks/application/artwork_controllers.dart";
import "../../processing/application/processing_run_controller.dart";

class EditorScreen extends ConsumerStatefulWidget {
  const EditorScreen(
      {required this.projectId, required this.artworkId, super.key});
  final String projectId;
  final String artworkId;

  @override
  ConsumerState<EditorScreen> createState() => _EditorScreenState();
}

class _EditorScreenState extends ConsumerState<EditorScreen> {
  static const _tag = "editor-tool";
  JobOperation? _running;

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

  Future<void> _runTool(JobOperation operation) async {
    setState(() => _running = operation);
    try {
      final job = await ref
          .read(processingRunControllerProvider(_tag).notifier)
          .run(
              projectId: widget.projectId,
              artworkId: widget.artworkId,
              operation: operation);
      if (!mounted) return;
      if (job.status == JobStatus.completed) {
        ref.invalidate(artworkDetailProvider(
            (projectId: widget.projectId, artworkId: widget.artworkId)));
        final resultId = job.resultArtworkId;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text("Done."),
            action: (resultId != null && resultId != widget.artworkId)
                ? SnackBarAction(
                    label: "View result",
                    onPressed: () {
                      ref.read(workspaceContextProvider.notifier).state =
                          WorkspaceRef(
                        projectId: widget.projectId,
                        artworkId: resultId,
                        projectName:
                            ref.read(workspaceContextProvider)?.projectName ??
                                "Project",
                      );
                      context.goNamed(
                        "editor",
                        pathParameters: {
                          "projectId": widget.projectId,
                          "artworkId": resultId
                        },
                      );
                    },
                  )
                : null,
          ),
        );
      } else if (job.status == JobStatus.failed && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(job.errorMessage ?? "That operation failed.")),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text("$error")));
      }
    } finally {
      if (mounted) setState(() => _running = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final artworkAsync = ref.watch(
      artworkDetailProvider(
          (projectId: widget.projectId, artworkId: widget.artworkId)),
    );

    return Column(
      children: [
        _TopBar(
          onExport: () => context.goNamed(
            "export",
            pathParameters: {
              "projectId": widget.projectId,
              "artworkId": widget.artworkId
            },
          ),
        ),
        Expanded(
          child: Row(
            children: [
              _ToolRail(running: _running, onSelect: _runTool),
              Expanded(
                child: Container(
                  color: AppColors.canvasDark,
                  child: artworkAsync.when(
                    loading: () => const LoadingPanel(),
                    error: (error, stackTrace) => ErrorPanel(
                      message: "Couldn't load this artwork. $error",
                      onRetry: () => ref.invalidate(
                        artworkDetailProvider(
                          (
                            projectId: widget.projectId,
                            artworkId: widget.artworkId
                          ),
                        ),
                      ),
                    ),
                    data: (artwork) =>
                        _Canvas(artwork: artwork, busy: _running != null),
                  ),
                ),
              ),
              _PropertiesPanel(
                  artworkAsync: artworkAsync,
                  onVectorize: () => _runTool(JobOperation.vectorize)),
            ],
          ),
        ),
      ],
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({required this.onExport});
  final VoidCallback onExport;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: const BoxDecoration(
        color: AppColors.charcoalLight,
        border: Border(bottom: BorderSide(color: Colors.white10)),
      ),
      child: Row(
        children: [
          for (final label in const [
            "File",
            "Edit",
            "AI Tools",
            "Effects",
            "DTF",
            "View"
          ])
            Padding(
              padding: const EdgeInsets.only(right: 24),
              child: Text(label,
                  style: const TextStyle(
                      color: AppColors.textSecondary, fontSize: 13)),
            ),
          const Spacer(),
          FilledButton(onPressed: onExport, child: const Text("Export")),
        ],
      ),
    );
  }
}

class _ToolRail extends StatelessWidget {
  const _ToolRail({required this.running, required this.onSelect});
  final JobOperation? running;
  final void Function(JobOperation) onSelect;

  @override
  Widget build(BuildContext context) {
    final tools = <(JobOperation, IconData, String)>[
      (JobOperation.enhance, Icons.auto_fix_high_rounded, "AI Enhance"),
      (JobOperation.upscale, Icons.open_in_full_rounded, "Upscale 2x"),
      (
        JobOperation.backgroundRemoval,
        Icons.layers_clear_rounded,
        "Remove Background",
      ),
      (JobOperation.vectorize, Icons.gesture_rounded, "Vectorize"),
      (JobOperation.halftone, Icons.grain_rounded, "Halftone"),
      (JobOperation.embroidery, Icons.texture_rounded, "Embroidery Preview"),
    ];
    return Container(
      width: 64,
      color: AppColors.charcoalLight,
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Column(
        children: [
          for (final (operation, icon, tooltip) in tools)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Tooltip(
                message: tooltip,
                child: InkWell(
                  borderRadius: BorderRadius.circular(10),
                  onTap: running == null ? () => onSelect(operation) : null,
                  child: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: running == operation
                          ? AppColors.pulseYellow
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: running == operation
                        ? const Padding(
                            padding: EdgeInsets.all(10),
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: AppColors.onAccent,
                            ),
                          )
                        : Icon(
                            icon,
                            color: running == null
                                ? AppColors.textMuted
                                : Colors.white24,
                            size: 20,
                          ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _Canvas extends StatelessWidget {
  const _Canvas({required this.artwork, required this.busy});
  final Artwork artwork;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 560, maxHeight: 560),
            margin: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              color: AppColors.charcoalLight,
              border: Border.all(color: Colors.white10),
              boxShadow: const [
                BoxShadow(color: Colors.black45, blurRadius: 24)
              ],
            ),
            child: artwork.isSvg
                ? _SvgFallback(artwork: artwork)
                : (artwork.downloadUrl != null
                    ? Image.network(artwork.downloadUrl!, fit: BoxFit.contain)
                    : const Center(
                        child: Icon(Icons.image_not_supported,
                            color: AppColors.textMuted),
                      )),
          ),
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: Container(
            height: 36,
            color: AppColors.charcoalLight,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Text(artwork.dimensionsLabel, style: _statusStyle),
                const SizedBox(width: 20),
                Text(artwork.dpiLabel, style: _statusStyle),
                const Spacer(),
                if (busy) ...[
                  const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: AppColors.pulseYellow),
                  ),
                  const SizedBox(width: 8),
                  const Text("Processing...", style: _statusStyle),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  static const _statusStyle = TextStyle(
    fontSize: 10,
    fontWeight: FontWeight.w600,
    color: AppColors.textMuted,
    letterSpacing: 0.4,
  );
}

class _SvgFallback extends StatelessWidget {
  const _SvgFallback({required this.artwork});
  final Artwork artwork;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.polyline, color: AppColors.pulseYellow, size: 40),
          const SizedBox(height: 12),
          const Text("Vector (SVG) result",
              style: TextStyle(color: AppColors.textSecondary)),
          if (artwork.downloadUrl != null) ...[
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => launchUrl(Uri.parse(artwork.downloadUrl!)),
              child: const Text("Open in a new tab"),
            ),
          ],
        ],
      ),
    );
  }
}

class _PropertiesPanel extends StatelessWidget {
  const _PropertiesPanel(
      {required this.artworkAsync, required this.onVectorize});
  final AsyncValue<Artwork> artworkAsync;
  final VoidCallback onVectorize;

  @override
  Widget build(BuildContext context) {
    final artwork = artworkAsync.valueOrNull;
    return Container(
      width: 300,
      color: AppColors.charcoalLight,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              "PROPERTIES",
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w900,
                color: AppColors.textPrimary,
                letterSpacing: 0.6,
              ),
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                const Text(
                  "PRINT INFO",
                  style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textMuted,
                      letterSpacing: 0.6),
                ),
                const SizedBox(height: 12),
                _InfoRow(
                    label: "Dimensions",
                    value: artwork?.dimensionsLabel ?? "—"),
                _InfoRow(label: "Resolution", value: artwork?.dpiLabel ?? "—"),
                _InfoRow(
                  label: "File Size",
                  value: artwork?.sizeBytes != null
                      ? "${(artwork!.sizeBytes! / 1024 / 1024).toStringAsFixed(2)} MB"
                      : "—",
                ),
                _InfoRow(label: "Status", value: artwork?.status.name ?? "—"),
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.pulseYellow.withValues(alpha: 0.05),
                    border: Border.all(
                        color: AppColors.pulseYellow.withValues(alpha: 0.2)),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(
                            Icons.auto_awesome_rounded,
                            color: AppColors.pulseYellow,
                            size: 14,
                          ),
                          SizedBox(width: 6),
                          Text(
                            "AI ASSISTANT",
                            style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: AppColors.pulseYellow,
                                letterSpacing: 0.6),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        "Vector conversion can improve edge quality for screen and DTF printing.",
                        style: TextStyle(
                            fontSize: 12,
                            color: AppColors.textSecondary,
                            height: 1.4),
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: onVectorize,
                          style: FilledButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            textStyle: const TextStyle(fontSize: 11),
                          ),
                          child: const Text("RUN VECTORIZER"),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
          Text(value,
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary)),
        ],
      ),
    );
  }
}
