<!--
Sync Impact Report:
Version change: 0.0.0 → 1.0.0
Modified principles: N/A (initial creation)
Added sections: All sections
Removed sections: N/A
Templates requiring updates:
  ✅ spec-template.md - Reviewed for alignment
  ✅ plan-template.md - Reviewed for alignment
  ✅ tasks-template.md - Reviewed for alignment
Follow-up TODOs: None
-->

# Analytical Platform Constitution

## Core Principles

### I. Headless Backend-First Architecture

**NON-NEGOTIABLE**: All business logic MUST reside in the backend. Frontend is a thin presentation layer with NO business rules. Backend exposes REST API contracts; frontend consumes via HTTP/JSON. This enables future frontend replacement (React, Vue, native mobile) without backend changes.

**Rationale**: Separates concerns, enables independent scaling, matches thesis requirements for modular architecture, and ensures backend remains the single source of truth for business logic.

### II. Modular Monolith First

**NON-NEGOTIABLE**: Project structure follows modular monolith pattern. Modules (Marketing Analytics, Forecasting, API Gateway) are isolated via clear boundaries with defined interfaces. Microservices are NOT allowed without explicit justification in Complexity Tracking table. All modules share single codebase and deployment unit.

**Rationale**: Graduation project scale does not justify distributed complexity. Modular monolith provides clear boundaries while avoiding microservice overhead (network latency, deployment coordination, eventual consistency issues). Matches thesis requirements and team size.

### III. Supabase Foundation

**NON-NEGOTIABLE**: Supabase is the single source for database, authentication, and real-time subscriptions. Direct database access from backend code MUST use Supabase client or Postgres protocol. Authentication MUST use Supabase Auth (JWT). No external auth providers or separate database services.

**Rationale**: Provides integrated auth, database, and real-time capabilities with minimal operational overhead. Reduces complexity for graduation project while maintaining production-grade features.

### IV. Secure-by-Default

**NON-NEGOTIABLE**: All endpoints require authentication by default. Public endpoints MUST be explicitly documented and justified. Input validation at API boundary. SQL injection prevention via parameterized queries. Secrets management via environment variables (NEVER commit to repo). Rate limiting on all API endpoints. HTTPS enforced in production.

**Rationale**: Security is a thesis requirement. Default-secure approach prevents vulnerabilities. Authentication-first design matches thesis requirements for professional implementation.

### V. Data-Driven KPI Design

**NON-NEGOTIABLE**: All metrics and analytics MUST be derived from explicit data mart definitions. KPI calculations MUST be reproducible and version-controlled. Forecast results MUST be stored with metadata (model version, timestamp, parameters). No ad-hoc calculations in production code.

**Rationale**: Thesis requires marketing analytics module with KPI calculation. Explicit data marts ensure reproducibility and auditability, which is critical for academic work and production systems.

### VI. Test-First for Critical Paths

**NON-NEGOTIABLE**: Tests MUST be written before implementation for: (1) All API endpoints, (2) Data transformation pipelines, (3) Forecast model training/inference, (4) Authentication flows. Tests MUST fail before implementation begins. Test coverage threshold: 80% minimum for backend business logic.

**Rationale**: Ensures system correctness before integration. Critical for data pipelines and ML models where correctness is non-obvious. Supports thesis requirement for professional quality.

### VII. Observability Required

**NON-NEGOTIABLE**: Structured logging for all API requests, data pipeline stages, and model operations. Metrics for API response times, data processing duration, and forecast accuracy. Logs include correlation IDs for request tracing. Monitoring dashboard for critical KPIs and system health.

**Rationale**: Required for thesis (production-minded structure) and essential for debugging data/ML systems. Enables performance analysis and failure diagnosis.

## Security Requirements

### Authentication & Authorization

- All API endpoints require valid JWT from Supabase Auth
- Role-based access control (RBAC) with explicit roles: `admin`, `analyst`, `viewer`
- Token validation on every request
- CORS policies restrict to frontend domain

### Data Protection

- Sensitive data (PII) encrypted at rest and in transit
- API keys and secrets stored in environment variables
- Database credentials via Supabase connection strings
- Data retention policy defined and enforced

### Input Validation

- All API inputs validated at schema level
- SQL queries use parameterized queries (no string concatenation)
- File uploads validated for type, size, and content
- Rate limiting prevents abuse (100 req/min per user)

### Audit Logging

- All user actions logged (who, what, when)
- Failed authentication attempts logged
- Data access logged with user context
- Forecast model predictions logged with model metadata

## Performance Standards

### API Performance

- 95th percentile response time < 200ms for KPI queries
- 95th percentile response time < 500ms for forecast queries
- Support 100 concurrent users without degradation
- Database queries optimized with proper indexing

### Data Processing Performance

- Data ingestion pipeline completes within 5 minutes for 100K records
- KPI calculation completes within 2 minutes
- Forecast model training completes within 10 minutes (for reasonable dataset size)

### Scalability

- Modular design allows horizontal scaling of individual components
- Database connection pooling configured appropriately
- Caching layer for frequently accessed KPIs

## Development Workflow

### Branch Strategy

- `main` branch is production-ready at all times
- Feature branches: `###-feature-name` (e.g., `001-data-ingestion`)
- Hotfix branches: `hotfix-###-description`
- Pull requests required for all changes to main

### Code Review Process

- All changes require at least one approval
- Review checklist includes: constitution compliance, test coverage, security review
- Auto-formatting and linting must pass before merge
- PR description includes: purpose, changes made, testing performed

### Quality Gates

- Test coverage minimum 80% for backend code
- All tests must pass before merge
- Security scan must pass (OWASP ZAP, dependency scanning)
- Documentation updated for all user-facing changes

### Deployment Process

- Staging environment required before production deployment
- Database migrations run as part of deployment
- Rollback procedure documented and tested
- Deployment checklist verified before release

### Documentation Standards

- All API endpoints documented in OpenAPI/Swagger format
- Data model documentation with entity relationships
- Setup instructions in README.md
- Architecture diagrams for major components
- Change log maintained for version history

## Technology Stack Constraints

### Required Technologies

- **Backend**: Python 3.11+ (data/ML ecosystem)
- **Framework**: FastAPI (async, type-safe, OpenAPI integration)
- **Database**: PostgreSQL via Supabase
- **ORM**: SQLAlchemy 2.0+ (async support)
- **Authentication**: Supabase Auth (JWT)
- **ML/Data**: pandas, scikit-learn, numpy
- **Testing**: pytest, pytest-asyncio
- **API Documentation**: Auto-generated via FastAPI
- **Deployment**: Docker containers

### Prohibited Technologies

- No microservice architecture (unless justified)
- No external authentication providers (must use Supabase)
- No NoSQL databases (PostgreSQL required)
- No synchronous ORM (must use async)

### Technology Change Process

Any deviation from required technologies requires:
1. Justification documented in plan.md
2. Added to Complexity Tracking table
3. Approved via code review
4. Updated in constitution with version bump

## Module Boundaries

### Marketing Analytics Module

**Responsibilities**: Data ingestion, preprocessing, KPI calculation, metric storage
**Interfaces**: REST API for KPI queries, data warehouse tables
**Constraints**: No frontend dependencies, no ML model training

### Forecasting Module

**Responsibilities**: Model training, inference, forecast storage, accuracy tracking
**Interfaces**: REST API for forecast queries, model storage, forecast tables
**Constraints**: No frontend dependencies, separate from analytics module

### API Gateway Module

**Responsibilities**: Request routing, authentication, rate limiting, response formatting
**Interfaces**: External REST API, internal module APIs
**Constraints**: No business logic, only orchestration

### Frontend Module (Future)

**Responsibilities**: Data visualization, user interaction, dashboard display
**Interfaces**: REST API consumption from backend
**Constraints**: No business logic, only presentation

## Testing Strategy

### Unit Tests

- Test individual functions and classes in isolation
- Mock external dependencies (database, APIs)
- Focus on business logic validation
- 80% coverage minimum

### Integration Tests

- Test API endpoints with database
- Test data pipeline end-to-end
- Test authentication flows
- Test model inference with stored models

### Contract Tests

- Test API contracts against OpenAPI schema
- Test database schema migrations
- Test module interface contracts

### Performance Tests

- Load test API endpoints (100 concurrent users)
- Test data processing performance
- Test forecast model inference time

## Observability & Monitoring

### Logging

- Structured JSON logging for all components
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include correlation IDs for request tracing
- Log sensitive data only in redacted form

### Metrics

- API response times (p50, p95, p99)
- Request rates per endpoint
- Error rates per endpoint
- Data processing duration
- Forecast model accuracy metrics
- Database query performance

### Alerting

- Alert on error rate > 5%
- Alert on API response time > 500ms (p95)
- Alert on data pipeline failures
- Alert on forecast accuracy degradation > 10%

## Governance

### Amendment Process

- Constitution amendments require documentation in plan.md
- Justification for each change required
- Approval via code review
- Version bump according to semantic versioning:
  - MAJOR: Backward incompatible changes, principle removals
  - MINOR: New principle added, section materially expanded
  - PATCH: Clarifications, wording fixes, non-semantic refinements

### Compliance Review

- All PRs must verify constitution compliance
- Code review checklist includes constitution items
- Complexity must be justified in plan.md
- Violations documented with rationale

### Runtime Guidance

- Use `.specify/memory/constitution.md` as reference during development
- Update constitution when architecture patterns change
- Maintain complexity tracking for all deviations
- Document decisions that affect multiple modules

**Version**: 1.0.0 | **Ratified**: 2026-03-06 | **Last Amended**: 2026-03-06
