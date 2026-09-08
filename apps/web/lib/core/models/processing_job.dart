enum JobOperation {
  metadata,
  enhance,
  upscale,
  backgroundRemoval("background_removal"),
  vectorize,
  halftone,
  embroidery,
  dtfCheck("dtf_check");

  const JobOperation([String? wireValue]) : _wireValue = wireValue;

  final String? _wireValue;
  String get wireValue => _wireValue ?? name;

  static JobOperation fromJson(String value) =>
      JobOperation.values.firstWhere((e) => e.wireValue == value);
}

enum JobStatus {
  requested,
  queued,
  processing,
  completed,
  failed,
  cancelled;

  static JobStatus fromJson(String value) => JobStatus.values
      .firstWhere((e) => e.name == value, orElse: () => JobStatus.requested);

  bool get isTerminal =>
      this == completed || this == failed || this == cancelled;
}

class ProcessingJob {
  const ProcessingJob({
    required this.id,
    required this.projectId,
    required this.artworkId,
    required this.resultArtworkId,
    required this.resultData,
    required this.operation,
    required this.status,
    required this.progress,
    required this.errorMessage,
    required this.createdAt,
  });

  factory ProcessingJob.fromJson(Map<String, dynamic> json) => ProcessingJob(
        id: json["id"] as String,
        projectId: json["project_id"] as String,
        artworkId: json["artwork_id"] as String,
        resultArtworkId: json["result_artwork_id"] as String?,
        resultData: json["result_data"] as Map<String, dynamic>?,
        operation: JobOperation.fromJson(json["operation"] as String),
        status: JobStatus.fromJson(json["status"] as String),
        progress: json["progress"] as int,
        errorMessage: json["error_message"] as String?,
        createdAt: DateTime.parse(json["created_at"] as String),
      );

  final String id;
  final String projectId;
  final String artworkId;
  final String? resultArtworkId;
  final Map<String, dynamic>? resultData;
  final JobOperation operation;
  final JobStatus status;
  final int progress;
  final String? errorMessage;
  final DateTime createdAt;
}

/// A single finding from a `dtf_check` analysis job's `result_data.checks`.
class DtfCheckFinding {
  const DtfCheckFinding(
      {required this.code, required this.severity, required this.message});

  factory DtfCheckFinding.fromJson(Map<String, dynamic> json) =>
      DtfCheckFinding(
        code: json["code"] as String,
        severity: json["severity"] as String,
        message: json["message"] as String,
      );

  final String code;
  final String severity; // "warning" | "error"
  final String message;

  bool get isError => severity == "error";
}

class DtfCheckReport {
  const DtfCheckReport(
      {required this.ready, required this.effectiveDpi, required this.checks});

  factory DtfCheckReport.fromJson(Map<String, dynamic> json) => DtfCheckReport(
        ready: json["ready"] as bool? ?? false,
        effectiveDpi: json["effective_dpi"] as int?,
        checks: (json["checks"] as List<dynamic>? ?? [])
            .map((e) => DtfCheckFinding.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  final bool ready;
  final int? effectiveDpi;
  final List<DtfCheckFinding> checks;
}
