import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:url_launcher/url_launcher.dart";

import "../../../app/theme/app_colors.dart";
import "../../../app/widgets/common_widgets.dart";
import "../../../core/models/artwork.dart";
import "../../../core/models/gang_sheet.dart";
import "../../artworks/application/artwork_controllers.dart";
import "../application/gang_sheet_run_controller.dart";

/// Multi-artwork auto-nest: pick artworks from the project, set copies and
/// rotation per item, choose a roll-width preset (or a custom width) plus
/// spacing/DPI, and composite them onto one print sheet.
class GangSheetScreen extends ConsumerStatefulWidget {
  const GangSheetScreen({required this.projectId, super.key});
  final String projectId;

  @override
  ConsumerState<GangSheetScreen> createState() => _GangSheetScreenState();
}

class _GangSheetScreenState extends ConsumerState<GangSheetScreen> {
  final Map<String, GangSheetItem> _selected = {};
  String _widthPreset = gangSheetWidthPresetsMm.keys.first;
  final _customWidthController = TextEditingController(text: "300");
  int _spacingMm = 5;
  int _dpi = 300;

  @override
  void dispose() {
    _customWidthController.dispose();
    super.dispose();
  }

  int get _sheetWidthMm => _widthPreset == "Custom"
      ? (int.tryParse(_customWidthController.text) ?? 300)
      : gangSheetWidthPresetsMm[_widthPreset]!;

  void _toggle(Artwork artwork, bool selected) {
    setState(() {
      if (selected) {
        _selected[artwork.id] = GangSheetItem(artworkId: artwork.id);
      } else {
        _selected.remove(artwork.id);
      }
    });
  }

  void _updateItem(String artworkId, GangSheetItem item) {
    setState(() => _selected[artworkId] = item);
  }

  Future<void> _build() async {
    ref.read(gangSheetRunControllerProvider.notifier).reset();
    await ref.read(gangSheetRunControllerProvider.notifier).run(
          projectId: widget.projectId,
          sheetWidthMm: _sheetWidthMm,
          spacingMm: _spacingMm,
          dpi: _dpi,
          items: _selected.values.toList(),
        );
  }

  @override
  Widget build(BuildContext context) {
    final artworksAsync =
        ref.watch(projectArtworksProvider(widget.projectId));
    final runState = ref.watch(gangSheetRunControllerProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  "Gang Sheet Builder",
                  style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                      color: AppColors.textPrimary),
                ),
              ),
              TextButton.icon(
                onPressed: () => context.goNamed("project-detail",
                    pathParameters: {"projectId": widget.projectId}),
                icon: const Icon(Icons.arrow_back, size: 16),
                label: const Text("Back to Project"),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            "Auto-nests the selected artworks onto one print sheet. A "
            "simulation of layout, not a RIP replacement.",
            style: TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
          const SizedBox(height: 32),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 3,
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("SELECT ARTWORKS",
                            style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: AppColors.textMuted,
                                letterSpacing: 0.6)),
                        const SizedBox(height: 12),
                        artworksAsync.when(
                          loading: () => const Padding(
                            padding: EdgeInsets.symmetric(vertical: 24),
                            child: LoadingPanel(),
                          ),
                          error: (error, _) =>
                              ErrorPanel(message: "$error"),
                          data: (artworks) {
                            final ready = artworks
                                .where((a) => a.status == ArtworkStatus.ready)
                                .toList();
                            if (ready.isEmpty) {
                              return const Padding(
                                padding: EdgeInsets.symmetric(vertical: 24),
                                child: Text(
                                  "No ready artworks in this project yet.",
                                  style:
                                      TextStyle(color: AppColors.textMuted),
                                ),
                              );
                            }
                            return Column(
                              children: [
                                for (final artwork in ready)
                                  _ArtworkRow(
                                    artwork: artwork,
                                    item: _selected[artwork.id],
                                    onToggle: (v) => _toggle(artwork, v),
                                    onChanged: (item) =>
                                        _updateItem(artwork.id, item),
                                  ),
                              ],
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                flex: 2,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text("SHEET SETTINGS",
                                style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.textMuted,
                                    letterSpacing: 0.6)),
                            const SizedBox(height: 12),
                            const Text("Roll width",
                                style: TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textMuted)),
                            const SizedBox(height: 6),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                for (final label in [
                                  ...gangSheetWidthPresetsMm.keys,
                                  "Custom",
                                ])
                                  _PresetChip(
                                    label: label,
                                    selected: _widthPreset == label,
                                    onTap: () =>
                                        setState(() => _widthPreset = label),
                                  ),
                              ],
                            ),
                            if (_widthPreset == "Custom") ...[
                              const SizedBox(height: 8),
                              TextField(
                                controller: _customWidthController,
                                keyboardType: TextInputType.number,
                                decoration: const InputDecoration(
                                    labelText: "Width (mm)"),
                              ),
                            ],
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: _NumberField(
                                    label: "Spacing (mm)",
                                    value: _spacingMm,
                                    onChanged: (v) =>
                                        setState(() => _spacingMm = v),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: _NumberField(
                                    label: "DPI",
                                    value: _dpi,
                                    onChanged: (v) =>
                                        setState(() => _dpi = v),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 20),
                            SizedBox(
                              width: double.infinity,
                              child: FilledButton.icon(
                                onPressed: (_selected.isEmpty ||
                                        runState.isLoading)
                                    ? null
                                    : _build,
                                icon: runState.isLoading
                                    ? const SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: AppColors.onAccent),
                                      )
                                    : const Icon(Icons.grid_view_rounded,
                                        size: 18),
                                label: Text(runState.isLoading
                                    ? "Building..."
                                    : "Build Gang Sheet"),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    runState.when(
                      loading: () => const SizedBox.shrink(),
                      error: (error, _) => Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text("$error",
                              style:
                                  const TextStyle(color: AppColors.critical)),
                        ),
                      ),
                      data: (gangSheet) {
                        if (gangSheet == null) return const SizedBox.shrink();
                        if (gangSheet.status == GangSheetStatus.failed) {
                          return Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Text(
                                gangSheet.errorMessage ??
                                    "Gang sheet build failed.",
                                style:
                                    const TextStyle(color: AppColors.critical),
                              ),
                            ),
                          );
                        }
                        if (gangSheet.status != GangSheetStatus.ready) {
                          return const SizedBox.shrink();
                        }
                        return _ResultCard(gangSheet: gangSheet);
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ArtworkRow extends StatelessWidget {
  const _ArtworkRow({
    required this.artwork,
    required this.item,
    required this.onToggle,
    required this.onChanged,
  });
  final Artwork artwork;
  final GangSheetItem? item;
  final ValueChanged<bool> onToggle;
  final ValueChanged<GangSheetItem> onChanged;

  @override
  Widget build(BuildContext context) {
    final selected = item != null;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: selected ? AppColors.pulseYellow.withValues(alpha: 0.06) : null,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Checkbox(value: selected, onChanged: (v) => onToggle(v ?? false)),
          Expanded(
            child: Text(
              artwork.originalFilename ?? "Untitled",
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: AppColors.textPrimary, fontSize: 13),
            ),
          ),
          if (selected) ...[
            IconButton(
              tooltip: "Rotate 90°",
              icon: const Icon(Icons.rotate_90_degrees_cw_rounded, size: 18),
              onPressed: () => onChanged(GangSheetItem(
                artworkId: artwork.id,
                copies: item!.copies,
                rotateDeg: (item!.rotateDeg + 90) % 360,
              )),
            ),
            IconButton(
              tooltip: "Fewer copies",
              icon: const Icon(Icons.remove_circle_outline, size: 18),
              onPressed: item!.copies <= 1
                  ? null
                  : () => onChanged(GangSheetItem(
                        artworkId: artwork.id,
                        copies: item!.copies - 1,
                        rotateDeg: item!.rotateDeg,
                      )),
            ),
            SizedBox(
              width: 20,
              child: Text("${item!.copies}",
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.textPrimary)),
            ),
            IconButton(
              tooltip: "More copies",
              icon: const Icon(Icons.add_circle_outline, size: 18),
              onPressed: () => onChanged(GangSheetItem(
                artworkId: artwork.id,
                copies: item!.copies + 1,
                rotateDeg: item!.rotateDeg,
              )),
            ),
          ],
        ],
      ),
    );
  }
}

class _PresetChip extends StatelessWidget {
  const _PresetChip(
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
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? AppColors.pulseYellow : Colors.black26,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
              color: selected ? AppColors.pulseYellow : Colors.white10),
        ),
        child: Text(
          label,
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

class _NumberField extends StatelessWidget {
  const _NumberField(
      {required this.label, required this.value, required this.onChanged});
  final String label;
  final int value;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      initialValue: "$value",
      keyboardType: TextInputType.number,
      decoration: InputDecoration(labelText: label),
      onChanged: (text) {
        final parsed = int.tryParse(text);
        if (parsed != null) onChanged(parsed);
      },
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.gangSheet});
  final GangSheet gangSheet;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.check_circle, color: AppColors.success, size: 18),
                SizedBox(width: 8),
                Text("Sheet ready",
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              "${gangSheet.sheetWidthMm}mm x ${gangSheet.sheetHeightMm ?? '—'}mm "
              "@ ${gangSheet.dpi} DPI",
              style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
            ),
            if (gangSheet.downloadUrl != null) ...[
              const SizedBox(height: 12),
              AspectRatio(
                aspectRatio: gangSheet.sheetHeightMm != null &&
                        gangSheet.sheetHeightMm! > 0
                    ? gangSheet.sheetWidthMm / gangSheet.sheetHeightMm!
                    : 1,
                child: Image.network(gangSheet.downloadUrl!, fit: BoxFit.contain),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () =>
                      launchUrl(Uri.parse(gangSheet.downloadUrl!)),
                  icon: const Icon(Icons.download_rounded, size: 16),
                  label: const Text("Download"),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
