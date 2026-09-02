# Packages

Shared, reusable libraries consumed by the apps and services.

| Package | Purpose |
|---------|---------|
| `design_system/` | Flutter design tokens, theme, and shared widgets (brand: yellow / grey / black) |
| `image_models/` | Shared image/artwork domain models and metadata types |
| `api_contracts/` | Versioned request/response contracts shared across client and server |

API contracts are versioned; breaking changes get a new version rather than
mutating an existing one.
