# Backend

FastAPI backend for the headless modular monolith. This module is the only
authoritative business boundary for frontend and external clients.

**Current status**: Setup and foundational scaffolding implemented in Phase 1.

## Scope in Current Phase

- FastAPI application bootstrap
- Versioned API router skeleton
- Authentication and request-context scaffolding
- Shared error envelope and exception handlers
- Database session factory and repository base abstractions
- Foundational auth and health routes

## Current Structure

```text
backend/
├── pyproject.toml
├── requirements.txt
├── src/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── repositories/
│   ├── schemas/
│   └── security/
└── tests/
    └── integration/
```

## Architectural Rules

- All business logic stays in backend services.
- Frontend consumes backend REST endpoints only.
- Supabase remains the persistence, auth, and storage foundation.
- No feature endpoints beyond foundational auth and health routes are added in
  this phase.

## Next Planned Work

- Data repositories for stores, sales, KPIs, and forecasts
- Auth-aware business services
- Versioned REST endpoints for analytics and forecasting
