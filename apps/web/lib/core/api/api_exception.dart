import "package:dio/dio.dart";

/// The API's error envelope: `{ "error": { "code", "message", "details" }, "request_id" }`.
class ApiException implements Exception {
  const ApiException({
    required this.code,
    required this.message,
    this.statusCode,
    this.details,
  });

  factory ApiException.fromDioError(DioException error) {
    final data = error.response?.data;
    if (data is Map && data["error"] is Map) {
      final err = data["error"] as Map;
      return ApiException(
        code: err["code"]?.toString() ?? "unknown_error",
        message: err["message"]?.toString() ?? "Something went wrong.",
        statusCode: error.response?.statusCode,
        details: err["details"],
      );
    }
    return ApiException(
      code: "network_error",
      message: switch (error.type) {
        DioExceptionType.connectionTimeout ||
        DioExceptionType.receiveTimeout ||
        DioExceptionType.sendTimeout =>
          "The server took too long to respond. Please try again.",
        DioExceptionType.connectionError =>
          "Couldn't reach the Pulse API. Check your connection and try again.",
        _ => error.message ?? "Something went wrong.",
      },
      statusCode: error.response?.statusCode,
    );
  }

  final String code;
  final String message;
  final int? statusCode;
  final Object? details;

  @override
  String toString() => message;
}
