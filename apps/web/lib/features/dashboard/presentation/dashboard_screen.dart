import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../app/theme/app_colors.dart";
import "../../../app/widgets/common_widgets.dart";
import "../../../core/models/project.dart";
import "../../artworks/application/artwork_controllers.dart";
import "../../auth/application/auth_session_controller.dart";
import "../../projects/application/projects_controller.dart";
import "../application/dashboard_stats_provider.dart";

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider).valueOrNull;
    final projectsAsync = ref.watch(projectsProvider);
    final statsAsync = ref.watch(dashboardStatsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "Welcome back${user != null ? ', ${user.displayName.split(' ').first}' : ''}",
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      "Ready to prepare some stunning artwork today?",
                      style: TextStyle(color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
              FilledButton.icon(
                onPressed: () => context.goNamed("upload"),
                icon: const Icon(Icons.add, size: 18),
                label: const Text("New Project"),
              ),
            ],
          ),
          const SizedBox(height: 40),
          const _QuickActions(),
          const SizedBox(height: 48),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                  flex: 2,
                  child: _RecentProjects(projectsAsync: projectsAsync)),
              const SizedBox(width: 32),
              Expanded(child: _ProductionOverview(statsAsync: statsAsync)),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuickActions extends StatelessWidget {
  const _QuickActions();

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return Wrap(
          spacing: 20,
          runSpacing: 20,
          children: [
            _ActionTile(
              icon: Icons.upload_rounded,
              iconColor: AppColors.pulseYellow,
              title: "Upload Artwork",
              subtitle: "Quick start from local files",
              onTap: () => context.goNamed("upload"),
            ),
            _ActionTile(
              icon: Icons.verified_user_rounded,
              iconColor: AppColors.info,
              title: "AI Inspector",
              subtitle: "Analyze quality issues",
              onTap: () => context.goNamed("upload"),
            ),
            const _ActionTile(
              icon: Icons.grid_view_rounded,
              iconColor: Colors.purpleAccent,
              title: "Gang Sheet",
              subtitle: "Coming soon",
              enabled: false,
            ),
            const _ActionTile(
              icon: Icons.chat_bubble_outline_rounded,
              iconColor: AppColors.success,
              title: "AI Assistant",
              subtitle: "Coming soon",
              enabled: false,
            ),
          ],
        );
      },
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.enabled = true,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: enabled ? 1 : 0.5,
      child: SizedBox(
        width: 230,
        child: Card(
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: enabled ? onTap : null,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: iconColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, color: iconColor, size: 22),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    title,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(subtitle,
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textMuted)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RecentProjects extends ConsumerWidget {
  const _RecentProjects({required this.projectsAsync});
  final AsyncValue<List<Project>> projectsAsync;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          "Recent Projects",
          style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary),
        ),
        const SizedBox(height: 16),
        projectsAsync.when(
          loading: () => const Padding(
            padding: EdgeInsets.symmetric(vertical: 40),
            child: LoadingPanel(),
          ),
          error: (error, stackTrace) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 24),
            child: ErrorPanel(
              message: "Couldn't load your projects. $error",
              onRetry: () => ref.invalidate(projectsProvider),
            ),
          ),
          data: (projects) {
            if (projects.isEmpty) {
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                    children: [
                      const Icon(Icons.folder_open,
                          color: AppColors.textMuted, size: 32),
                      const SizedBox(height: 12),
                      const Text(
                        "No projects yet",
                        style: TextStyle(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        "Start a new project to upload your first artwork.",
                        style: TextStyle(color: AppColors.textMuted),
                      ),
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: () => context.goNamed("upload"),
                        child: const Text("New Project"),
                      ),
                    ],
                  ),
                ),
              );
            }
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: projects.length,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                mainAxisSpacing: 20,
                crossAxisSpacing: 20,
                childAspectRatio: 0.95,
              ),
              itemBuilder: (context, index) =>
                  _ProjectCard(project: projects[index]),
            );
          },
        ),
      ],
    );
  }
}

class _ProjectCard extends ConsumerWidget {
  const _ProjectCard({required this.project});
  final Project project;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {
          ref.read(workspaceContextProvider.notifier).state = null;
          context.goNamed("project-detail",
              pathParameters: {"projectId": project.id});
        },
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Container(
                color: AppColors.surfaceRaised,
                child: const Center(
                  child: Icon(Icons.image_outlined,
                      color: AppColors.textMuted, size: 36),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    project.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    "Updated ${formatRelativeTime(project.updatedAt)}",
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProductionOverview extends StatelessWidget {
  const _ProductionOverview({required this.statsAsync});
  final AsyncValue<DashboardStats> statsAsync;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "Production Overview",
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 20),
                statsAsync.when(
                  loading: () => const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: LoadingPanel(),
                  ),
                  error: (error, stackTrace) => const Text(
                    "Stats unavailable right now.",
                    style: TextStyle(color: AppColors.textMuted),
                  ),
                  data: (stats) => Column(
                    children: [
                      _StatRow(
                        icon: Icons.check_circle_rounded,
                        color: AppColors.pulseYellow,
                        value: "${stats.readyArtworks}",
                        label: "Ready Artworks",
                      ),
                      const SizedBox(height: 16),
                      _StatRow(
                        icon: Icons.folder_rounded,
                        color: AppColors.info,
                        value: "${stats.totalProjects}",
                        label: "Total Projects",
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppColors.pulseYellow, AppColors.pulseGold],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "UPGRADE TO UNLIMITED",
                style: TextStyle(
                  color: AppColors.onAccent,
                  fontWeight: FontWeight.w900,
                  fontSize: 16,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                "Get high-res vector exports and unlimited AI enhancement tools.",
                style: TextStyle(color: Colors.black54, fontSize: 11),
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.onAccent,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: null,
                  child: const Text("See Plans"),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StatRow extends StatelessWidget {
  const _StatRow({
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final Color color;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
              color: color, borderRadius: BorderRadius.circular(10)),
          child: Icon(icon, color: AppColors.onAccent, size: 20),
        ),
        const SizedBox(width: 14),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              value,
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w900,
                color: AppColors.textPrimary,
              ),
            ),
            Text(
              label.toUpperCase(),
              style: const TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.bold,
                color: AppColors.textMuted,
                letterSpacing: 0.6,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
