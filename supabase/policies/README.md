# Supabase Policy Baseline

This directory documents the policy expectations for the platform.

## Current Phase

Phase 1 introduces only the baseline policy posture:

- `internal`, `analytics`, and `ml` are restricted schemas
- direct client access is not assumed or required
- row-level security is enabled on core internal tables
- policies are minimal and scoped to authenticated self-access or store-scoped
  reads

## Locked Rules

- Frontend does not receive privileged database access
- Backend remains the primary business boundary
- Schema exposure stays controlled and minimal
- Future policies must extend this baseline rather than weaken it
