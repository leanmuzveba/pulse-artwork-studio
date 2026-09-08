import "package:dio/dio.dart";

/// Unwraps the API's `{ "data": ..., "request_id": ... }` success envelope.
T unwrap<T>(Response<dynamic> response, T Function(dynamic json) fromJson) {
  final body = response.data as Map<String, dynamic>;
  return fromJson(body["data"]);
}

List<T> unwrapList<T>(Response<dynamic> response,
    T Function(Map<String, dynamic> json) fromJson) {
  final body = response.data as Map<String, dynamic>;
  final list = body["data"] as List<dynamic>;
  return list.map((e) => fromJson(e as Map<String, dynamic>)).toList();
}
