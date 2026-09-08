import "package:dio/dio.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/api/api_client.dart";
import "../../../core/api/api_envelope.dart";
import "../../../core/api/api_exception.dart";
import "../../../core/models/export_job.dart";

final exportRepositoryProvider = Provider<ExportRepository>((ref) {
  return ExportRepository(ref.watch(apiClientProvider));
});

class ExportRepository {
  ExportRepository(this._dio);
  final Dio _dio;

  Future<ExportJob> create({
    required String projectId,
    required String artworkId,
    required ExportFormat format,
    Map<String, dynamic> parameters = const {},
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/exports",
        data: {
          "project_id": projectId,
          "artwork_id": artworkId,
          "format": format.name,
          "parameters": parameters,
        },
      );
      return await unwrap(
          response, (json) => ExportJob.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<ExportJob> get(String exportId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>("/exports/$exportId");
      return await unwrap(
          response, (json) => ExportJob.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}
