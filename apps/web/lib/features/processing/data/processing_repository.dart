import "package:dio/dio.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/api/api_client.dart";
import "../../../core/api/api_envelope.dart";
import "../../../core/api/api_exception.dart";
import "../../../core/models/processing_job.dart";

final processingRepositoryProvider = Provider<ProcessingRepository>((ref) {
  return ProcessingRepository(ref.watch(apiClientProvider));
});

class ProcessingRepository {
  ProcessingRepository(this._dio);
  final Dio _dio;

  Future<ProcessingJob> createJob({
    required String projectId,
    required String artworkId,
    required JobOperation operation,
    Map<String, dynamic> parameters = const {},
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/processing/jobs",
        data: {
          "project_id": projectId,
          "artwork_id": artworkId,
          "operation": operation.wireValue,
          "parameters": parameters,
        },
      );
      return await unwrap(
        response,
        (json) => ProcessingJob.fromJson(json as Map<String, dynamic>),
      );
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<ProcessingJob> getJob(String jobId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>("/processing/jobs/$jobId");
      return await unwrap(
        response,
        (json) => ProcessingJob.fromJson(json as Map<String, dynamic>),
      );
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}
