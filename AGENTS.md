# AGENTS.md

## Project

Analytical Platform for an Online Store with Sales Forecasting

## Current Phase

Phase 1 — Repository Foundation

## Core Rules

### Project Management

- Follow the approved Spec Kit constitution, specification, plan, and tasks.
- Implement only the current phase requirements.
- Do not introduce features from future phases.

### Architecture

- Follow a **headless modular monolith** architecture.
- Do not introduce microservices unless explicitly requested.
- Backend-first business logic – all business rules must be implemented in the backend.
- Frontend is presentation layer only – no business logic in React/Next.js.

### Security

- No secrets in frontend or committed files.
- No API keys, database credentials, or secrets in code.
- Use environment variables for all sensitive configuration.
- Respect Supabase security boundaries and avoid exposing privileged keys.

### Development Standards

- Prefer maintainable, thesis-ready code over clever shortcuts.
- Keep changes focused to the requested phase only.
- Keep changes small and reviewable.
- Do not invent new architecture – use the established modular monolith pattern.
- Do not implement extra features outside the requested phase.

### Documentation

- Add concise documentation for every meaningful structural change.
- Keep the repo clean and review-friendly.
- Documentation should be brief but clear for structural decisions.