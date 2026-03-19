# Infrastructure

Infrastructure assets for local orchestration, CI validation, and later
deployment hardening.

**Current status**: Phase 1 setup and foundational scaffolding implemented.

## Current Assets

- Docker Compose files for backend, frontend, and local database scaffolding
- GitHub Actions workflows for CI validation and manual deployment placeholder

## Responsibility Boundary

- Support runtime modules without containing business logic
- Keep environment orchestration and automation separate from backend, data,
  ML, and frontend feature code
- Preserve the single modular monolith deployment direction

## Next Planned Work

- Expand CI checks as modules gain executable features
- Add deployment-specific scripts and documentation in later phases
- Introduce environment-specific operational checks during hardening
