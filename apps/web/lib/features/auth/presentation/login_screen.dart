import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../app/theme/app_colors.dart";
import "../../../core/api/api_exception.dart";
import "../application/auth_session_controller.dart";

enum AuthFormMode { login, register }

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({required this.mode, super.key});
  final AuthFormMode mode;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  bool _submitting = false;
  String? _error;

  bool get _isRegister => widget.mode == AuthFormMode.register;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final controller = ref.read(authSessionControllerProvider.notifier);
      if (_isRegister) {
        await controller.register(
          email: _emailController.text.trim(),
          password: _passwordController.text,
          fullName: _nameController.text.trim().isEmpty
              ? null
              : _nameController.text.trim(),
        );
      } else {
        await controller.login(
          email: _emailController.text.trim(),
          password: _passwordController.text,
        );
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.charcoalDark,
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(32),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
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
                          const Text(
                            "PULSE",
                            style: TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -0.5,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),
                      Text(
                        _isRegister ? "Create your account" : "Sign in",
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        "AI-powered artwork preparation for DTF printing.",
                        style: TextStyle(color: AppColors.textMuted),
                      ),
                      const SizedBox(height: 24),
                      if (_isRegister) ...[
                        TextFormField(
                          controller: _nameController,
                          style: const TextStyle(color: AppColors.textPrimary),
                          decoration: const InputDecoration(
                              labelText: "Full name (optional)"),
                        ),
                        const SizedBox(height: 16),
                      ],
                      TextFormField(
                        controller: _emailController,
                        style: const TextStyle(color: AppColors.textPrimary),
                        keyboardType: TextInputType.emailAddress,
                        decoration: const InputDecoration(labelText: "Email"),
                        validator: (value) =>
                            (value == null || !value.contains("@"))
                                ? "Enter a valid email"
                                : null,
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _passwordController,
                        style: const TextStyle(color: AppColors.textPrimary),
                        obscureText: true,
                        decoration:
                            const InputDecoration(labelText: "Password"),
                        validator: (value) =>
                            (value == null || value.length < 8)
                                ? "At least 8 characters"
                                : null,
                        onFieldSubmitted: (_) => _submit(),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            const Icon(
                              Icons.error_outline,
                              color: AppColors.critical,
                              size: 16,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _error!,
                                style: const TextStyle(
                                    color: AppColors.critical, fontSize: 13),
                              ),
                            ),
                          ],
                        ),
                      ],
                      const SizedBox(height: 24),
                      FilledButton(
                        onPressed: _submitting ? null : _submit,
                        child: _submitting
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: AppColors.onAccent,
                                ),
                              )
                            : Text(_isRegister ? "Create account" : "Sign in"),
                      ),
                      const SizedBox(height: 16),
                      TextButton(
                        onPressed: () => context.goNamed(
                          _isRegister ? "login" : "register",
                        ),
                        child: Text(
                          _isRegister
                              ? "Already have an account? Sign in"
                              : "New to Pulse? Create an account",
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
