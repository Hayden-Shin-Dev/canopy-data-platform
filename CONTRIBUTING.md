# Contributing

## Repository boundaries

- `apps/` — deployable applications
- `ml/` — ML models, inference, evaluation, and shared ML components
- `cloud/` — provider-specific infrastructure and deployment definitions
- `data/` — local data layout and small tracked fixtures; large datasets should not be committed
- `shared/` — cross-component schemas, configuration, and constants
- `tools/` — development and maintenance utilities only
- `tests/` — cross-component integration and end-to-end tests
- `docs/` — architecture and project documentation
- `legacy/` — retained obsolete code; no new development

## Conventions

1. Do not create new top-level directories without team agreement.
2. Prefer task-oriented ML model directories under `ml/models/`.
3. Put reusable ML-only code in `ml/shared/`; put cross-system contracts in root `shared/`.
4. Keep deployable code out of `tools/`.
5. Keep application code independent of Azure where practical; Azure-specific deployment belongs under `cloud/azure/`.
6. Do not commit secrets, large datasets, trained model binaries, caches, or generated build artifacts unless explicitly agreed.
7. Move obsolete implementation to `legacy/` only when its replacement or deprecation is clear.
