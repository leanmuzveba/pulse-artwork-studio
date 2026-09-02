import "package:flutter/material.dart";

/// Placeholder login. Email/password auth is implemented in the next Phase-1 step.
class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Sign in")),
      body: const Center(child: Text("Authentication — coming in Phase 1.")),
    );
  }
}
