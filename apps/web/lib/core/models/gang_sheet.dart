/// DTF roll-width presets this print shop stocks, in millimeters — matches
/// the roadmap's "30 / 33 / 60 cm" plus a free-entry custom width.
const Map<String, int> gangSheetWidthPresetsMm = {
  "30 cm": 300,
  "33 cm": 330,
  "60 cm": 600,
};

enum GangSheetStatus {
  pending,
  ready,
  failed;

  static GangSheetStatus fromJson(String value) => GangSheetStatus.values
      .firstWhere((e) => e.name == value, orElse: () => GangSheetStatus.pending);

  bool get isTerminal => this == ready || this == failed;
}

/// One artwork placed on a gang sheet — both as requested (`copies`,
/// `rotateDeg`) and, once the sheet is ready, as actually laid out
/// (`x`/`y`/`width`/`height`, all millimeters).
class GangSheetItem {
  const GangSheetItem({
    required this.artworkId,
    this.copies = 1,
    this.rotateDeg = 0,
  });

  factory GangSheetItem.fromJson(Map<String, dynamic> json) => GangSheetItem(
        artworkId: json["artwork_id"] as String,
        copies: json["copies"] as int? ?? 1,
        rotateDeg: json["rotate_deg"] as int? ?? 0,
      );

  final String artworkId;
  final int copies;
  final int rotateDeg;

  Map<String, dynamic> toJson() =>
      {"artwork_id": artworkId, "copies": copies, "rotate_deg": rotateDeg};
}

class GangSheetPlacement {
  const GangSheetPlacement({
    required this.artworkId,
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    required this.rotateDeg,
  });

  factory GangSheetPlacement.fromJson(Map<String, dynamic> json) =>
      GangSheetPlacement(
        artworkId: json["artwork_id"] as String,
        x: json["x"] as int,
        y: json["y"] as int,
        width: json["width"] as int,
        height: json["height"] as int,
        rotateDeg: json["rotate_deg"] as int,
      );

  final String artworkId;
  final int x;
  final int y;
  final int width;
  final int height;
  final int rotateDeg;
}

class GangSheet {
  const GangSheet({
    required this.id,
    required this.projectId,
    required this.status,
    required this.sheetWidthMm,
    required this.sheetHeightMm,
    required this.spacingMm,
    required this.dpi,
    required this.items,
    required this.layout,
    required this.errorMessage,
    required this.createdAt,
    this.downloadUrl,
  });

  factory GangSheet.fromJson(Map<String, dynamic> json) => GangSheet(
        id: json["id"] as String,
        projectId: json["project_id"] as String,
        status: GangSheetStatus.fromJson(json["status"] as String),
        sheetWidthMm: json["sheet_width_mm"] as int,
        sheetHeightMm: json["sheet_height_mm"] as int?,
        spacingMm: json["spacing_mm"] as int,
        dpi: json["dpi"] as int,
        items: (json["items"] as List<dynamic>? ?? [])
            .map((e) => GangSheetItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        layout: (json["layout"] as List<dynamic>?)
            ?.map((e) => GangSheetPlacement.fromJson(e as Map<String, dynamic>))
            .toList(),
        errorMessage: json["error_message"] as String?,
        createdAt: DateTime.parse(json["created_at"] as String),
        downloadUrl: json["download_url"] as String?,
      );

  final String id;
  final String projectId;
  final GangSheetStatus status;
  final int sheetWidthMm;
  final int? sheetHeightMm;
  final int spacingMm;
  final int dpi;
  final List<GangSheetItem> items;
  final List<GangSheetPlacement>? layout;
  final String? errorMessage;
  final DateTime createdAt;
  final String? downloadUrl;
}
