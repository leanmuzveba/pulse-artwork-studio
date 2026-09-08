import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/api/session_events.dart";
import "../../../core/storage/token_storage.dart";
import "../data/auth_repository.dart";

/// Whether the app currently holds a session (an access token in storage).
/// This is a synchronous, local check — it does not itself verify the token
/// is still valid server-side; a stale token is caught the first time an API
/// call 401s (see [sessionExpiredProvider]) and clears itself here.
final authSessionControllerProvider =
    NotifierProvider<AuthSessionController, bool>(
  AuthSessionController.new,
);

class AuthSessionController extends Notifier<bool> {
  @override
  bool build() {
    ref.listen(sessionExpiredProvider, (previous, next) => state = false);
    return ref.read(tokenStorageProvider).accessToken != null;
  }

  Future<void> login({required String email, required String password}) async {
    await ref
        .read(authRepositoryProvider)
        .login(email: email, password: password);
    state = true;
  }

  Future<void> register({
    required String email,
    required String password,
    String? fullName,
  }) async {
    await ref.read(authRepositoryProvider).register(
          email: email,
          password: password,
          fullName: fullName,
        );
    await login(email: email, password: password);
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    state = false;
  }
}

/// The signed-in user's profile, fetched lazily for display (sidebar, dashboard
/// greeting). Independent of route guarding, which relies only on
/// [authSessionControllerProvider].
final currentUserProvider = FutureProvider.autoDispose((ref) async {
  final isAuthed = ref.watch(authSessionControllerProvider);
  if (!isAuthed) return null;
  return ref.watch(authRepositoryProvider).me();
});
