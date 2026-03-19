# Tasks: Sales Forecasting Platform

**Input**: Design documents from `/specs/001-sales-forecasting-platform/`  
**Required Sources**: `spec.md`, `plan.md`, `../../docs/ARCHITECTURE_DETAILED.md`  
**Supporting Sources**: `research.md`, `data-model.md`, `contracts/api-spec.json`, `quickstart.md`

**Tests**: Included. The specification, implementation plan, and constitution require test coverage for critical API, data, auth, and ML paths.  
**Organization**: Tasks are grouped by phase and user story, with dependency-driven ordering that preserves architecture boundaries.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel when dependencies are satisfied and files do not conflict
- **[Story]**: Maps to the user story from `spec.md`
- All tasks include exact target file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish repository structure, project metadata, and local execution scaffolding

- [ ] T001 Create module skeleton markers in `backend/src/__init__.py`, `data/src/__init__.py`, `ml/src/__init__.py`, `frontend/src/app/page.tsx`, and `supabase/migrations/.gitkeep`
- [ ] T002 Create root and module environment documentation in `.env.example`, `backend/README.md`, `data/README.md`, `ml/README.md`, and `frontend/README.md`
- [ ] T003 [P] Initialize backend project metadata in `backend/pyproject.toml` and `backend/requirements.txt`
- [ ] T004 [P] Initialize frontend project metadata in `frontend/package.json`, `frontend/tsconfig.json`, and `frontend/next.config.ts`
- [ ] T005 [P] Create local orchestration assets in `infra/docker/docker-compose.yml` and `infra/docker/local-supabase.yml`
- [ ] T006 Create CI workflow skeleton for lint, test, and docs validation in `.github/workflows/ci.yml` and `.github/workflows/deploy.yml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the shared infrastructure that blocks all later implementation

**⚠️ CRITICAL**: No user story work should start until this phase is complete

- [ ] T007 Create baseline schema migration for `internal`, `analytics`, `ml`, and minimal `public` boundaries in `supabase/migrations/20260311_001_base_schemas.sql`
- [ ] T008 [P] Create core operational and access-control tables migration in `supabase/migrations/20260311_002_core_entities.sql`
- [ ] T009 [P] Create RLS and controlled schema exposure baseline in `supabase/migrations/20260311_003_rls_baseline.sql` and `supabase/policies/README.md`
- [ ] T010 [P] Create backend application bootstrap and router wiring in `backend/src/main.py` and `backend/src/api/router.py`
- [ ] T011 [P] Create backend configuration and dependency wiring in `backend/src/core/config.py` and `backend/src/core/dependencies.py`
- [ ] T012 [P] Create backend JWT validation and request-context helpers in `backend/src/security/jwt.py`, `backend/src/security/context.py`, and `backend/src/security/dependencies.py`
- [ ] T013 [P] Create backend DB session and repository base abstractions in `backend/src/db/session.py` and `backend/src/repositories/base.py`
- [ ] T014 [P] Create shared error envelope and exception handling in `backend/src/schemas/common.py` and `backend/src/core/errors.py`
- [ ] T015 Create auth and health route skeletons in `backend/src/api/v1/auth.py` and `backend/src/api/v1/health.py`
- [ ] T016 [P] Create frontend auth shell, protected layout, and base API client in `frontend/src/app/layout.tsx`, `frontend/src/app/login/page.tsx`, `frontend/src/lib/api/base-client.ts`, and `frontend/src/lib/auth/session.ts`
- [ ] T017 Create foundational backend and policy test harness in `backend/tests/conftest.py`, `backend/tests/integration/test_auth_baseline.py`, and `backend/tests/integration/test_rls_baseline.py`
- [ ] T018 Create non-secret seed conventions for admin, analyst, and demo users in `supabase/seed/roles.sql` and `supabase/seed/demo_users.sql`

**Checkpoint**: Core architecture boundaries, auth baseline, and Supabase foundations are in place

---

## Phase 3: User Story 5 - Automated Data Preparation (Priority: P2, scheduled early due to dependencies)

**Goal**: Build the trusted ingestion and preprocessing pipeline that feeds all later analytics and forecasting work

**Independent Test**: Provide Rossmann source files, run the ingestion flow, verify validated and cleaned data is loaded to controlled tables, and confirm invalid inputs produce a visible error report and failed run state

### Tests for User Story 5

- [ ] T019 [P] [US5] Add successful ingestion integration test in `data/tests/integration/test_ingestion_success.py`
- [ ] T020 [P] [US5] Add validation-failure coverage for malformed input files in `data/tests/integration/test_ingestion_failures.py`

### Implementation for User Story 5

- [ ] T021 [P] [US5] Create Rossmann raw dataset readers in `data/src/ingest/read_train_csv.py` and `data/src/ingest/read_store_csv.py`
- [ ] T022 [P] [US5] Create structural and logical validation rules in `data/src/quality/validate_sales_records.py` and `data/src/quality/validate_store_records.py`
- [ ] T023 [US5] Implement validation reporting and run-state models in `data/src/runs/models.py` and `data/src/runs/reporting.py`
- [ ] T024 [US5] Implement cleaning and normalization flow in `data/src/transform/normalize_sales.py` and `data/src/transform/normalize_stores.py`
- [ ] T025 [US5] Implement operational data loaders for staging and base tables in `data/src/load/load_operational_tables.py`
- [ ] T026 [US5] Add ingestion run metadata migration and persistence logic in `supabase/migrations/20260311_004_ingestion_runs.sql` and `data/src/runs/persist_ingestion_run.py`
- [ ] T027 [US5] Create repeatable ingestion entrypoint and operator documentation in `data/src/runs/run_ingestion.py` and `data/README.md`

**Checkpoint**: Raw Rossmann data can be ingested, validated, normalized, and persisted repeatably

---

## Phase 4: User Story 1 - View Store Performance Dashboard (Priority: P1) 🎯 MVP

**Goal**: Let an authenticated user view store performance, date-filtered historical sales, and KPI summaries through the backend API and dashboard UI

**Independent Test**: Log in as an authorized store user, request a store dashboard, apply a date filter, and confirm that only authorized store data and KPI summaries are returned and rendered

### Tests for User Story 1

- [ ] T028 [P] [US1] Add KPI mart validation tests for daily, weekly, and monthly outputs in `data/tests/integration/test_kpi_marts.py`
- [ ] T029 [P] [US1] Add backend contract tests for stores, sales, and KPI endpoints in `backend/tests/contract/test_stores_api.py` and `backend/tests/contract/test_kpis_api.py`
- [ ] T030 [P] [US1] Add backend integration test for authorized dashboard access in `backend/tests/integration/test_dashboard_access.py`
- [ ] T031 [P] [US1] Add frontend dashboard rendering test in `frontend/tests/dashboard/dashboard-page.test.tsx`

### Implementation for User Story 1

- [ ] T032 [P] [US1] Create KPI mart migrations in `supabase/migrations/20260311_005_kpi_daily.sql`, `supabase/migrations/20260311_006_kpi_weekly.sql`, and `supabase/migrations/20260311_007_kpi_monthly.sql`
- [ ] T033 [P] [US1] Implement KPI mart builders and refresh workflow in `data/src/marts/build_daily_kpi.py`, `data/src/marts/build_periodic_kpis.py`, and `data/src/marts/refresh_kpis.py`
- [ ] T034 [P] [US1] Create store, sales, and KPI repositories in `backend/src/repositories/store_repository.py`, `backend/src/repositories/sales_repository.py`, and `backend/src/repositories/kpi_repository.py`
- [ ] T035 [P] [US1] Define store, sales, and KPI request-response schemas in `backend/src/schemas/stores.py`, `backend/src/schemas/sales.py`, and `backend/src/schemas/kpis.py`
- [ ] T036 [US1] Implement store and KPI services with access-aware filtering in `backend/src/services/store_service.py` and `backend/src/services/kpi_service.py`
- [ ] T037 [US1] Implement `/api/v1/stores`, `/api/v1/sales`, and base `/api/v1/kpis` routes in `backend/src/api/v1/stores.py`, `backend/src/api/v1/sales.py`, and `backend/src/api/v1/kpis.py`
- [ ] T038 [P] [US1] Create frontend analytics API clients and dashboard page shell in `frontend/src/lib/api/stores.ts`, `frontend/src/lib/api/analytics.ts`, and `frontend/src/app/dashboard/page.tsx`
- [ ] T039 [US1] Implement store selection, date filtering, and historical chart components in `frontend/src/features/dashboard/store-dashboard.tsx`, `frontend/src/features/dashboard/store-filter-form.tsx`, and `frontend/src/components/charts/sales-history-chart.tsx`
- [ ] T040 [US1] Add analytics-specific logging and dashboard error states in `backend/src/observability/analytics_logging.py` and `frontend/src/features/dashboard/dashboard-error-state.tsx`

**Checkpoint**: User Story 1 is independently functional and demoable as the MVP dashboard

---

## Phase 5: User Story 2 - Generate Sales Forecast (Priority: P1)

**Goal**: Let an authenticated user retrieve governed six-week sales forecasts, confidence context, and model accuracy metadata through the API and forecast UI

**Independent Test**: Log in as an authorized user, request a six-week forecast for a store, and confirm the system returns persisted forecast values, confidence ranges, model metadata, and a warning or fallback path for insufficient data

### Tests for User Story 2

- [ ] T041 [P] [US2] Add feature-generation and baseline-model tests in `ml/tests/test_feature_generation.py` and `ml/tests/test_baseline_model.py`
- [ ] T042 [P] [US2] Add model evaluation and low-data fallback tests in `ml/tests/test_model_evaluation.py` and `ml/tests/test_low_data_fallback.py`
- [ ] T043 [P] [US2] Add backend contract and integration tests for forecast retrieval in `backend/tests/contract/test_forecasts_api.py` and `backend/tests/integration/test_forecast_access.py`
- [ ] T044 [P] [US2] Add frontend forecast page tests in `frontend/tests/forecasts/forecast-page.test.tsx`

### Implementation for User Story 2

- [ ] T045 [P] [US2] Create ML metadata and forecast output migrations in `supabase/migrations/20260311_008_ml_metadata.sql` and `supabase/migrations/20260311_009_forecast_results.sql`
- [ ] T046 [P] [US2] Implement forecast feature preparation in `ml/src/features/build_forecast_features.py`
- [ ] T047 [P] [US2] Implement baseline training and fallback publication in `ml/src/training/train_baseline.py` and `ml/src/publishing/publish_baseline_forecasts.py`
- [ ] T048 [P] [US2] Implement Prophet and XGBoost training workflows in `ml/src/training/train_prophet.py` and `ml/src/training/train_xgboost.py`
- [ ] T049 [US2] Implement model evaluation, selection, and active-model publication in `ml/src/evaluation/evaluate_models.py`, `ml/src/evaluation/select_active_model.py`, and `ml/src/publishing/publish_model_metadata.py`
- [ ] T050 [US2] Implement forecast publication and artifact reference persistence in `ml/src/publishing/publish_forecasts.py` and `ml/src/publishing/publish_artifacts.py`
- [ ] T051 [P] [US2] Create forecast repository and response schemas in `backend/src/repositories/forecast_repository.py` and `backend/src/schemas/forecasts.py`
- [ ] T052 [US2] Implement forecast service and `/api/v1/forecasts` route in `backend/src/services/forecast_service.py` and `backend/src/api/v1/forecasts.py`
- [ ] T053 [P] [US2] Create frontend forecast API client and chart components in `frontend/src/lib/api/forecasts.ts` and `frontend/src/components/charts/forecast-chart.tsx`
- [ ] T054 [US2] Implement forecast page, accuracy summary, and warning states in `frontend/src/app/forecasts/page.tsx` and `frontend/src/features/forecasts/forecast-view.tsx`
- [ ] T055 [US2] Document forecast publication and model metadata expectations in `ml/README.md` and `docs/api/forecasts.md`

**Checkpoint**: User Story 2 is independently functional with governed forecast retrieval and fallback behavior

---

## Phase 6: User Story 3 - Compare Store Performance (Priority: P2)

**Goal**: Let authorized users compare KPI performance across stores using a controlled analytical mart and comparison UI

**Independent Test**: Log in as a marketing user, request comparison data for accessible stores, apply filters, and confirm the system returns ranked comparison results only within authorized scope

### Tests for User Story 3

- [ ] T056 [P] [US3] Add comparison mart validation tests in `data/tests/integration/test_store_comparison_mart.py`
- [ ] T057 [P] [US3] Add backend contract and integration tests for comparison queries in `backend/tests/contract/test_store_comparison_api.py` and `backend/tests/integration/test_store_comparison_access.py`
- [ ] T058 [P] [US3] Add frontend comparison page tests in `frontend/tests/comparison/comparison-page.test.tsx`

### Implementation for User Story 3

- [ ] T059 [P] [US3] Create comparison mart migration and refresh logic in `supabase/migrations/20260311_010_store_comparison.sql`, `data/src/marts/build_store_comparison.py`, and `data/src/marts/refresh_store_comparison.py`
- [ ] T060 [P] [US3] Create comparison repository and schemas in `backend/src/repositories/comparison_repository.py` and `backend/src/schemas/comparison.py`
- [ ] T061 [US3] Implement comparison service and KPI comparison route extensions in `backend/src/services/comparison_service.py` and `backend/src/api/v1/kpis.py`
- [ ] T062 [P] [US3] Create frontend comparison API client and page shell in `frontend/src/lib/api/comparison.ts` and `frontend/src/app/dashboard/comparison/page.tsx`
- [ ] T063 [US3] Implement accessible-store ranking view and filter components in `frontend/src/features/comparison/store-comparison-view.tsx` and `frontend/src/features/comparison/comparison-filters.tsx`

**Checkpoint**: User Story 3 is independently functional with filterable, authorized store comparison

---

## Phase 7: User Story 4 - Access Detailed KPIs via API (Priority: P2)

**Goal**: Provide analyst-friendly, paginated, validated KPI and forecast API access with consistent error envelopes and updated API documentation

**Independent Test**: Authenticate as a data analyst, query detailed KPI and forecast endpoints with filters and pagination, and confirm the API returns documented response shapes, rejects unauthorized access, and preserves consistent errors

### Tests for User Story 4

- [ ] T064 [P] [US4] Add contract tests for paginated KPI and forecast API responses in `backend/tests/contract/test_kpi_pagination.py` and `backend/tests/contract/test_forecast_pagination.py`
- [ ] T065 [P] [US4] Add integration tests for analyst access, unauthorized requests, and error envelopes in `backend/tests/integration/test_analyst_api_access.py` and `backend/tests/integration/test_error_envelopes.py`

### Implementation for User Story 4

- [ ] T066 [P] [US4] Extend shared pagination, filter, and error schemas in `backend/src/schemas/common.py`, `backend/src/schemas/kpis.py`, and `backend/src/schemas/forecasts.py`
- [ ] T067 [US4] Implement detailed KPI query options and paginated forecast retrieval in `backend/src/services/kpi_service.py` and `backend/src/services/forecast_service.py`
- [ ] T068 [US4] Extend `/api/v1/kpis` and `/api/v1/forecasts` for analyst-facing detailed API access in `backend/src/api/v1/kpis.py` and `backend/src/api/v1/forecasts.py`
- [ ] T069 [US4] Publish updated API contracts and examples in `specs/001-sales-forecasting-platform/contracts/api-spec.json` and `docs/api/openapi.json`
- [ ] T070 [US4] Document analyst API usage and authentication expectations in `docs/api/README.md` and `specs/001-sales-forecasting-platform/quickstart.md`

**Checkpoint**: User Story 4 is independently functional as a documented, analyst-ready API surface

---

## Phase 8: Polish & Cross-Cutting Hardening

**Purpose**: Finalize observability, security hardening, admin operations, demo readiness, and end-to-end validation

- [ ] T071 [P] Add end-to-end smoke tests for login, dashboard, comparison, and forecast flows in `backend/tests/integration/test_smoke_flows.py` and `frontend/tests/e2e/smoke.spec.ts`
- [ ] T072 [P] Expand structured logging and correlation propagation across backend, data, and ML in `backend/src/observability/logging.py`, `data/src/runs/logging.py`, and `ml/src/publishing/logging.py`
- [ ] T073 [P] Implement readiness and freshness checks for Supabase, ingestion, KPI refresh, and forecast publication in `backend/src/observability/readiness.py` and `backend/src/api/v1/health.py`
- [ ] T074 [P] Add rate limiting, secure CORS, and secret-safe error redaction in `backend/src/core/security.py` and `backend/src/core/errors.py`
- [ ] T075 [P] Implement admin access management and audit logging in `backend/src/services/admin_service.py`, `backend/src/api/v1/admin.py`, and `backend/tests/integration/test_admin_access_management.py`
- [ ] T076 [P] Create academic demo seed data and access restrictions in `supabase/seed/demo_access.sql` and `backend/tests/integration/test_academic_demo_access.py`
- [ ] T077 [P] Add deployment, operations, and demo-run documentation in `docs/deployment/README.md`, `docs/deployment/demo-checklist.md`, and `README.md`
- [ ] T078 [P] Add performance and pipeline freshness validation in `backend/tests/integration/test_performance_budget.py` and `data/tests/integration/test_pipeline_freshness.py`

**Checkpoint**: Platform is secure-by-default, observable, demo-ready, and validated across core flows

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** has no dependencies and starts immediately.
- **Phase 2: Foundational** depends on Setup and blocks all story work.
- **Phase 3: US5** depends on Foundational and must complete before downstream analytics and forecasting stories use trusted data.
- **Phase 4: US1** depends on US5 because dashboard analytics require validated operational data and KPI marts.
- **Phase 5: US2** depends on US5 because forecasting requires cleaned operational data and governed metadata structures.
- **Phase 6: US3** depends on US1 because comparison builds on the KPI layer and dashboard-ready analytical contracts.
- **Phase 7: US4** depends on US1 and US2 because it hardens and extends the existing KPI and forecast API surface.
- **Phase 8: Polish** depends on all desired user stories being complete.

### User Story Dependencies

- **US5 - Automated Data Preparation**: starts after Foundational and establishes the trusted data foundation.
- **US1 - View Store Performance Dashboard**: starts after US5 and provides the MVP user-facing analytical experience.
- **US2 - Generate Sales Forecast**: starts after US5 and can proceed in parallel with later US1 cleanup if staffing allows.
- **US3 - Compare Store Performance**: starts after US1 because it relies on KPI marts and established analytics contracts.
- **US4 - Access Detailed KPIs via API**: starts after US1 and US2 because it formalizes the existing analytical and forecast endpoints for analyst use.

### Within Each User Story

- Write test tasks first and confirm they fail before implementation.
- Create schema and persistence support before service logic.
- Create repository and schema models before routes or UI integration.
- Complete backend behavior before frontend presentation tasks.
- Finish story-specific logging and documentation before marking the story complete.

### Parallel Opportunities

- Setup tasks marked `[P]` can run in parallel after T001 and T002.
- Foundational tasks T008-T016 can run in parallel once T007 is defined.
- In US5, T021 and T022 can run in parallel before T023-T027.
- In US1, T032-T035 can run in parallel after the story tests are in place.
- In US2, T046-T048 and T051-T053 can run in parallel after T045.
- In US3, T059 and T060 can run in parallel after tests are defined.
- In US4, T066 can proceed in parallel with documentation preparation in T069-T070 after the API direction is fixed.
- Hardening tasks T071-T078 can be split across team members once core stories are stable.

---

## Parallel Example: User Story 5

- Task: `T019 [US5] Add successful ingestion integration test in data/tests/integration/test_ingestion_success.py`
- Task: `T020 [US5] Add validation-failure coverage in data/tests/integration/test_ingestion_failures.py`
- Task: `T021 [US5] Create Rossmann raw dataset readers in data/src/ingest/read_train_csv.py and data/src/ingest/read_store_csv.py`
- Task: `T022 [US5] Create validation rules in data/src/quality/validate_sales_records.py and data/src/quality/validate_store_records.py`

## Parallel Example: User Story 1

- Task: `T028 [US1] Add KPI mart validation tests in data/tests/integration/test_kpi_marts.py`
- Task: `T029 [US1] Add backend contract tests in backend/tests/contract/test_stores_api.py and backend/tests/contract/test_kpis_api.py`
- Task: `T032 [US1] Create KPI mart migrations in supabase/migrations/20260311_005_kpi_daily.sql, supabase/migrations/20260311_006_kpi_weekly.sql, and supabase/migrations/20260311_007_kpi_monthly.sql`
- Task: `T034 [US1] Create store, sales, and KPI repositories in backend/src/repositories/store_repository.py, backend/src/repositories/sales_repository.py, and backend/src/repositories/kpi_repository.py`

## Parallel Example: User Story 2

- Task: `T041 [US2] Add feature-generation and baseline-model tests in ml/tests/test_feature_generation.py and ml/tests/test_baseline_model.py`
- Task: `T042 [US2] Add model evaluation and low-data fallback tests in ml/tests/test_model_evaluation.py and ml/tests/test_low_data_fallback.py`
- Task: `T046 [US2] Implement forecast feature preparation in ml/src/features/build_forecast_features.py`
- Task: `T048 [US2] Implement Prophet and XGBoost training workflows in ml/src/training/train_prophet.py and ml/src/training/train_xgboost.py`

---

## Implementation Strategy

### MVP First

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US5 Automated Data Preparation
4. Complete Phase 4: US1 View Store Performance Dashboard
5. Stop and validate the platform as an analytics-first MVP

### Forecasting Increment

1. Add Phase 5: US2 Generate Sales Forecast
2. Validate persisted forecast retrieval, fallback handling, and frontend visualization
3. Demonstrate analytics plus forecasting as the primary thesis increment

### Extended Analytical Surface

1. Add Phase 6: US3 Compare Store Performance
2. Add Phase 7: US4 Access Detailed KPIs via API
3. Use Phase 8 for hardening, demo-readiness, and operations checks

### Small-Team Execution Guidance

- One developer can execute phases sequentially in the order above.
- A small team can split work by module after Foundational is complete:
  - Data and Supabase work on US5 and KPI marts
  - Backend work on auth, repositories, and REST endpoints
  - ML work on forecast preparation, evaluation, and publication
  - Frontend work starts after stable API contracts exist for each story

---

## Notes

- The task order is dependency-driven and intentionally keeps the headless modular monolith intact.
- The frontend never receives tasks that move business logic out of the backend.
- Supabase tasks are scoped to schema, RLS, storage, and seed responsibilities only.
- ML tasks stop at offline training, evaluation, publication, and controlled retrieval; no microservice split is introduced.
- Each story phase ends at an independently testable checkpoint to support thesis demos and incremental implementation.
