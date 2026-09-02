import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../features/auth/presentation/login_screen.dart";
import "../../features/dashboard/presentation/dashboard_screen.dart";
import "../../features/editor/presentation/editor_screen.dart";

/// App route table. Auth guarding is added when the auth feature lands.
final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: "/",
    routes: <RouteBase>[
      GoRoute(
        path: "/",
        name: "dashboard",
        builder: (context, state) => const DashboardScreen(),
      ),
      GoRoute(
        path: "/login",
        name: "login",
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: "/editor",
        name: "editor",
        builder: (context, state) => const EditorScreen(),
      ),
    ],
  );
});
