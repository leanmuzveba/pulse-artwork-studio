import "package:flutter/material.dart";

/// Placeholder editor. The canvas + tool panels are built out from Phase 2,
/// kept isolated from backend-specific implementation.
class EditorScreen extends StatelessWidget {
  const EditorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Editor")),
      body: const Center(child: Text("Artwork editor — canvas & tools land in Phase 2.")),
    );
  }
}
