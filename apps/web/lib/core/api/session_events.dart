import "package:flutter_riverpod/flutter_riverpod.dart";

/// Fired when the API layer determines the session is no longer valid (a 401
/// survived a refresh attempt). The auth feature listens for this to reset its
/// state; kept in core (rather than importing the auth feature) so the API
/// client never has to depend on a feature module.
final sessionExpiredProvider = StateProvider<Object>((ref) => Object());
