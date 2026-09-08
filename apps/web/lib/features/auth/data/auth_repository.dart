import "package:dio/dio.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/api/api_client.dart";
import "../../../core/api/api_envelope.dart";
import "../../../core/api/api_exception.dart";
import "../../../core/models/user.dart";
import "../../../core/storage/token_storage.dart";

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
      ref.watch(apiClientProvider), ref.watch(tokenStorageProvider));
});

class AuthTokens {
  const AuthTokens({required this.accessToken, required this.refreshToken});
  final String accessToken;
  final String refreshToken;
}

class AuthRepository {
  AuthRepository(this._dio, this._storage);

  final Dio _dio;
  final TokenStorage _storage;

  Future<User> register(
      {required String email,
      required String password,
      String? fullName}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/auth/register",
        data: {"email": email, "password": password, "full_name": fullName},
      );
      return await unwrap(
          response, (json) => User.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<void> login({required String email, required String password}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/auth/login",
        data: {"email": email, "password": password},
      );
      final tokens = unwrap(
        response,
        (json) => AuthTokens(
          accessToken: (json as Map<String, dynamic>)["access_token"] as String,
          refreshToken: json["refresh_token"] as String,
        ),
      );
      await _storage.save(
          accessToken: tokens.accessToken, refreshToken: tokens.refreshToken);
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<User> me() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>("/users/me");
      return await unwrap(
          response, (json) => User.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<void> logout() => _storage.clear();
}
