import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

/// Placeholder dashboard. Primary actions (New Project, Upload, AI Inspector,
/// Gang Sheet, Recent Projects, Templates, AI Assistant) are built in Phase 1+.
class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text("Pulse Artwork Studio")),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text("Create · Enhance · Print Smarter",
                    style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(
                  "Dashboard scaffold. The upload → analyze → improve → prepare "
                  "→ preview → export workflow is wired up over Phase 1.",
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: () => context.goNamed("editor"),
                  child: const Text("Open editor"),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
