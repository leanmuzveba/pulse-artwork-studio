import "dart:typed_data";

import "package:dio/dio.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/api/api_client.dart";
import "../../../core/api/api_envelope.dart";
import "../../../core/api/api_exception.dart";
import "../../../core/models/artwork.dart";

final artworkRepositoryProvider = Provider<ArtworkRepository>((ref) {
  // A bare Dio, deliberately without the API client's auth interceptor —
  // uploads go straight to a presigned object-storage URL, not the API.
  return ArtworkRepository(ref.watch(apiClientProvider), Dio());
});

class UploadUrlTicket {
  const UploadUrlTicket({
    required this.artworkId,
    required this.uploadUrl,
    required this.requiredHeaders,
  });

  final String artworkId;
  final String uploadUrl;
  final Map<String, String> requiredHeaders;
}

class ArtworkRepository {
  ArtworkRepository(this._dio, this._rawDio);
  final Dio _dio;
  final Dio _rawDio;

  Future<UploadUrlTicket> requestUploadUrl({
    required String projectId,
    required String filename,
    required String contentType,
    required int sizeBytes,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/projects/$projectId/artworks/upload-url",
        data: {
          "filename": filename,
          "content_type": contentType,
          "size_bytes": sizeBytes
        },
      );
      return await unwrap(
        response,
        (json) => UploadUrlTicket(
          artworkId: (json as Map<String, dynamic>)["artwork_id"] as String,
          uploadUrl: json["upload_url"] as String,
          requiredHeaders: (json["required_headers"] as Map<String, dynamic>)
              .map((k, v) => MapEntry(k, v.toString())),
        ),
      );
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<void> uploadBytes({
    required String uploadUrl,
    required Uint8List bytes,
    required Map<String, String> headers,
  }) async {
    try {
      await _rawDio.putUri<void>(
        Uri.parse(uploadUrl),
        data: Stream.fromIterable([bytes]),
        options: Options(
          headers: {...headers, Headers.contentLengthHeader: bytes.length},
        ),
      );
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<Artwork> confirm(
      {required String projectId, required String artworkId}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/projects/$projectId/artworks/$artworkId/confirm",
        data: <String, dynamic>{},
      );
      return await unwrap(
          response, (json) => Artwork.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<List<Artwork>> list(String projectId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>("/projects/$projectId/artworks");
      return unwrapList(response, Artwork.fromJson);
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<Artwork> get(
      {required String projectId, required String artworkId}) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
          "/projects/$projectId/artworks/$artworkId");
      return await unwrap(
          response, (json) => Artwork.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}
