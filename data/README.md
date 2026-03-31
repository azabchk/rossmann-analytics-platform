# Data Module

The `data` module owns the Rossmann ingestion and preprocessing path for the
platform. In the approved architecture this module is an internal pipeline
module, not a user-facing service. Its responsibility in the current phase is
to turn raw Rossmann source files into validated, normalized operational data
inside controlled Supabase schemas.

## Phase Scope

The currently implemented Phase 3 slice covers:

- raw CSV readers for `train.csv` and `store.csv`
- structural, logical, and referential validation
- validation reporting and ingestion run metadata
- normalization into stable operational column shapes
- loading into restricted staging tables and promotion into base tables
- a repeatable Python entrypoint for local operator execution

This module does not expose HTTP endpoints, compute KPI marts, or run forecast
training. Those capabilities belong to later approved phases.

## Ingestion Flow

The implemented pipeline follows this sequence:

1. Read `train.csv` and `store.csv` from configured local paths.
2. Validate raw structure, required columns, logical quality rules, duplicates,
   and cross-file store references.
3. Persist run metadata and validation outcomes to restricted ingestion tables.
4. Normalize accepted records into controlled operational shapes.
5. Load normalized records into `internal.stores_staging` and
   `internal.sales_records_staging`.
6. Promote the validated staging contents into `internal.stores` and
   `internal.sales_records`.

Validation errors stop the run before normalization and loading. Warnings are
retained in run metadata and reports but do not block progression by
themselves.

## Database Objects Used

Phase 3 relies on these `internal` schema objects:

- `internal.ingestion_runs`
- `internal.ingestion_validation_results`
- `internal.ingestion_validation_issues`
- `internal.stores_staging`
- `internal.sales_records_staging`
- `internal.stores`
- `internal.sales_records`

The `internal` schema remains restricted. The frontend does not read these
tables directly, and no user-facing API is defined here.

## Runtime Inputs

The ingestion entrypoint supports the following environment variables:

- `DATABASE_URL`
- `ROSSMANN_TRAIN_PATH` or `TRAIN_CSV_PATH`
- `ROSSMANN_STORE_PATH` or `STORE_CSV_PATH`
- `USE_STAGING` with default `true`
- `UPSERT` with default `true`
- `PROMOTE_AFTER_STAGING` with default `true`
- `TRIGGERED_BY`
- `LOG_LEVEL`

## Local Validation

Focused Phase 3 validation can be run from the repository root:

```bash
pytest data/tests/integration/test_ingestion_success.py data/tests/integration/test_ingestion_failures.py -q
```

The operator entrypoint can be executed directly with module syntax:

```bash
python -m data.src.runs.run_ingestion
```

## Boundary Reminder

- No frontend business logic belongs in this module.
- No KPI marts or forecast outputs are produced here.
- No direct client access to Supabase tables is introduced here.
- All writes stay inside the controlled database boundary defined by the
  approved architecture.
