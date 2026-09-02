# Pulse Web (Flutter)

The responsive web client — dashboard, project management, the artwork editor,
and API communication.

## Prerequisites

- Flutter SDK (stable, Dart >= 3.4)

## Run

```bash
cd apps/web
flutter pub get
flutter run -d chrome        # dev
flutter build web            # production bundle -> build/web
```

## Test / analyze

```bash
flutter analyze
flutter test
```

## Layout (feature-first)

```
lib/
  main.dart                     entrypoint (ProviderScope)
  app/
    app.dart                    MaterialApp.router
    router/app_router.dart      go_router route table
    theme/                      brand palette (yellow/grey/black) + themes
  features/
    auth/ dashboard/ editor/    one folder per feature (presentation/…)
  core/  shared/                cross-cutting utilities & widgets
```

State management uses Riverpod. The editor is kept isolated from backend
specifics so processing providers can change without touching the UI.
