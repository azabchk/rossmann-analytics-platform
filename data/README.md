# Data Module

Data ingestion, validation, preprocessing, and operational table loading for the
Sales Forecasting Platform.

## Overview

The data module implements a trusted data pipeline that:
1. Reads raw Rossmann CSV files (train.csv, store.csv)
2. Validates data quality with configurable rules
3. Normalizes and cleans the data
4. Loads transformed data into operational tables
5. Tracks all runs with detailed metadata and validation reports

## Architecture

### Modules

| Module | Purpose | Files |
|---------|---------|--------|
| `ingest` | Read raw Rossmann CSV files | `read_train_csv.py`, `read_store_csv.py` |
| `quality` | Validate data quality and identify issues | `validate_sales_records.py`, `validate_store_records.py` |
| `transform` | Normalize and clean data | `normalize_sales.py`, `normalize_stores.py` |
| `load` | Load data into database tables | `load_operational_tables.py` |
| `runs` | Orchestrate pipeline and track metadata | `run_ingestion.py`, `models.py`, `reporting.py`, `persist_ingestion_run.py` |

### Data Flow

```
Raw CSV Files
    ↓
[ingest] - Read and parse CSV
    ↓
[quality] - Validate and identify issues
    ↓
[runs] - Record validation results
    ↓
[transform] - Normalize and clean data
    ↓
[load] - Load into operational tables
    ↓
Database (internal schema)
```

## Running the Ingestion Pipeline

### Prerequisites

1. **Database Setup**: Ensure the ingestion runs migration is applied:
   ```bash
   # Apply migration
   psql -h localhost -U postgres -d sales_forecasting -f supabase/migrations/20260311_004_ingestion_runs.sql
   ```

2. **Data Files**: Have Rossmann CSV files ready:
   - `train.csv` - Daily sales records
   - `store.csv` - Store metadata

### Environment Variables

Configure these environment variables before running:

| Variable | Required | Description | Example |
|----------|-----------|-------------|----------|
| `DATABASE_URL` | Yes | PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/db` |
| `TRAIN_CSV_PATH` | Yes | Path to train.csv | `/data/train.csv` |
| `STORE_CSV_PATH` | Yes | Path to store.csv | `/data/store.csv` |
| `USE_STAGING` | No | Use staging tables before promotion (default: true) | `true` or `false` |
| `TRIGGERED_BY` | No | User/system triggering the run | `admin@example.com` |

### Running via Python

```bash
cd /home/azab-22/Desktop/DIPLOMA/data
export DATABASE_URL="postgresql://user:pass@localhost:5432/sales_forecasting"
export TRAIN_CSV_PATH="./train.csv"
export STORE_CSV_PATH="./store.csv"
export USE_STAGING="true"
export TRIGGERED_BY="admin@example.com"

python -m src.runs.run_ingestion
```

### Running Programmatically

```python
from src.runs.run_ingestion import run_ingestion

run = run_ingestion(
    train_csv_path="./train.csv",
    store_csv_path="./store.csv",
    database_url="postgresql://user:pass@localhost:5432/sales_forecasting",
    use_staging=True,
    upsert=True,
    triggered_by="admin@example.com",
)

print(f"Run {run.run_id} completed with status: {run.status.value}")
```

## Ingestion Stages

### 1. Read
- Parses CSV files with type validation
- Returns pandas DataFrames for processing
- Handles missing values and parsing errors

### 2. Validate
- Checks structural integrity (required fields, types)
- Checks logical consistency (e.g., sales when closed)
- Flags outliers and duplicates
- Records all issues with severity (error/warning/info)

### 3. Transform
- Normalizes data types and formats
- Handles missing values with business rules
- Removes invalid records
- Maps columns to operational schema

### 4. Load
- Loads data into staging or base tables
- Supports upsert (update existing, insert new)
- Uses PostgreSQL ON CONFLICT for efficiency
- Records load counts and failures

## Validation Rules

### Sales Records (train.csv)

| Rule | Severity | Description |
|-------|-----------|-------------|
| Missing Store | Error | Store ID cannot be null |
| Missing Date | Error | Date cannot be null |
| Invalid Date Range | Error | Date must be between 2013-01-01 and 2015-12-31 |
| Invalid Day of Week | Error | Must be 1-7 |
| Negative Sales | Error | Sales cannot be negative |
| Negative Customers | Error | Customers cannot be negative |
| Sales When Closed | Error | Closed stores cannot have sales |
| Customers When Closed | Error | Closed stores cannot have customers |
| Zero Sales When Open | Warning | Open stores typically have sales |
| Duplicate Store/Date | Error | Must be unique combination |
| Extreme Sales (>40000) | Warning | Potential outlier |

### Store Records (store.csv)

| Rule | Severity | Description |
|-------|-----------|-------------|
| Missing Store ID | Error | Store ID cannot be null |
| Invalid Store Type | Error | Must be a, b, c, or d |
| Invalid Assortment | Error | Must be a, b, or c |
| Negative Competition Distance | Error | Distance cannot be negative |
| Invalid Promo2 Flag | Error | Must be 0 or 1 |
| Incomplete Promo2 Dates | Error | When Promo2=1, require dates |
| Duplicate Store ID | Error | Store ID must be unique |

## Database Tables

### internal.ingestion_runs
Tracks each pipeline execution with:
- Run ID (UUID)
- Status (pending, running, validating, transforming, loading, completed, failed, cancelled)
- Input file paths and record counts
- Processing metrics
- Error messages and tracebacks
- Timestamps and duration

### internal.ingestion_validation_results
Aggregated validation results per table per run with:
- Result ID
- Run ID reference
- Table name
- Record counts (total, valid, error, warning)
- Detailed issues/warnings as JSON

### internal.ingestion_validation_issues
Individual validation issues with:
- Issue ID
- Run ID and Result ID references
- Issue type and severity
- Table name and row identifier
- Field name, actual/expected values
- Message

### internal.sales_operational_staging
Staging table for sales records before promotion:
- store_id, date, day_of_week
- sales, customers, open
- promo, state_holiday, school_holiday

### internal.stores_operational_staging
Staging table for store metadata before promotion:
- store_id (primary key)
- store_type, assortment
- competition_distance, competition_open_since_month, competition_open_since_year
- promo2, promo2_since_week, promo2_since_year, promo_interval

## Testing

```bash
cd data
pytest tests/ -v
```

### Test Structure

```
tests/
├── unit/          # Unit tests for individual functions
└── integration/   # Integration tests for the full pipeline
```

## Troubleshooting

### Common Issues

**Issue**: File not found error
```
Solution: Verify TRAIN_CSV_PATH and STORE_CSV_PATH point to existing files
```

**Issue**: Database connection error
```
Solution: Verify DATABASE_URL is correct and database is accessible
```

**Issue**: Validation errors preventing load
```
Solution: Check the validation report for specific issues.
Some errors (like extreme outliers) may be warnings that allow continuation.
```

**Issue**: Duplicate key errors during load
```
Solution: The pipeline should handle duplicates during validation.
If errors persist, check source data for duplicate store/date combinations.
```

### Viewing Ingestion Results

To view recent ingestion runs:

```sql
SELECT
    run_id,
    status,
    started_at,
    duration_seconds,
    train_record_count,
    store_record_count,
    records_loaded,
    total_error_count,
    total_warning_count
FROM internal.ingestion_runs
ORDER BY started_at DESC
LIMIT 10;
```

To view validation issues for a specific run:

```sql
SELECT
    issue_type,
    severity,
    table_name,
    row_identifier,
    field_name,
    message
FROM internal.ingestion_validation_issues
WHERE run_id = '<run-id>'
ORDER BY severity, issue_type;
```

## Next Steps

After data ingestion:
1. Data is available in `internal.sales_operational` and `internal.stores_operational`
2. Run KPI mart generation: `python -m src.marts.refresh_kpis`
3. Train forecasting models: `python -m ml.src.training.train_baseline`
4. Access data through backend API endpoints

## Module Boundary

This module **MUST NOT**:
- Expose user-facing APIs (that's the backend's responsibility)
- Perform authentication or authorization decisions
- Bypass controlled Supabase schemas
- Own frontend concerns
