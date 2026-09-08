import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/models/user.dart";
import "../../features/artworks/application/artwork_controllers.dart";
import "../../features/auth/application/auth_session_controller.dart";
import "../theme/app_colors.dart";

/// Persistent sidebar shell wrapping every authenticated screen — mirrors the
/// "pulsedashboard" design prototype's nav (Dashboard, Editor Workspace, AI
/// Inspector, New Project, DTF Preparation, Export & Finish).
class AppShell extends ConsumerWidget {
  const AppShell({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = GoRouterState.of(context).matchedLocation;
    final workspace = ref.watch(workspaceContextProvider);
    final userAsync = ref.watch(currentUserProvider);

    void goToWorkspace(String routeName) {
      if (workspace == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Open a project first.")),
        );
        context.goNamed("dashboard");
        return;
      }
      context.goNamed(
        routeName,
        pathParameters: {
          "projectId": workspace.projectId,
          "artworkId": workspace.artworkId
        },
      );
    }

    return Scaffold(
      body: Row(
        children: [
          SizedBox(
            width: 260,
            child: Container(
              decoration: const BoxDecoration(
                color: AppColors.charcoalLight,
                border: Border(right: BorderSide(color: Colors.white10)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const _BrandHeader(),
                  const SizedBox(height: 8),
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      children: [
                        _NavItem(
                          icon: Icons.grid_view_rounded,
                          label: "Dashboard",
                          selected: location.startsWith("/dashboard"),
                          onTap: () => context.goNamed("dashboard"),
                        ),
                        _NavItem(
                          icon: Icons.brush_rounded,
                          label: "Editor Workspace",
                          selected: location.startsWith("/editor"),
                          onTap: () => goToWorkspace("editor"),
                        ),
                        _NavItem(
                          icon: Icons.travel_explore_rounded,
                          label: "AI Inspector",
                          selected: location.startsWith("/inspector"),
                          onTap: () => goToWorkspace("inspector"),
                        ),
                        _NavItem(
                          icon: Icons.add_circle_outline_rounded,
                          label: "New Project",
                          selected: location.startsWith("/upload"),
                          onTap: () => context.goNamed("upload"),
                        ),
                        _NavItem(
                          icon: Icons.print_rounded,
                          label: "DTF Preparation",
                          selected: location.startsWith("/dtf"),
                          onTap: () => goToWorkspace("dtf"),
                        ),
                        _NavItem(
                          icon: Icons.ios_share_rounded,
                          label: "Export & Finish",
                          selected: location.startsWith("/export"),
                          onTap: () => goToWorkspace("export"),
                        ),
                      ],
                    ),
                  ),
                  _AccountFooter(userAsync: userAsync),
                ],
              ),
            ),
          ),
          Expanded(child: child),
        ],
      ),
    );
  }
}

class _BrandHeader extends StatelessWidget {
  const _BrandHeader();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
      child: Row(
        children: [
          Transform.rotate(
            angle: 0.78,
            child: Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: AppColors.pulseYellow,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Text(
            "PULSE",
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.5,
                  color: AppColors.textPrimary,
                ),
          ),
        ],
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Material(
        color: selected ? AppColors.pulseYellow : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Row(
              children: [
                Icon(icon,
                    size: 18,
                    color: selected ? AppColors.onAccent : AppColors.textMuted),
                const SizedBox(width: 12),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: selected ? AppColors.onAccent : AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _AccountFooter extends ConsumerWidget {
  const _AccountFooter({required this.userAsync});

  final AsyncValue<User?> userAsync;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = userAsync.valueOrNull;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: Colors.white10)),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor: AppColors.pulseYellow,
            child: Text(
              user?.initials ?? "..",
              style: const TextStyle(
                color: AppColors.onAccent,
                fontWeight: FontWeight.bold,
                fontSize: 11,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  user?.displayName ?? "Loading...",
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
                const Text(
                  "Free Plan",
                  style: TextStyle(color: AppColors.textMuted, fontSize: 11),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: "Sign out",
            icon:
                const Icon(Icons.logout, size: 18, color: AppColors.textMuted),
            onPressed: () =>
                ref.read(authSessionControllerProvider.notifier).logout(),
          ),
        ],
      ),
    );
  }
}
