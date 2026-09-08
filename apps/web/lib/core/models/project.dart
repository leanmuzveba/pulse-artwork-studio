enum ProjectStatus {
  active,
  archived,
  deleted;

  static ProjectStatus fromJson(String value) => ProjectStatus.values
      .firstWhere((e) => e.name == value, orElse: () => ProjectStatus.active);
}

class Project {
  const Project({
    required this.id,
    required this.name,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Project.fromJson(Map<String, dynamic> json) => Project(
        id: json["id"] as String,
        name: json["name"] as String,
        status: ProjectStatus.fromJson(json["status"] as String),
        createdAt: DateTime.parse(json["created_at"] as String),
        updatedAt: DateTime.parse(json["updated_at"] as String),
      );

  final String id;
  final String name;
  final ProjectStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;
}
