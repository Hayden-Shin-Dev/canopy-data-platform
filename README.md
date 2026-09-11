# Canopy Data Platform

Integrated monorepo for the Canopy product, covering the iPhone application, backend/API, machine-learning models, Azure infrastructure, data assets, and shared contracts.

## Repository structure

```text
apps/       Deployable applications (`ios/`, `api/`)
ml/         Model tasks, shared ML components, and ML pipelines
cloud/      Cloud infrastructure and deployment definitions
  azure/    Azure-specific infrastructure, functions, pipelines, monitoring, and config
data/       Raw, processed, reference, fixture, and cache layout
shared/     Contracts/configuration shared across iOS, API, ML, and cloud components
tools/      Development and maintenance utilities grouped by domain
tests/      Cross-component integration and end-to-end tests
docs/       Architecture and domain documentation
legacy/     Superseded or not-yet-migrated implementation retained for reference
```

## Working convention

- Do not create new top-level directories without team agreement.
- Production application code belongs under `apps/`; helper scripts belong under `tools/`.
- Each ML prediction task gets its own directory under `ml/models/`.
- ML-only reusable code belongs in `ml/shared/`; cross-system contracts belong in root `shared/`.
- Azure-specific deployment and infrastructure belongs under `cloud/azure/`.
- Large datasets, model binaries, caches, secrets, and generated build artifacts should not be committed unless explicitly agreed.

## Original prototype

The repository originally forked from `Hayden-Shin-Dev/canopy-data-platform`. Existing prototype implementation that did not map safely to the new architecture has been retained under `legacy/original-data-platform/` rather than partially moved and potentially broken.

Promote code out of `legacy/` only when its new ownership is clear and imports/tests are updated in the same change.
