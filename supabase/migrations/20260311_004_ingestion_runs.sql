-- Migration: Ingestion Run Metadata Tables
-- Description: Creates tables to track ingestion pipeline runs and validation results
-- Schema: internal (for pipeline metadata)
-- Dependencies: 20260311_001_base_schemas.sql

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Ingestion runs table
-- Tracks each execution of the data ingestion pipeline
CREATE TABLE IF NOT EXISTS internal.ingestion_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(50) NOT NULL CHECK (status IN (
        'pending', 'running', 'validating', 'transforming', 'loading',
        'completed', 'failed', 'cancelled'
    )),

    -- Input information
    train_csv_path TEXT,
    store_csv_path TEXT,
    train_record_count INTEGER DEFAULT 0,
    store_record_count INTEGER DEFAULT 0,

    -- Processing metrics
    records_normalized INTEGER DEFAULT 0,
    records_loaded INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,

    -- Error handling
    error_message TEXT,
    error_traceback TEXT,

    -- Metadata
    triggered_by TEXT,
    parameters JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds NUMERIC(10, 2),

    -- Summary flags
    has_validation_errors BOOLEAN DEFAULT FALSE,
    total_error_count INTEGER DEFAULT 0,
    total_warning_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status ON internal.ingestion_runs(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started_at ON internal.ingestion_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_triggered_by ON internal.ingestion_runs(triggered_by);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION internal.update_ingestion_runs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS ingestion_runs_updated_at ON internal.ingestion_runs;
CREATE TRIGGER ingestion_runs_updated_at
    BEFORE UPDATE ON internal.ingestion_runs
    FOR EACH ROW
    EXECUTE FUNCTION internal.update_ingestion_runs_updated_at();


-- Table validation results table
-- Stores aggregated validation results per table per run
CREATE TABLE IF NOT EXISTS internal.ingestion_validation_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES internal.ingestion_runs(run_id) ON DELETE CASCADE,

    -- Table information
    table_name VARCHAR(100) NOT NULL,

    -- Summary counts
    total_records INTEGER DEFAULT 0,
    valid_records INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,

    -- Detailed results stored as JSON
    issues JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_run_table UNIQUE (run_id, table_name)
);

-- Indexes for querying validation results
CREATE INDEX IF NOT EXISTS idx_ingestion_validation_results_run_id ON internal.ingestion_validation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_validation_results_table_name ON internal.ingestion_validation_results(table_name);


-- Validation issues detail table
-- Stores individual validation issues for detailed reporting
CREATE TABLE IF NOT EXISTS internal.ingestion_validation_issues (
    issue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id UUID NOT NULL REFERENCES internal.ingestion_validation_results(result_id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES internal.ingestion_runs(run_id) ON DELETE CASCADE,

    -- Issue classification
    issue_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('error', 'warning', 'info')),

    -- Issue location
    table_name VARCHAR(100) NOT NULL,
    row_identifier TEXT,
    field_name TEXT,

    -- Issue details
    actual_value TEXT,
    expected_value TEXT,
    message TEXT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for querying validation issues
CREATE INDEX IF NOT EXISTS idx_ingestion_validation_issues_run_id ON internal.ingestion_validation_issues(run_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_validation_issues_table_name ON internal.ingestion_validation_issues(table_name);
CREATE INDEX IF NOT EXISTS idx_ingestion_validation_issues_severity ON internal.ingestion_validation_issues(severity);
CREATE INDEX IF NOT EXISTS idx_ingestion_validation_issues_issue_type ON internal.ingestion_validation_issues(issue_type);


-- Operational staging tables
-- These are staging versions of the operational data tables
-- They are loaded first, validated, then promoted to production

-- Sales operational staging table
CREATE TABLE IF NOT EXISTS internal.sales_operational_staging (
    id BIGSERIAL PRIMARY KEY,
    store_id INTEGER NOT NULL,
    date DATE NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    sales NUMERIC(10, 2) NOT NULL CHECK (sales >= 0),
    customers INTEGER NOT NULL CHECK (customers >= 0),
    open INTEGER NOT NULL CHECK (open IN (0, 1)),
    promo INTEGER NOT NULL CHECK (promo IN (0, 1)),
    state_holiday VARCHAR(10) NOT NULL DEFAULT '0',
    school_holiday INTEGER NOT NULL CHECK (school_holiday IN (0, 1)),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint for sales records
CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_operational_staging_unique
    ON internal.sales_operational_staging(store_id, date);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_sales_operational_staging_store_id
    ON internal.sales_operational_staging(store_id);
CREATE INDEX IF NOT EXISTS idx_sales_operational_staging_date
    ON internal.sales_operational_staging(date);


-- Stores operational staging table
CREATE TABLE IF NOT EXISTS internal.stores_operational_staging (
    store_id INTEGER PRIMARY KEY,
    store_type VARCHAR(10),
    assortment VARCHAR(10),
    competition_distance NUMERIC(10, 2),
    competition_open_since_month INTEGER CHECK (competition_open_since_month BETWEEN 1 AND 12),
    competition_open_since_year INTEGER,
    promo2 INTEGER NOT NULL CHECK (promo2 IN (0, 1)),
    promo2_since_week INTEGER CHECK (promo2_since_week BETWEEN 1 AND 53),
    promo2_since_year INTEGER,
    promo_interval TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_stores_operational_staging_store_type
    ON internal.stores_operational_staging(store_type);
CREATE INDEX IF NOT EXISTS idx_stores_operational_staging_promo2
    ON internal.stores_operational_staging(promo2);


-- Comments for documentation
COMMENT ON TABLE internal.ingestion_runs IS 'Tracks each execution of the data ingestion pipeline';
COMMENT ON TABLE internal.ingestion_validation_results IS 'Stores aggregated validation results per table per run';
COMMENT ON TABLE internal.ingestion_validation_issues IS 'Stores individual validation issues for detailed reporting';
COMMENT ON TABLE internal.sales_operational_staging IS 'Staging table for sales records before promotion to production';
COMMENT ON TABLE internal.stores_operational_staging IS 'Staging table for store metadata before promotion to production';
