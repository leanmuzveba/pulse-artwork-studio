import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../app/theme/app_colors.dart";
import "../../../app/widgets/common_widgets.dart";
import "../../../core/models/processing_job.dart";
import "../../artworks/application/artwork_controllers.dart";
import "../../processing/application/processing_run_controller.dart";

/// Maps a `dtf_check` finding code to the processing operation that can fix
/// it, when one exists. Some findings (unsupported color mode, image too
/// small) have no one-click remedy yet.
const _fixByCode = <String, JobOperation>{
  "low_resolution": JobOperation.upscale,
  "no_transparency": JobOperation.backgroundRemoval,
};

class InspectorScreen extends ConsumerStatefulWidget {
  const InspectorScreen(
      {required this.projectId, required this.artworkId, super.key});
  final String projectId;
  final String artworkId;

  @override
  ConsumerState<InspectorScreen> createState() => _InspectorScreenState();
}

class _InspectorScreenState extends ConsumerState<InspectorScreen> {
  static const _scanTag = "inspector-scan";
  static const _fixTag = "inspector-fix";
  bool _fixingAll = false;

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
      _scan();
    });
  }

  Future<void> _scan() {
    return ref.read(processingRunControllerProvider(_scanTag).notifier).run(
        projectId: widget.projectId,
        artworkId: widget.artworkId,
        operation: JobOperation.dtfCheck);
  }

  Future<void> _fix(DtfCheckFinding finding) async {
    final operation = _fixByCode[finding.code];
    if (operation == null) return;
    await ref.read(processingRunControllerProvider(_fixTag).notifier).run(
        projectId: widget.projectId,
        artworkId: widget.artworkId,
        operation: operation);
    await _scan();
  }

  Future<void> _fixAll(List<DtfCheckFinding> findings) async {
    setState(() => _fixingAll = true);
    try {
      for (final finding in findings) {
        final operation = _fixByCode[finding.code];
        if (operation == null) continue;
        await ref.read(processingRunControllerProvider(_fixTag).notifier).run(
            projectId: widget.projectId,
            artworkId: widget.artworkId,
            operation: operation);
      }
      await _scan();
    } finally {
      if (mounted) setState(() => _fixingAll = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scanState = ref.watch(processingRunControllerProvider(_scanTag));
    final artworkAsync = ref.watch(
      artworkDetailProvider(
          (projectId: widget.projectId, artworkId: widget.artworkId)),
    );

    return SingleChildScrollView(
      padding: const EdgeInsets.all(40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "AI Artwork Inspector",
                      style: TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textPrimary),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      "Analysis of \"${artworkAsync.valueOrNull?.originalFilename ?? '...'}\"",
                      style: const TextStyle(color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
              OutlinedButton(onPressed: _scan, child: const Text("Re-scan")),
              const SizedBox(width: 12),
              scanState.whenOrNull(
                    data: (job) {
                      final report = _reportOf(job);
                      if (report == null ||
                          report.checks
                              .every((f) => _fixByCode[f.code] == null)) {
                        return null;
                      }
                      return FilledButton.icon(
                        onPressed:
                            _fixingAll ? null : () => _fixAll(report.checks),
                        icon: _fixingAll
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: AppColors.onAccent),
                              )
                            : const Icon(Icons.auto_fix_high_rounded, size: 16),
                        label: const Text("Fix All Issues"),
                      );
                    },
                  ) ??
                  const SizedBox.shrink(),
            ],
          ),
          const SizedBox(height: 32),
          scanState.when(
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: 60),
              child: LoadingPanel(message: "Scanning artwork..."),
            ),
            error: (error, stackTrace) =>
                ErrorPanel(message: "$error", onRetry: _scan),
            data: (job) {
              if (job == null) return const SizedBox.shrink();
              if (job.status == JobStatus.failed) {
                return ErrorPanel(
                    message: job.errorMessage ?? "Inspection failed.",
                    onRetry: _scan);
              }
              if (!job.status.isTerminal) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 60),
                  child: LoadingPanel(message: "Scanning artwork..."),
                );
              }
              final report = _reportOf(job);
              if (report == null) return const SizedBox.shrink();
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 5, child: _SummaryCard(report: report)),
                  const SizedBox(width: 40),
                  Expanded(
                      flex: 7,
                      child: _FindingsList(report: report, onFix: _fix)),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  DtfCheckReport? _reportOf(ProcessingJob? job) {
    if (job == null || job.resultData == null) return null;
    return DtfCheckReport.fromJson(job.resultData as Map<String, dynamic>);
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.report});
  final DtfCheckReport report;

  @override
  Widget build(BuildContext context) {
    final color = report.ready ? AppColors.success : AppColors.warning;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          children: [
            Icon(
              report.ready ? Icons.check_circle : Icons.warning_amber_rounded,
              color: color,
              size: 56,
            ),
            const SizedBox(height: 16),
            Text(
              report.ready ? "Ready for DTF Print" : "Needs Attention",
              style: TextStyle(
                  fontSize: 18, fontWeight: FontWeight.w800, color: color),
            ),
            const SizedBox(height: 8),
            if (report.effectiveDpi != null)
              Text(
                "${report.effectiveDpi} effective DPI",
                style: const TextStyle(color: AppColors.textMuted),
              ),
            const SizedBox(height: 16),
            Text(
              report.ready
                  ? "This artwork passes all automated print-readiness checks."
                  : "${report.checks.where((f) => f.isError).length} critical and "
                      "${report.checks.where((f) => !f.isError).length} warning issue(s) found.",
              textAlign: TextAlign.center,
              style:
                  const TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}

class _FindingsList extends StatelessWidget {
  const _FindingsList({required this.report, required this.onFix});
  final DtfCheckReport report;
  final void Function(DtfCheckFinding) onFix;

  @override
  Widget build(BuildContext context) {
    if (report.checks.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Row(
            children: [
              Icon(Icons.check, color: AppColors.success),
              SizedBox(width: 12),
              Expanded(
                child: Text("No issues detected.",
                    style: TextStyle(color: AppColors.textSecondary)),
              ),
            ],
          ),
        ),
      );
    }
    return Column(
      children: [
        Text(
          "Detected Issues (${report.checks.length})",
          style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary),
        ),
        const SizedBox(height: 12),
        for (final finding in report.checks)
          _FindingCard(finding: finding, onFix: onFix),
      ],
    );
  }
}

class _FindingCard extends StatelessWidget {
  const _FindingCard({required this.finding, required this.onFix});
  final DtfCheckFinding finding;
  final void Function(DtfCheckFinding) onFix;

  @override
  Widget build(BuildContext context) {
    final color = finding.isError ? AppColors.critical : AppColors.warning;
    final fixable = _fixByCode.containsKey(finding.code);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.charcoalLight,
        borderRadius: BorderRadius.circular(14),
        border: Border(left: BorderSide(color: color, width: 4)),
      ),
      padding: const EdgeInsets.all(18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              finding.isError ? Icons.priority_high : Icons.info_outline,
              color: color,
              size: 20,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _titleFor(finding.code),
                        style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            color: AppColors.textPrimary),
                      ),
                    ),
                    StatusChip(
                        label: finding.isError ? "CRITICAL" : "WARNING",
                        color: color),
                  ],
                ),
                const SizedBox(height: 6),
                Text(finding.message,
                    style: const TextStyle(
                        color: AppColors.textSecondary, fontSize: 13)),
                if (fixable) ...[
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: () => onFix(finding),
                    style: TextButton.styleFrom(padding: EdgeInsets.zero),
                    child: Text("Fix: ${_fixByCode[finding.code]!.wireValue}"),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _titleFor(String code) {
    return switch (code) {
      "low_resolution" => "Resolution Too Low",
      "no_transparency" => "Background Detected",
      "unsupported_color_mode" => "Unsupported Color Mode",
      "image_too_small" => "Image Too Small",
      _ => code,
    };
  }
}
