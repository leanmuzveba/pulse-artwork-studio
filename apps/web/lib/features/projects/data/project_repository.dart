import "package:dio/dio.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/api/api_client.dart";
import "../../../core/api/api_envelope.dart";
import "../../../core/api/api_exception.dart";
import "../../../core/models/project.dart";

final projectRepositoryProvider = Provider<ProjectRepository>((ref) {
  return ProjectRepository(ref.watch(apiClientProvider));
});

class ProjectRepository {
  ProjectRepository(this._dio);
  final Dio _dio;

  Future<Project> create(String name) async {
    try {
      final response = await _dio
          .post<Map<String, dynamic>>("/projects", data: {"name": name});
      return await unwrap(
          response, (json) => Project.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<List<Project>> list() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>("/projects");
      return unwrapList(response, Project.fromJson);
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<Project> get(String projectId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>("/projects/$projectId");
      return await unwrap(
          response, (json) => Project.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}
