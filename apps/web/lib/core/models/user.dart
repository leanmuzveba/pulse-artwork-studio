class User {
  const User({
    required this.id,
    required this.email,
    required this.fullName,
    required this.isVerified,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
        id: json["id"] as String,
        email: json["email"] as String,
        fullName: json["full_name"] as String?,
        isVerified: json["is_verified"] as bool,
      );

  final String id;
  final String email;
  final String? fullName;
  final bool isVerified;

  String get displayName =>
      (fullName == null || fullName!.trim().isEmpty) ? email : fullName!;

  String get initials {
    final name = displayName.trim();
    if (name.isEmpty) return "?";
    final parts = name.split(RegExp(r"\s+"));
    if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
    return (parts.first.substring(0, 1) + parts.last.substring(0, 1))
        .toUpperCase();
  }
}
