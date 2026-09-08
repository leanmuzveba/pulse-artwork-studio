enum ArtworkKind {
  original,
  derived;

  static ArtworkKind fromJson(String value) => ArtworkKind.values
      .firstWhere((e) => e.name == value, orElse: () => ArtworkKind.original);
}

enum ArtworkStatus {
  uploading,
  ready,
  failed;

  static ArtworkStatus fromJson(String value) =>
      ArtworkStatus.values.firstWhere((e) => e.name == value,
          orElse: () => ArtworkStatus.uploading);
}

class Artwork {
  const Artwork({
    required this.id,
    required this.projectId,
    required this.parentArtworkId,
    required this.kind,
    required this.status,
    required this.originalFilename,
    required this.mimeType,
    required this.sizeBytes,
    required this.width,
    required this.height,
    required this.sourceDpi,
    required this.createdAt,
    this.downloadUrl,
  });

  factory Artwork.fromJson(Map<String, dynamic> json) => Artwork(
        id: json["id"] as String,
        projectId: json["project_id"] as String,
        parentArtworkId: json["parent_artwork_id"] as String?,
        kind: ArtworkKind.fromJson(json["kind"] as String),
        status: ArtworkStatus.fromJson(json["status"] as String),
        originalFilename: json["original_filename"] as String?,
        mimeType: json["mime_type"] as String?,
        sizeBytes: json["size_bytes"] as int?,
        width: json["width"] as int?,
        height: json["height"] as int?,
        sourceDpi: json["source_dpi"] as int?,
        createdAt: DateTime.parse(json["created_at"] as String),
        downloadUrl: json["download_url"] as String?,
      );

  final String id;
  final String projectId;
  final String? parentArtworkId;
  final ArtworkKind kind;
  final ArtworkStatus status;
  final String? originalFilename;
  final String? mimeType;
  final int? sizeBytes;
  final int? width;
  final int? height;
  final int? sourceDpi;
  final DateTime createdAt;
  final String? downloadUrl;

  bool get isSvg => mimeType == "image/svg+xml";

  String get dimensionsLabel => (width != null && height != null)
      ? "$width x $height px"
      : "Dimensions pending";

  String get dpiLabel => sourceDpi != null ? "$sourceDpi DPI" : "DPI pending";
}
