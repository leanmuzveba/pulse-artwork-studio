import "package:dio/dio.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../env.dart";
import "../storage/token_storage.dart";
import "session_events.dart";

/// Paths that must never carry a (possibly stale) Authorization header, and
/// whose own 401s must never trigger a refresh-and-retry loop.
const _publicPaths = <String>["/auth/login", "/auth/register", "/auth/refresh"];

final apiClientProvider = Provider<Dio>((ref) {
  final storage = ref.watch(tokenStorageProvider);
  final dio = Dio(
    BaseOptions(
      baseUrl: Env.apiBaseUrl,
      connectTimeout: const Duration(seconds: 20),
      receiveTimeout: const Duration(seconds: 60),
      contentType: "application/json",
    ),
  );

  // Separate client for token refresh so its interceptor never re-triggers
  // this file's own 401 handling.
  final refreshDio = Dio(BaseOptions(baseUrl: Env.apiBaseUrl));

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        final isPublic = _publicPaths.any((p) => options.path.startsWith(p));
        if (!isPublic) {
          final token = storage.accessToken;
          if (token != null) {
            options.headers["Authorization"] = "Bearer $token";
          }
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final isPublic =
            _publicPaths.any((p) => error.requestOptions.path.startsWith(p));
        final alreadyRetried = error.requestOptions.extra["retried"] == true;
        if (error.response?.statusCode != 401 || isPublic || alreadyRetried) {
          handler.next(error);
          return;
        }

        final refreshToken = storage.refreshToken;
        if (refreshToken == null) {
          handler.next(error);
          return;
        }

        try {
          final response = await refreshDio.post<Map<String, dynamic>>(
            "/auth/refresh",
            data: {"refresh_token": refreshToken},
          );
          final tokens = response.data?["data"] as Map<String, dynamic>?;
          final accessToken = tokens?["access_token"] as String?;
          final newRefreshToken = tokens?["refresh_token"] as String?;
          if (accessToken == null || newRefreshToken == null) {
            throw StateError("Malformed refresh response");
          }
          await storage.save(
              accessToken: accessToken, refreshToken: newRefreshToken);

          final retryOptions = error.requestOptions
            ..headers["Authorization"] = "Bearer $accessToken"
            ..extra["retried"] = true;
          final retryResponse = await dio.fetch<dynamic>(retryOptions);
          handler.resolve(retryResponse);
        } catch (_) {
          await storage.clear();
          ref.read(sessionExpiredProvider.notifier).state = Object();
          handler.next(error);
        }
      },
    ),
  );

  return dio;
});
