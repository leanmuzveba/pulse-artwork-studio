import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:shared_preferences/shared_preferences.dart";

final tokenStorageProvider = Provider<TokenStorage>((ref) {
  throw UnimplementedError(
      "tokenStorageProvider must be overridden at app startup");
});

/// Persists the access/refresh token pair. Backed by SharedPreferences, which
/// is local-storage-backed on web — adequate for this MVP's client-side auth.
class TokenStorage {
  TokenStorage(this._prefs);

  static const _accessKey = "pulse.access_token";
  static const _refreshKey = "pulse.refresh_token";

  final SharedPreferences _prefs;

  static Future<TokenStorage> create() async {
    return TokenStorage(await SharedPreferences.getInstance());
  }

  String? get accessToken => _prefs.getString(_accessKey);
  String? get refreshToken => _prefs.getString(_refreshKey);

  Future<void> save(
      {required String accessToken, required String refreshToken}) async {
    await _prefs.setString(_accessKey, accessToken);
    await _prefs.setString(_refreshKey, refreshToken);
  }

  Future<void> clear() async {
    await _prefs.remove(_accessKey);
    await _prefs.remove(_refreshKey);
  }
}
