import "package:flutter/foundation.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../features/auth/application/auth_session_controller.dart";
import "../../features/auth/presentation/login_screen.dart";
import "../../features/dashboard/presentation/dashboard_screen.dart";
import "../../features/dtf_prep/presentation/dtf_prep_screen.dart";
import "../../features/editor/presentation/editor_screen.dart";
import "../../features/exports/presentation/export_screen.dart";
import "../../features/gang_sheet/presentation/gang_sheet_screen.dart";
import "../../features/inspector/presentation/inspector_screen.dart";
import "../../features/projects/presentation/new_project_screen.dart";
import "../../features/projects/presentation/project_detail_screen.dart";
import "../widgets/app_shell.dart";

/// Bridges Riverpod's [authSessionControllerProvider] into a [Listenable]
/// go_router can use as `refreshListenable`, so route guards re-evaluate the
/// moment the session changes without recreating the router itself.
class _AuthRefreshListenable extends ChangeNotifier {
  _AuthRefreshListenable(Ref ref) {
    ref.listen(
        authSessionControllerProvider, (previous, next) => notifyListeners());
  }
}

final appRouterProvider = Provider<GoRouter>((ref) {
  final refresh = _AuthRefreshListenable(ref);

  return GoRouter(
    initialLocation: "/dashboard",
    refreshListenable: refresh,
    redirect: (context, state) {
      final isAuthed = ref.read(authSessionControllerProvider);
      final onAuthScreen = state.matchedLocation == "/login" ||
          state.matchedLocation == "/register";
      if (!isAuthed && !onAuthScreen) return "/login";
      if (isAuthed && onAuthScreen) return "/dashboard";
      return null;
    },
    routes: <RouteBase>[
      GoRoute(
        path: "/login",
        name: "login",
        builder: (context, state) =>
            const LoginScreen(mode: AuthFormMode.login),
      ),
      GoRoute(
        path: "/register",
        name: "register",
        builder: (context, state) =>
            const LoginScreen(mode: AuthFormMode.register),
      ),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: <RouteBase>[
          GoRoute(
            path: "/dashboard",
            name: "dashboard",
            builder: (context, state) => const DashboardScreen(),
          ),
          GoRoute(
            path: "/upload",
            name: "upload",
            builder: (context, state) => const NewProjectScreen(),
          ),
          GoRoute(
            path: "/projects/:projectId",
            name: "project-detail",
            builder: (context, state) => ProjectDetailScreen(
                projectId: state.pathParameters["projectId"]!),
          ),
          GoRoute(
            path: "/editor/:projectId/:artworkId",
            name: "editor",
            builder: (context, state) => EditorScreen(
              projectId: state.pathParameters["projectId"]!,
              artworkId: state.pathParameters["artworkId"]!,
            ),
          ),
          GoRoute(
            path: "/inspector/:projectId/:artworkId",
            name: "inspector",
            builder: (context, state) => InspectorScreen(
              projectId: state.pathParameters["projectId"]!,
              artworkId: state.pathParameters["artworkId"]!,
            ),
          ),
          GoRoute(
            path: "/dtf/:projectId/:artworkId",
            name: "dtf",
            builder: (context, state) => DtfPrepScreen(
              projectId: state.pathParameters["projectId"]!,
              artworkId: state.pathParameters["artworkId"]!,
            ),
          ),
          GoRoute(
            path: "/export/:projectId/:artworkId",
            name: "export",
            builder: (context, state) => ExportScreen(
              projectId: state.pathParameters["projectId"]!,
              artworkId: state.pathParameters["artworkId"]!,
            ),
          ),
          GoRoute(
            path: "/gang-sheet/:projectId",
            name: "gang-sheet",
            builder: (context, state) => GangSheetScreen(
              projectId: state.pathParameters["projectId"]!,
            ),
          ),
        ],
      ),
    ],
  );
});
