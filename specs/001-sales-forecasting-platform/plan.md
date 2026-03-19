# Implementation Plan: Sales Forecasting Platform

**Branch**: `001-sales-forecasting-platform`  
**Date**: 2026-03-11  
**Specification**: [spec.md](./spec.md)  
**Architecture Authority**: [../../docs/ARCHITECTURE_DETAILED.md](../../docs/ARCHITECTURE_DETAILED.md)

## Planning Basis

This plan translates the approved specification and the detailed architecture document into an implementation-ready roadmap for the Analytical Platform for an Online Store with Sales Forecasting. The specification remains the source of scope, user needs, and acceptance intent. The detailed architecture document is the mandatory source of truth for technical boundaries, architectural decisions, security model, module responsibilities, data flow, and operational posture.

The plan is intentionally implementation-oriented. It is written to guide later `/speckit.tasks` output, not to restate theory. Every section below turns an architectural decision into work packages, module responsibilities, interfaces, sequencing, and phase completion criteria. The plan assumes a small graduation-project team, prioritizes a headless modular monolith, and keeps all business logic in the backend. It also assumes that the repository is still in Phase 1 today, so the plan defines the approved MVP target state and the sequence for reaching it.

## Locked Decisions

The following decisions are fixed by the architecture and must not be weakened by future task breakdowns:

- Headless modular monolith is the required system style.
- FastAPI is the only authoritative REST API boundary.
- Frontend is a thin presentation client and must not contain business logic.
- Supabase is the foundation for Postgres, Auth, and Storage.
- Schema exposure must remain controlled and minimal.
- Backend authorization plus database RLS must be used as defense in depth.
- ML training is offline; user-facing forecast delivery is based on persisted, governed outputs.
- No microservices are permitted unless later justified by a separate architecture decision.

## Technical Context

| Area | Planned choice |
|---|---|
| Primary language | Python 3.11+ for backend, data, and ML |
| Frontend language | TypeScript 5.x |
| Backend framework | FastAPI |
| Database and auth | Supabase Postgres and Supabase Auth |
| Storage | Supabase Storage for model artifacts and large derived files |
| Data tooling | pandas-based pipelines with explicit validation steps |
| ML tooling | Baseline statistical method plus Prophet and/or XGBoost candidate models |
| Frontend | Next.js dashboard consuming backend REST API |
| Testing | pytest, API integration tests, schema and policy tests, frontend UI and contract tests |
| Deployment style | Single modular monolith deployment with supporting offline jobs |
| Scale target | Full Rossmann dataset, approximately 1M+ sales rows and 1,115 stores |

## Constitution Check

| Principle | Status | Plan consequence |
|---|---|---|
| Headless Backend-First Architecture | Pass | All business rules, KPI semantics, access rules, and forecast-serving logic stay in backend services |
| Modular Monolith First | Pass | One codebase and one application boundary with explicit module interfaces; no service decomposition |
| Supabase Foundation | Pass | Postgres, Auth, RLS, and Storage all remain under Supabase |
| Secure-by-Default | Pass | Auth required by default, controlled schemas, validated inputs, least-privilege secrets |
| Data-Driven KPI Design | Pass | KPI marts and definitions are explicit, reproducible, and versioned through migrations and pipelines |
| Test-First for Critical Paths | Pass | Tasks must start with tests for API, data transformations, auth flows, and forecast logic |
| Observability Required | Pass | Structured logs, health checks, run metadata, and demo-readiness visibility are mandatory |

## 1. Repository Structure

The repository structure should remain modular and map cleanly to the architecture layers. The target implementation layout is below. Individual filenames may evolve slightly, but the module boundaries and responsibility split must stay stable.

```text
DIPLOMA/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   └── v1/                # auth, stores, sales, kpis, forecasts, admin, health
│   │   ├── core/                  # configuration, application settings, dependency wiring
│   │   ├── security/              # JWT validation, role extraction, authorization helpers
│   │   ├── services/              # business logic and orchestration
│   │   ├── repositories/          # database access abstractions
│   │   ├── schemas/               # request and response models
│   │   ├── db/                    # database session and query integration
│   │   └── observability/         # logging, correlation IDs, health helpers
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── contract/
├── data/
│   ├── src/
│   │   ├── ingest/                # raw dataset acquisition and load staging
│   │   ├── quality/               # validation and profiling rules
│   │   ├── transform/             # cleaning and operational data shaping
│   │   ├── marts/                 # KPI computation and refresh flows
│   │   ├── load/                  # writes to Supabase/Postgres
│   │   └── runs/                  # run metadata and pipeline orchestration
│   └── tests/
├── ml/
│   ├── src/
│   │   ├── features/              # feature preparation
│   │   ├── training/              # baseline and candidate model training
│   │   ├── evaluation/            # holdout scoring and comparison
│   │   ├── publishing/            # publish approved forecasts and metadata
│   │   └── inference/             # controlled retrieval-oriented inference helpers
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                   # routes and auth-aware pages
│   │   ├── components/            # reusable UI components
│   │   ├── features/              # dashboard, analytics, forecasts, admin views
│   │   └── lib/                   # API client and presentation-only helpers
│   └── tests/
├── supabase/
│   ├── migrations/                # schema and policy evolution
│   ├── policies/                  # documented RLS policy definitions if separated
│   └── seed/                      # non-secret local/demo seed data
├── infra/
│   ├── docker/
│   ├── github/
│   └── deployment/
├── docs/
├── specs/
└── README.md
```

This structure keeps runtime concerns in `backend`, `data`, `ml`, `frontend`, `supabase`, and `infra`, while `docs` and `specs` remain documentation and planning sources rather than runtime modules. `/speckit.tasks` should preserve this structure when generating tasks and avoid assigning cross-cutting work to vague “miscellaneous” buckets.

## 2. Module Responsibilities

Each module must own a specific part of the system and avoid absorbing responsibilities from neighboring modules.

| Module | Owns | Interfaces | Must not own |
|---|---|---|---|
| `frontend` | Rendering dashboards, forms, filters, auth-aware navigation, data visualization | Calls backend REST API only | KPI computation, store-access rules, forecast calculation, privileged secrets |
| `backend` | REST API, request validation, business logic, orchestration, authorization checks, response contracts | Receives HTTP requests, reads from Supabase-backed data via repositories, returns JSON responses | Offline ETL, model training, direct UI rendering concerns |
| `data` | Raw dataset ingestion, validation, preprocessing, curated loading, KPI mart refresh orchestration | Reads raw files, writes cleaned and analytical structures to Supabase | Frontend contracts, user-facing auth logic, ad hoc API behavior |
| `ml` | Feature creation, baseline and candidate model training, evaluation, forecast publishing, artifact metadata | Reads prepared datasets, writes forecasts and model metadata to Supabase | Direct frontend delivery, uncontrolled experiments in production path |
| `supabase` | Schema migrations, RLS, storage conventions, DB-side support objects | Serves backend, data, and ML modules | Application business orchestration or frontend-driven privileged access |
| `infra` | Environment assets, CI jobs, local orchestration, deployment support | Supports all runtime modules | Business rules or KPI logic |
| `docs` | Architecture, operations, deployment and rationale | Supports implementation and defense | Hidden source of runtime truth |
| `specs` | Scope, requirements, contracts, planning artifacts | Drives planning and tasking | Runtime configuration or undocumented feature drift |

The implementation plan must keep the module interfaces narrow. For example, the backend may query analytical views, but it must not ask the frontend to compute KPI rollups. The ML module may publish persisted forecasts, but it must not expose an independent external API. The `supabase` module may host RLS policies and schema support, but it must not become a substitute for backend business logic.

## 3. Environment and Configuration Strategy

The system should support local development and one controlled deployed environment suitable for demo or production-like validation. A separate staging environment is optional for the MVP, but if a true production deployment is later introduced, a pre-production validation environment should be used before release. The plan does not assume a large multi-environment platform setup.

Configuration should be environment-based, documented, and module-owned:

- Root-level `.env.example` documents required variables for all modules.
- Real secrets must never be committed.
- Frontend receives only public-safe configuration such as backend base URL and public auth settings.
- Backend receives API, database, auth-validation, and logging configuration.
- Data and ML jobs receive only the privileged secrets required for ingestion, artifact publication, and controlled writes.
- Supabase-specific operational variables remain limited to trusted modules.

Configuration groups should be defined as follows:

| Group | Used by | Examples of contents |
|---|---|---|
| Public client config | `frontend` | Public backend URL, non-secret auth URL, non-sensitive feature flags |
| API runtime config | `backend` | App host/port, JWT audience/issuer, DB connection, log level |
| Data pipeline config | `data` | Dataset paths, run modes, batch sizes, quality thresholds |
| ML runtime config | `ml` | Feature window settings, horizon length, artifact paths, evaluation thresholds |
| Supabase admin config | `backend`, `data`, `ml`, `infra` | Service-role key, storage bucket names, migration targets |

Ownership rules are critical. The frontend must not receive service-role secrets. The backend must not rely on undeclared local-only configuration. Data and ML modules must not invent their own undocumented secret channels. `/speckit.tasks` should therefore create configuration tasks by module and environment group rather than one generic “set up env vars” task.

## 4. Data Ingestion and Preprocessing Flow

The data flow starts with the Rossmann source files. `train.csv` and `store.csv` are mandatory source inputs. `test.csv` and related reference files may be retained as auxiliary data for benchmark or demonstration support, but they do not replace the core operational input set.

The ingestion pipeline should be implemented in the following sequence:

1. Read source files into a raw pipeline context without treating them as trusted data.
2. Validate structure, required columns, data types, date parseability, duplicate candidates, and basic referential integrity.
3. Apply quality rules for nulls, logical inconsistencies, outliers, and invalid categorical values.
4. Produce a validation report or run summary that clearly states pass, warn, or fail conditions.
5. Normalize and clean accepted records into operationally consistent representations.
6. Load cleaned entities into controlled relational tables in restricted schemas.
7. Record ingestion run metadata, source references, row counts, and failure details.

The pipeline should write raw and staging work products only to restricted areas. Raw ingestion state, validation results, and processing runs belong in the `internal` schema or controlled file paths. Cleaned operational entities should then be loaded into stable relational structures that downstream KPI and ML processes can trust. Failed validations should not be silently dropped; they must be surfaced in run metadata and prevent downstream publication when they violate minimum data-quality thresholds.

Implementation tasks for this section should be broken down into:

- raw source readers
- validation rules
- cleaning and normalization rules
- operational table loaders
- run metadata tracking
- repeatable local execution path

## 5. KPI Computation Flow

KPI computation begins only after operational data is validated and loaded. The platform must not compute user-visible KPIs from ad hoc frontend logic or directly from raw files. KPI definitions belong to the backend and analytical layer, and their data preparation belongs to the data module and the database structures it maintains.

The KPI flow should be:

1. Read cleaned operational sales and store data from controlled base tables.
2. Build daily analytical facts first, because they form the foundation for higher-level aggregates.
3. Derive weekly and monthly marts from stable daily structures rather than repeatedly aggregating raw-level data.
4. Build store-comparison assets from the same approved KPI definitions.
5. Publish marts and read-oriented views in the `analytics` schema.
6. Expose KPIs only through backend endpoints and documented response models.

The initial KPI layer should prioritize the metrics already present in the specification: daily sales, weekly averages, year-over-year growth, promotion impact, and holiday effects. The plan should treat daily, weekly, monthly, and comparison structures as separate deliverables because they have different validation and performance requirements. The KPI path must also include refresh rules so that tasks can define how marts are recalculated after ingestion or backfill operations.

Task sequencing for `/speckit.tasks` should separate:

- KPI definition approval
- daily mart build
- weekly and monthly aggregation build
- comparison mart build
- validation against expected counts and metric spot checks
- API-facing read model verification

## 6. ML Training, Evaluation, and Inference Flow

The ML flow must preserve the distinction between experimentation, approved training, and user-facing serving. The plan therefore uses three explicit stages: feature preparation, model evaluation and selection, and forecast publishing.

The approved ML path is:

1. Generate features from cleaned historical data and store attributes.
2. Train a baseline model first for fallback behavior and academic comparison.
3. Train stronger candidate models, specifically Prophet and/or XGBoost-based approaches, using the same governed feature inputs.
4. Evaluate all candidates using a time-aware holdout strategy and record MAPE, RMSE, and MAE.
5. Select or approve the active model based on recorded evidence, not informal preference.
6. Publish forecast results, confidence context, model metadata, and artifact references into controlled persistence.
7. Serve forecast results through the backend from persisted outputs and metadata.

The architecture does not allow ordinary user requests to trigger full retraining. Forecast generation for user-facing flows should rely on previously trained artifacts and stored forecast outputs whenever possible. If a bounded “generate latest forecast” operation is later implemented, it must remain backend-controlled, auditable, and separate from research experimentation.

Implementation tasks should be grouped into:

- feature engineering
- baseline model training
- candidate model training
- evaluation and model comparison
- artifact and metadata publishing
- forecast result publication
- backend retrieval integration

The `ml` schema should store structured metadata such as training run identifiers, dataset references, feature version references, metric outputs, model version labels, and forecast publication records. Supabase Storage should hold serialized artifacts or larger generated files. `/speckit.tasks` should treat metadata persistence and artifact storage as distinct tasks.

## 7. FastAPI REST API Structure

The backend API is the only authoritative online interface for the platform. All protected business data must flow through `/api/v1`, and all endpoint groups must map to explicit business domains. The required groups are:

- `/api/v1/auth`
- `/api/v1/stores`
- `/api/v1/sales`
- `/api/v1/kpis`
- `/api/v1/forecasts`
- `/api/v1/admin`
- `/api/v1/health`

The API implementation should follow these rules:

- Every endpoint uses explicit request and response schemas.
- Validation happens at the API boundary for dates, store IDs, aggregations, filters, pagination, and role-sensitive operations.
- Error responses follow one consistent envelope.
- Pagination is mandatory where result sets can grow large.
- Admin routes are isolated from user-facing routes and use stricter authorization requirements.
- Health endpoints include at least liveness and readiness behavior.

Endpoint grouping and module ownership should be planned as follows:

| Endpoint group | Core responsibility | Primary backend collaborators |
|---|---|---|
| `auth` | current-user context, auth-aware session support, role reflection | security helpers, user repository |
| `stores` | store lookup and authorized store access | store service, store repository |
| `sales` | historical sales retrieval with filters and aggregation choices | sales service, analytical repositories |
| `kpis` | KPI retrieval from governed marts and views | KPI service, analytics repository |
| `forecasts` | forecast retrieval, forecast metadata, bounded generation or refresh triggers if approved | forecast service, ML metadata repository |
| `admin` | user access management, refresh control, restricted operational actions | admin service, audit logging, privileged repositories |
| `health` | liveness, readiness, dependency checks | observability helpers, DB connectivity |

`/speckit.tasks` should generate backend work by endpoint group plus shared backend infrastructure tasks for config, error handling, auth middleware, repository interfaces, and OpenAPI accuracy.

## 8. Supabase Integration Boundaries

Supabase is the single managed foundation for database, authentication, and storage, but it is not the application layer. The plan must preserve the schema and access boundaries defined in the architecture.

The controlled schema model is:

| Schema | Purpose | Allowed writers | Allowed readers |
|---|---|---|---|
| `auth` | Supabase-managed identity data | Supabase Auth flows | Backend security integration only |
| `internal` | staging data, ingestion runs, pipeline metadata, restricted operational structures | data jobs, trusted backend/admin flows | backend, data, and ML modules only |
| `analytics` | KPI marts, comparison views, read-optimized analytical assets | data jobs and controlled refresh paths | backend repositories |
| `ml` | training metadata, evaluation results, forecast outputs, active model records | ML jobs and controlled backend/admin flows | backend repositories, ML module |
| `public` | minimal, tightly controlled API-facing support objects only if needed | migrations and trusted server-side modules | backend only by default |

The backend may use Postgres protocol access or Supabase-compatible clients, but the frontend must not receive privileged data access paths. Frontend auth may use safe client-side auth flows as needed, but all protected data access still routes through the backend. Storage usage follows the same rule: only trusted backend, data, or ML modules manage artifacts and privileged storage writes.

Required Supabase task groups are:

- schema creation and migration discipline
- RLS policy design and tests
- role and store-access support tables
- analytical schema population paths
- ML metadata and artifact reference support
- storage bucket conventions for artifacts

## 9. Authentication and Authorization Strategy

Authentication is handled by Supabase Auth, and authorization is enforced in two layers: backend authorization logic and database-level row-level security. Both are required. RLS alone is not sufficient because endpoint-level behavior, admin capabilities, and business-specific error handling belong in the backend.

The canonical application roles for implementation planning are:

- `admin`
- `store_manager`
- `marketing_manager`
- `data_analyst`
- `academic_demo`

The `academic_demo` role is an authenticated, read-only role with curated access. It exists specifically to support safe thesis demonstrations without granting privileged or broad administrative capabilities. If a later implementation prefers to map roles differently in code, the effective permissions must still preserve this role’s read-only and restricted nature.

Authorization behavior should include:

- JWT validation on every protected request
- current user resolution in backend dependencies or middleware
- store-access enforcement through a user-to-store mapping
- role checks for admin-only operations
- RLS policies that prevent row leakage even if a backend query is mis-scoped
- audit logging for access failures and admin actions

`/speckit.tasks` should split auth work into:

- Supabase Auth integration
- JWT verification and security middleware
- role mapping and user context extraction
- store-access model and policy setup
- RLS tests
- audit logging for sensitive flows

## 10. Testing Strategy by Layer

Testing should mirror the architecture, not merely the file structure. Each layer needs different tests because each layer fails in different ways.

| Layer | Primary tests | Focus |
|---|---|---|
| Backend domain and services | unit tests | business rules, access checks, KPI semantics, forecast-serving logic |
| FastAPI endpoints | integration and contract tests | request validation, response shapes, status codes, auth enforcement |
| Data pipelines | unit and integration tests | validation rules, transformation correctness, row counts, failure handling |
| KPI marts | data validation and query tests | aggregation accuracy, refresh logic, analytical consistency |
| ML workflows | unit, evaluation, and regression tests | feature generation, baseline fallback, metric calculation, publish logic |
| Supabase schema and policies | migration tests and RLS tests | schema correctness, permissions, access isolation |
| Frontend | component, route, and API contract tests | rendering, authorized page behavior, correct API usage, no embedded business logic |
| Cross-system | end-to-end smoke tests | login, KPI retrieval, forecast retrieval, error visibility |

The task plan must include fixtures for representative Rossmann subsets, seeded user/store-access test data, and stable test cases for model evaluation and fallback behavior. Critical-path tests should be introduced before or alongside implementation, especially for auth, ingestion validation, KPI definitions, and forecast-serving rules.

## 11. Observability and Operational Readiness

Observability is a mandatory delivery stream, not a late hardening add-on. The implementation plan must deliver visibility for the API path, the ingestion path, and the ML publication path.

Required observability elements are:

- structured backend logs with correlation IDs
- ingestion run logs with run identifiers, row counts, and validation outcomes
- ML run logs with training identifiers, evaluation summaries, and publication events
- liveness and readiness health endpoints
- freshness indicators for latest ingestion, latest KPI refresh, and latest forecast publication
- audit-relevant logs for admin actions and authorization failures

Operational readiness before demo or deployment means the team can answer the following questions quickly:

- Is the API alive and ready?
- Can the backend reach Supabase?
- When did the last successful ingestion run finish?
- When were KPI marts last refreshed?
- Which model version produced the current published forecasts?
- Are authentication or authorization failures occurring unexpectedly?

`/speckit.tasks` should therefore include separate tasks for shared logging infrastructure, run metadata persistence, health endpoints, and demo-readiness validation rather than hiding them inside feature tasks.

## 12. Phased Roadmap

The implementation roadmap should follow the architectural evolution already defined in the detailed architecture document.

| Phase | Goal | Main outputs | Depends on |
|---|---|---|---|
| 1. Foundation | Establish repo, docs, planning, and baseline conventions | stable module structure, architecture and plan artifacts, env templates | none |
| 2. Ingestion | Build trusted operational data foundation | ingestion pipeline, validation rules, cleaned base tables, run metadata | foundation |
| 3. KPI Layer | Build read-optimized analytical structures | daily, weekly, monthly, and comparison marts plus validation checks | ingestion |
| 4. Forecasting Layer | Build reproducible forecasting workflow | feature generation, baseline model, candidate models, evaluation records, forecast publication | ingestion, KPI layer |
| 5. API Layer | Expose business capabilities through FastAPI | `/api/v1` routes, schemas, auth integration, health endpoints, admin boundaries | ingestion, KPI layer, forecasting metadata |
| 6. Frontend Integration | Deliver thin dashboard client | auth-aware pages, analytics views, forecast views, API client integration | API layer |
| 7. Hardening and Demo Readiness | Make the system observable, testable, and defensible | structured logging, operational checks, seeded demo data, end-to-end verification | all previous phases |

Tasks should be generated phase-first, then module-specific within each phase. This avoids building frontend pages before stable API contracts or forecast pages before governed forecast outputs exist.

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Data quality issues weaken KPI and forecast credibility | High | Enforce validation gates, run metadata, and failure visibility before downstream publication |
| Forecast model quality is below target | High | Keep baseline model, record evaluation evidence, publish accuracy context, and allow fallback serving |
| Frontend or database layer starts absorbing business logic | High | Keep backend-first tasks explicit, review task boundaries against architecture, test backend rules directly |
| Schema exposure becomes too broad | High | Implement schema-specific tasks, review RLS and grants, keep frontend behind backend API |
| Privileged key leakage | High | Strict environment ownership, no secrets in frontend, least-privilege runtime separation |
| Plan grows beyond thesis timeline | High | Sequence phases tightly, keep out-of-scope features deferred, prioritize core analytical and forecast path first |
| Observability is postponed until the end | Medium | Add logging, health, and run metadata tasks in each phase instead of one final cleanup bucket |
| API contracts drift from frontend expectations | Medium | Maintain request/response schemas and contract tests from the start |

These risks should be converted into explicit task safeguards. For example, a risk about schema exposure should not remain only in prose; it should appear as migration review, RLS testing, and backend access tasks.

## 14. Definition of Done per Phase

Each phase is complete only when its deliverables exist, its acceptance checks pass, and its outputs are ready to support the next phase.

### Phase 1: Foundation

- Repository structure matches the approved modular monolith shape.
- Architecture, plan, spec, data model, and contract artifacts are consistent.
- Environment variable templates and module ownership rules are documented.
- No architectural contradictions remain in planning documents.

### Phase 2: Ingestion

- Rossmann source files can be loaded repeatably in local development.
- Validation rules detect structural and logical data issues.
- Cleaned operational data is written to controlled schemas.
- Ingestion run metadata and failure reporting exist.

### Phase 3: KPI Layer

- Daily, weekly, monthly, and comparison KPI assets are built from cleaned data.
- KPI calculations match approved definitions and spot-check expectations.
- Analytical outputs are queryable through controlled read paths.
- Refresh behavior is documented and testable.

### Phase 4: Forecasting Layer

- Baseline and candidate models can be trained from governed inputs.
- Evaluation results are recorded with model and dataset references.
- Forecast outputs and metadata are persisted in controlled storage and schemas.
- Fallback behavior exists for low-data or failed-model scenarios.

### Phase 5: API Layer

- `/api/v1` endpoint groups exist with validated schemas and consistent errors.
- Authentication and authorization are enforced on protected routes.
- KPI and forecast retrieval work through backend services only.
- Health endpoints provide liveness and readiness information.

### Phase 6: Frontend Integration

- Users can log in and reach auth-aware views appropriate to their role.
- Dashboard pages render historical analytics from backend APIs.
- Forecast pages render persisted forecast results and confidence context.
- Frontend contains no authoritative business logic or privileged data access.

### Phase 7: Hardening and Demo Readiness

- Structured logs, run metadata, and health visibility are active.
- End-to-end smoke tests cover login, KPI retrieval, and forecast retrieval.
- Demo user access is restricted and read-only.
- Documentation is sufficient to explain architecture, data flow, security, and operations during thesis defense.

## Task Extraction Guidance for `/speckit.tasks`

The next task breakdown should follow four ordering rules:

1. Create shared infrastructure and schema tasks before feature tasks that depend on them.
2. Keep backend, data, ML, and frontend work separated by module and phase.
3. Add test tasks alongside each implementation stream instead of as one final testing block.
4. Include observability, policy, and documentation tasks inside each phase, not only at the end.

The task model should therefore be organized first by phase, then by module, then by validation or acceptance artifact. That structure is the safest way to preserve the approved architecture while keeping the work executable for a small graduation-project team.
