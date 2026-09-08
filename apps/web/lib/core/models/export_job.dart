enum ExportFormat {
  png,
  svg,
  pdf;

  static ExportFormat fromJson(String value) =>
      ExportFormat.values.firstWhere((e) => e.name == value);

  String get label => name.toUpperCase();
}

enum ExportStatus {
  pending,
  ready,
  failed;

  static ExportStatus fromJson(String value) => ExportStatus.values
      .firstWhere((e) => e.name == value, orElse: () => ExportStatus.pending);
}

class ExportJob {
  const ExportJob({
    required this.id,
    required this.projectId,
    required this.artworkId,
    required this.format,
    required this.status,
    required this.width,
    required this.height,
    required this.dpi,
    required this.errorMessage,
    required this.createdAt,
    this.downloadUrl,
  });

  factory ExportJob.fromJson(Map<String, dynamic> json) => ExportJob(
        id: json["id"] as String,
        projectId: json["project_id"] as String,
        artworkId: json["artwork_id"] as String,
        format: ExportFormat.fromJson(json["format"] as String),
        status: ExportStatus.fromJson(json["status"] as String),
        width: json["width"] as int?,
        height: json["height"] as int?,
        dpi: json["dpi"] as int?,
        errorMessage: json["error_message"] as String?,
        createdAt: DateTime.parse(json["created_at"] as String),
        downloadUrl: json["download_url"] as String?,
      );

  final String id;
  final String projectId;
  final String artworkId;
  final ExportFormat format;
  final ExportStatus status;
  final int? width;
  final int? height;
  final int? dpi;
  final String? errorMessage;
  final DateTime createdAt;
  final String? downloadUrl;
}
