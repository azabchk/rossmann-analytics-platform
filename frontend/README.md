# Frontend

Thin presentation client for the analytical platform. It renders auth-aware
pages and consumes backend REST endpoints only.

**Current status**: Setup and foundational shell implemented in Phase 1.

## Scope in Current Phase

- Next.js project metadata
- Root layout and login shell
- Base API client utilities
- Session helper placeholder for future Supabase-authenticated flows

## Architectural Rules

- No business logic in frontend code
- No direct privileged Supabase data access
- No KPI or forecast calculation in the UI
- All protected business data flows through FastAPI

## Current Structure

```text
frontend/
├── package.json
├── tsconfig.json
├── next.config.ts
└── src/
    ├── app/
    └── lib/
```

## Next Planned Work

- Dashboard routes
- Analytics and forecast pages
- Chart components and auth-aware navigation
