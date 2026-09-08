import "package:flutter/material.dart";

import "../theme/app_colors.dart";

/// Centered spinner for an in-progress async section.
class LoadingPanel extends StatelessWidget {
  const LoadingPanel({this.message, super.key});
  final String? message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(color: AppColors.pulseYellow),
          if (message != null) ...[
            const SizedBox(height: 16),
            Text(message!, style: const TextStyle(color: AppColors.textMuted)),
          ],
        ],
      ),
    );
  }
}

/// Inline error state with a retry action.
class ErrorPanel extends StatelessWidget {
  const ErrorPanel({required this.message, this.onRetry, super.key});
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, color: AppColors.critical, size: 32),
          const SizedBox(height: 12),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 360),
            child: Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.textSecondary),
            ),
          ),
          if (onRetry != null) ...[
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onRetry, child: const Text("Retry")),
          ],
        ],
      ),
    );
  }
}

/// Small rounded status/severity chip (CRITICAL / WARNING / NOTICE / etc).
class StatusChip extends StatelessWidget {
  const StatusChip({required this.label, required this.color, super.key});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style:
            TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w800),
      ),
    );
  }
}

String formatRelativeTime(DateTime dateTime) {
  final diff = DateTime.now().toUtc().difference(dateTime.toUtc());
  if (diff.inSeconds < 60) return "just now";
  if (diff.inMinutes < 60) return "${diff.inMinutes}m ago";
  if (diff.inHours < 24) return "${diff.inHours}h ago";
  if (diff.inDays < 7) return "${diff.inDays}d ago";
  return "${dateTime.toLocal().year}-${dateTime.toLocal().month.toString().padLeft(2, '0')}-${dateTime.toLocal().day.toString().padLeft(2, '0')}";
}
