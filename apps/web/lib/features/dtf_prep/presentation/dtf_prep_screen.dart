import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../app/theme/app_colors.dart";
import "../../../app/widgets/common_widgets.dart";
import "../../../core/models/artwork.dart";
import "../../../core/models/processing_job.dart";
import "../../artworks/application/artwork_controllers.dart";
import "../../processing/application/processing_run_controller.dart";

/// DTF sheet placement & print-readiness. Sheet size and choke/dot-width are
/// local preview-only controls — the backend doesn't yet have a place to
/// persist per-sheet layout, so nothing here is saved. The print-check list
/// is real: it's driven by the same `dtf_check` analysis as the AI Inspector.
class DtfPrepScreen extends ConsumerStatefulWidget {
  const DtfPrepScreen(
      {required this.projectId, required this.artworkId, super.key});
  final String projectId;
  final String artworkId;

  @override
  ConsumerState<DtfPrepScreen> createState() => _DtfPrepScreenState();
}

class _DtfPrepScreenState extends ConsumerState<DtfPrepScreen> {
  static const _tag = "dtf-scan";
  double _choke = 0.3;
  double _minDotWidth = 0.5;
  int _viewMode = 0;

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
      ref.read(processingRunControllerProvider(_tag).notifier).run(
          projectId: widget.projectId,
          artworkId: widget.artworkId,
          operation: JobOperation.dtfCheck);
    });
  }

  @override
  Widget build(BuildContext context) {
    final artworkAsync = ref.watch(
      artworkDetailProvider(
          (projectId: widget.projectId, artworkId: widget.artworkId)),
    );
    final scanState = ref.watch(processingRunControllerProvider(_tag));
    final report = scanState.valueOrNull?.resultData != null
        ? DtfCheckReport.fromJson(scanState.valueOrNull!.resultData!)
        : null;

    return Column(
      children: [
        Container(
          height: 60,
          padding: const EdgeInsets.symmetric(horizontal: 24),
          decoration: const BoxDecoration(
            color: AppColors.charcoalLight,
            border: Border(bottom: BorderSide(color: Colors.white10)),
          ),
          child: Row(
            children: [
              const Text(
                "DTF PRINT SETUP",
                style: TextStyle(
                    fontWeight: FontWeight.w900,
                    color: AppColors.textPrimary,
                    letterSpacing: 0.5),
              ),
              const Spacer(),
              FilledButton.icon(
                style: FilledButton.styleFrom(
                    backgroundColor: AppColors.success,
                    foregroundColor: Colors.white),
                onPressed: () => context.goNamed(
                  "export",
                  pathParameters: {
                    "projectId": widget.projectId,
                    "artworkId": widget.artworkId
                  },
                ),
                icon: const Icon(Icons.check, size: 16),
                label: Text(report?.ready == true
                    ? "Print Ready"
                    : "Continue to Export"),
              ),
            ],
          ),
        ),
        Expanded(
          child: Row(
            children: [
              Container(
                width: 300,
                color: AppColors.charcoalLight,
                child: ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    const _SectionLabel("Physical Dimensions"),
                    const SizedBox(height: 8),
                    artworkAsync.when(
                      loading: () => const SizedBox.shrink(),
                      error: (error, stackTrace) => const SizedBox.shrink(),
                      data: (artwork) => _PhysicalDimensions(artwork: artwork),
                    ),
                    const SizedBox(height: 24),
                    const _SectionLabel("Underbase & Choke (preview only)"),
                    const SizedBox(height: 12),
                    _SliderRow(
                      label: "White Underbase (Choke)",
                      value: _choke,
                      max: 2,
                      unit: "mm",
                      onChanged: (v) => setState(() => _choke = v),
                    ),
                    _SliderRow(
                      label: "Min Dot Width",
                      value: _minDotWidth,
                      max: 2,
                      unit: "pt",
                      onChanged: (v) => setState(() => _minDotWidth = v),
                    ),
                    const SizedBox(height: 24),
                    const _SectionLabel("Canvas Actions"),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final label in const [
                          "Mirror Canvas",
                          "Auto Center",
                          "Rotate 90°",
                          "Fit to Sheet"
                        ])
                          Tooltip(
                            message: "Coming soon",
                            child: OutlinedButton(
                              onPressed: null,
                              child: Text(label,
                                  style: const TextStyle(fontSize: 11)),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    const _SectionLabel("Print Check"),
                    const SizedBox(height: 12),
                    _PrintCheckList(scanState: scanState, report: report),
                  ],
                ),
              ),
              Expanded(
                child: Container(
                  color: AppColors.black,
                  child: Stack(
                    children: [
                      Center(
                        child: artworkAsync.when(
                          loading: () => const LoadingPanel(),
                          error: (error, _) => ErrorPanel(message: "$error"),
                          data: (artwork) => Container(
                            width: 280,
                            height: 280,
                            decoration: BoxDecoration(
                              color: const Color(0xFF1A1A1A),
                              border: Border.all(color: AppColors.info),
                            ),
                            child: artwork.downloadUrl != null && !artwork.isSvg
                                ? ColorFiltered(
                                    colorFilter: _viewMode == 1
                                        ? const ColorFilter.mode(
                                            Colors.white, BlendMode.saturation)
                                        : const ColorFilter.mode(
                                            Colors.transparent,
                                            BlendMode.multiply),
                                    child: Image.network(artwork.downloadUrl!,
                                        fit: BoxFit.contain),
                                  )
                                : const Icon(Icons.image,
                                    color: AppColors.textMuted),
                          ),
                        ),
                      ),
                      Positioned(
                        bottom: 24,
                        left: 0,
                        right: 0,
                        child: Center(
                          child: Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: Colors.black54,
                              borderRadius: BorderRadius.circular(24),
                              border: Border.all(color: Colors.white10),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                for (final (index, label) in const [
                                  "Standard CMYK",
                                  "White Underbase",
                                  "Combined",
                                ].indexed)
                                  _ViewModeButton(
                                    label: label,
                                    selected: _viewMode == index,
                                    onTap: () =>
                                        setState(() => _viewMode = index),
                                  ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: const TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.bold,
          color: AppColors.pulseYellow,
          letterSpacing: 0.6),
    );
  }
}

class _PhysicalDimensions extends StatelessWidget {
  const _PhysicalDimensions({required this.artwork});
  final Artwork artwork;

  @override
  Widget build(BuildContext context) {
    final dpi = artwork.sourceDpi ?? 300;
    final widthCm = artwork.width != null
        ? (artwork.width! / dpi * 2.54).toStringAsFixed(1)
        : "—";
    final heightCm = artwork.height != null
        ? (artwork.height! / dpi * 2.54).toStringAsFixed(1)
        : "—";
    return Row(
      children: [
        Expanded(child: _DimField(label: "W (cm)", value: widthCm)),
        const SizedBox(width: 10),
        Expanded(child: _DimField(label: "H (cm)", value: heightCm)),
      ],
    );
  }
}

class _DimField extends StatelessWidget {
  const _DimField({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.black26,
        border: Border.all(color: Colors.white10),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 9, color: AppColors.textMuted)),
          Text(value,
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary)),
        ],
      ),
    );
  }
}

class _SliderRow extends StatelessWidget {
  const _SliderRow({
    required this.label,
    required this.value,
    required this.max,
    required this.unit,
    required this.onChanged,
  });

  final String label;
  final double value;
  final double max;
  final String unit;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label,
                style:
                    const TextStyle(fontSize: 11, color: AppColors.textMuted)),
            Text(
              "${value.toStringAsFixed(1)} $unit",
              style:
                  const TextStyle(fontSize: 11, color: AppColors.textPrimary),
            ),
          ],
        ),
        Slider(value: value, max: max, onChanged: onChanged),
      ],
    );
  }
}

class _PrintCheckList extends StatelessWidget {
  const _PrintCheckList({required this.scanState, required this.report});
  final AsyncValue<ProcessingJob?> scanState;
  final DtfCheckReport? report;

  @override
  Widget build(BuildContext context) {
    if (scanState.isLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: LoadingPanel(),
      );
    }
    if (report == null) {
      return const Text("Scan pending...",
          style: TextStyle(color: AppColors.textMuted, fontSize: 12));
    }
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.info.withValues(alpha: 0.08),
        border: Border.all(color: AppColors.info.withValues(alpha: 0.2)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final finding in report!.checks)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    finding.isError ? Icons.close : Icons.warning_amber_rounded,
                    color: finding.isError
                        ? AppColors.critical
                        : AppColors.warning,
                    size: 14,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      finding.message,
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textSecondary),
                    ),
                  ),
                ],
              ),
            ),
          if (report!.checks.isEmpty)
            const Row(
              children: [
                Icon(Icons.check, color: AppColors.success, size: 14),
                SizedBox(width: 8),
                Text("All automated checks passed",
                    style: TextStyle(
                        fontSize: 11, color: AppColors.textSecondary)),
              ],
            ),
        ],
      ),
    );
  }
}

class _ViewModeButton extends StatelessWidget {
  const _ViewModeButton(
      {required this.label, required this.selected, required this.onTap});
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(20),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.pulseYellow : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.bold,
            color: selected ? AppColors.onAccent : AppColors.textMuted,
          ),
        ),
      ),
    );
  }
}
