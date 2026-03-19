# Data Model: Sales Forecasting Platform

**Feature**: Sales Forecasting Platform
**Branch**: `001-sales-forecasting-platform`
**Date**: 2026-03-06

## Overview

This document defines the complete data model for the Sales Forecasting Platform. The model is organized into three layers:

1. **Source Data Layer**: Raw data from Rossmann dataset
2. **Transformed Data Layer**: Cleaned, validated, and processed data
3. **Analytical Layer**: KPI marts and forecast results for API consumption

All tables follow PostgreSQL naming conventions (snake_case) and include standard audit fields where applicable.

## Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│     User     │───────│ Store Access │───────│    Store     │
└──────────────┘       └──────────────┘       └──────┬───────┘
                                                     │
                                             ┌───────────┴───────────┐
                                             │                       │
                                    ┌────────▼────────┐   ┌────────▼────────┐
                                    │ Sales Record    │   │ Forecast Result  │
                                    └─────────────────┘   └─────────────────┘
                                             │
                                    ┌───────────┴───────────┐
                                    │                       │
                             ┌────────▼────────┐   ┌────────▼────────┐
                             │ Daily KPI Mart  │   │ Weekly KPI Mart │
                             └─────────────────┘   └─────────────────┘
```

## Security-Sensitive Entities

| Entity | Sensitivity Level | Protection Mechanism |
|---------|------------------|---------------------|
| `User` | HIGH (email, password hash) | Row-level security, admin-only access |
| `Store Access` | HIGH (access permissions) | Row-level security by user_id |
| `Forecast Result` | MEDIUM (business value) | Row-level security by store access |

## Core Entities

### Store

**Description**: Represents a physical retail location with static attributes.

**Purpose**: Master data for all stores, reference for sales records and forecasts.

**Source Mapping**: Derived from `store.csv` in Rossmann dataset.

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `store_id` | INTEGER | PRIMARY KEY, NOT NULL | Unique | Yes |
| `store_type` | VARCHAR(1) | NOT NULL, VALUES('A','B','C','D') | Yes |
| `assortment` | VARCHAR(1) | NOT NULL, VALUES('a','b','c') | Yes |
| `competition_distance` | INTEGER | NOT NULL, >= 0 | Yes |
| `competition_open_since_month` | INTEGER | NULL, VALUES(1-12) | Yes |
| `competition_open_since_year` | INTEGER | NULL, >= 1900 | Yes |
| `promo2` | BOOLEAN | NOT NULL | Yes |
| `promo2_since_week` | INTEGER | NULL, VALUES(1-52) | Yes |
| `promo2_since_year` | INTEGER | NULL, >= 2010 | Yes |
| `promo_interval` | VARCHAR(10) | NULL, Matches 'Jan,Apr,...' pattern | Yes |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Indexes**:
- PRIMARY: `store_id`
- Query: `store_type` (for filtering by type)

**Row-Level Security**: All users with access to this store can read.

---

### Sales Record

**Description**: Daily sales transaction data for a specific store.

**Purpose**: Core transactional data for KPI calculation and model training.

**Source Mapping**: Derived from `train.csv` in Rossmann dataset.

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `sales_record_id` | BIGSERIAL | PRIMARY KEY | No |
| `store_id` | INTEGER | NOT NULL, FK → Store.store_id | Yes |
| `date` | DATE | NOT NULL | Yes |
| `sales` | INTEGER | NOT NULL, >= 0 | Yes |
| `customers` | INTEGER | NULL, >= 0 | Yes |
| `open` | BOOLEAN | NOT NULL | Yes |
| `promo` | BOOLEAN | NOT NULL | Yes |
| `state_holiday` | VARCHAR(20) | NULL, VALUES('a','b','c',NULL) | Yes |
| `school_holiday` | BOOLEAN | NOT NULL | Yes |
| `day_of_week` | INTEGER | NOT NULL, VALUES(0-6) | Yes |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Indexes**:
- PRIMARY: `sales_record_id`
- Query: `store_id, date` (for time-series queries)
- Query: `date` (for aggregate queries)

**Row-Level Security**: Users can only read records for stores they have access to.

**Validation Rules**:
- `sales` must be non-negative
- `customers` must be non-negative when not NULL
- `open = FALSE` implies `sales = 0`
- Weekday must match `day_of_week` for given `date`

---

### User

**Description**: System user account with authentication and authorization details.

**Purpose**: Authentication and role-based access control.

**Source Mapping**: Supabase Auth system (auth.users table).

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `user_id` | UUID | PRIMARY KEY | No (managed by Supabase) |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | Yes (current user only) |
| `role` | VARCHAR(20) | NOT NULL, VALUES('admin','store_manager','marketing_manager','data_analyst') | Yes (current user only) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Row-Level Security**: Users can only read their own record.

**Admin Operations**:
- `role` can only be changed by users with `admin` role
- Email changes require re-authentication

---

### Store Access

**Description**: Junction table defining which stores each user can access.

**Purpose**: Enforces row-level security for multi-store users.

**Source Mapping**: Application-specific, not in source dataset.

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `access_id` | BIGSERIAL | PRIMARY KEY | No |
| `user_id` | UUID | NOT NULL, FK → User.user_id | No |
| `store_id` | INTEGER | NOT NULL, FK → Store.store_id | No |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Indexes**:
- PRIMARY: `access_id`
- Query: `user_id` (for RLS filtering)
- Query: `store_id` (for reverse lookups)

**Row-Level Security**: Admins see all entries; users see only their own.

**Validation Rules**:
- A user cannot have duplicate store access records
- `store_manager` role limited to exactly 1 store access
- `marketing_manager` and `data_analyst` roles can have multiple store accesses

---

## Analytical Entities

### Daily KPI Mart

**Description**: Pre-aggregated daily KPIs by store for dashboard queries.

**Purpose**: Optimize query performance for historical data visualization.

**Source Mapping**: Computed from `Sales Record`.

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `kpi_daily_id` | BIGSERIAL | PRIMARY KEY | No |
| `store_id` | INTEGER | NOT NULL, FK → Store.store_id | Yes |
| `date` | DATE | NOT NULL | Yes |
| `total_sales` | INTEGER | NOT NULL, >= 0 | Yes |
| `avg_customers` | NUMERIC(10,2) | NOT NULL, >= 0 | Yes |
| `promo_days` | INTEGER | NOT NULL, >= 0 | Yes |
| `holiday_days` | INTEGER | NOT NULL, >= 0 | Yes |
| `is_weekend` | BOOLEAN | NOT NULL | Yes |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Indexes**:
- PRIMARY: `kpi_daily_id`
- Query: `store_id, date` (for time-series queries)
- Query: `date` (for cross-store queries)

**Row-Level Security**: Users can only read KPIs for stores they have access to.

**Computed Fields**:
- `total_sales`: SUM(sales) for store on date
- `avg_customers`: AVG(customers) for store on date (NULL values excluded)
- `promo_days`: COUNT(DISTINCT date) where promo = TRUE (for weekly context)
- `holiday_days`: COUNT(DISTINCT date) where holiday = TRUE

---

### Weekly KPI Mart

**Description**: Pre-aggregated weekly KPIs by store.

**Purpose**: Optimize query performance for weekly trend analysis.

**Source Mapping**: Computed from `Daily KPI Mart`.

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `kpi_weekly_id` | BIGSERIAL | PRIMARY KEY | No |
| `store_id` | INTEGER | NOT NULL, FK → Store.store_id | Yes |
| `year` | INTEGER | NOT NULL, >= 2013 | Yes |
| `week` | INTEGER | NOT NULL, VALUES(1-53) | Yes |
| `total_sales` | INTEGER | NOT NULL, >= 0 | Yes |
| `avg_daily_sales` | NUMERIC(10,2) | NOT NULL, >= 0 | Yes |
| `max_daily_sales` | INTEGER | NOT NULL, >= 0 | Yes |
| `min_daily_sales` | INTEGER | NOT NULL, >= 0 | Yes |
| `promo_days` | INTEGER | NOT NULL, >= 0, <= 7 | Yes |
| `yoy_growth_rate` | NUMERIC(10,4) | NULL | Yes |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Indexes**:
- PRIMARY: `kpi_weekly_id`
- Query: `store_id, year, week` (for time-series queries)

**Row-Level Security**: Users can only read KPIs for stores they have access to.

**Computed Fields**:
- `avg_daily_sales`: SUM(total_sales) / COUNT(days)
- `yoy_growth_rate`: (current_week - same_week_last_year) / same_week_last_year

---

### Monthly KPI Mart

**Description**: Pre-aggregated monthly KPIs by store.

**Purpose**: Optimize query performance for monthly reports and seasonality analysis.

**Source Mapping**: Computed from `Weekly KPI Mart`.

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `kpi_monthly_id` | BIGSERIAL | PRIMARY KEY | No |
| `store_id` | INTEGER | NOT NULL, FK → Store.store_id | Yes |
| `year` | INTEGER | NOT NULL, >= 2013 | Yes |
| `month` | INTEGER | NOT NULL, VALUES(1-12) | Yes |
| `total_sales` | INTEGER | NOT NULL, >= 0 | Yes |
| `avg_daily_sales` | NUMERIC(10,2) | NOT NULL, >= 0 | Yes |
| `promo_uplift_pct` | NUMERIC(10,4) | NULL | Yes |
| `holiday_effect_pct` | NUMERIC(10,4) | NULL | Yes |
| `yoy_growth_rate` | NUMERIC(10,4) | NULL | Yes |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Indexes**:
- PRIMARY: `kpi_monthly_id`
- Query: `store_id, year, month` (for time-series queries)

**Row-Level Security**: Users can only read KPIs for stores they have access to.

**Computed Fields**:
- `promo_uplift_pct`: (promo_days_sales / non_promo_days_sales - 1) * 100
- `holiday_effect_pct`: (holiday_days_sales / non_holiday_days_sales - 1) * 100

---

### Store Comparison Mart

**Description**: Cross-store performance metrics for comparison views.

**Purpose**: Enable store-to-store benchmarking and performance ranking.

**Source Mapping**: Computed from `Weekly KPI Mart`.

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `comparison_id` | BIGSERIAL | PRIMARY KEY | No |
| `store_id` | INTEGER | NOT NULL, FK → Store.store_id | Yes |
| `period_start` | DATE | NOT NULL | Yes |
| `period_end` | DATE | NOT NULL | Yes |
| `total_sales` | INTEGER | NOT NULL, >= 0 | Yes |
| `rank_by_type` | INTEGER | NOT NULL, >= 1 | Yes |
| `rank_overall` | INTEGER | NOT NULL, >= 1 | Yes |
| `percentile_by_type` | INTEGER | NOT NULL, VALUES(0-100) | Yes |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Indexes**:
- PRIMARY: `comparison_id`
- Query: `period_start, period_end` (for filtering by date range)
- Query: `store_id` (for store-specific comparison)

**Row-Level Security**: Users can only read comparisons for stores they have access to.

**Computed Fields**:
- `rank_by_type`: Position within same store_type
- `rank_overall`: Position across all stores
- `percentile_by_type`: Percentile within same store_type (0-100)

---

## Forecast Result Entities

### Forecast Result

**Description**: Predicted sales for a specific store and future date.

**Purpose**: Store forecast outputs for dashboard and API access.

**Source Mapping**: Generated by ML models (Prophet/XGBoost).

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `forecast_id` | BIGSERIAL | PRIMARY KEY | No |
| `store_id` | INTEGER | NOT NULL, FK → Store.store_id | Yes |
| `forecast_date` | DATE | NOT NULL, >= current_date | Yes |
| `predicted_sales` | NUMERIC(10,2) | NOT NULL, >= 0 | Yes |
| `confidence_lower` | NUMERIC(10,2) | NOT NULL, >= 0 | Yes |
| `confidence_upper` | NUMERIC(10,2) | NOT NULL, >= 0 | Yes |
| `model_id` | VARCHAR(50) | NOT NULL | Yes |
| `model_version` | VARCHAR(20) | NOT NULL | Yes |
| `mape` | NUMERIC(10,4) | NULL, >= 0 | Yes |
| `rmse` | NUMERIC(10,2) | NULL, >= 0 | Yes |
| `generated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Yes |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |

**Indexes**:
- PRIMARY: `forecast_id`
- Query: `store_id, forecast_date` (for time-series queries)
- Query: `generated_at` (for latest forecast lookup)

**Row-Level Security**: Users can only read forecasts for stores they have access to.

**Validation Rules**:
- `confidence_lower` <= `predicted_sales` <= `confidence_upper`
- `forecast_date` must be in future (>= generation date)
- `mape` and `rmse` calculated on holdout set during training

---

### Forecast Metadata

**Description**: Metadata about model training runs and version tracking.

**Purpose**: Track model training history for reproducibility and audit.

**Source Mapping**: Generated during model training process.

| Field | Type | Constraints | Validation | API Exposure |
|--------|--------|--------------|----------------|---------------|
| `metadata_id` | BIGSERIAL | PRIMARY KEY | No |
| `model_id` | VARCHAR(50) | NOT NULL, UNIQUE | No |
| `model_version` | VARCHAR(20) | NOT NULL | No |
| `model_type` | VARCHAR(20) | NOT NULL, VALUES('prophet','xgboost','ensemble') | No |
| `training_start_date` | DATE | NOT NULL | No |
| `training_end_date` | DATE | NOT NULL | No |
| `training_records` | INTEGER | NOT NULL, >= 0 | No |
| `features_used` | JSONB | NOT NULL | No |
| `hyperparameters` | JSONB | NOT NULL | No |
| `mape_train` | NUMERIC(10,4) | NULL, >= 0 | No |
| `mape_validation` | NUMERIC(10,4) | NULL, >= 0 | No |
| `rmse_train` | NUMERIC(10,2) | NULL, >= 0 | No |
| `rmse_validation` | NUMERIC(10,2) | NULL, >= 0 | No |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT FALSE | No |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | No |
| `activated_at` | TIMESTAMP | NULL | No |

**Indexes**:
- PRIMARY: `metadata_id`
- Query: `is_active` (for finding active model)
- Query: `model_id, model_version` (for version lookup)

**Row-Level Security**: Only admins can read this table.

**Validation Rules**:
- `training_start_date` <= `training_end_date`
- `is_active = TRUE` requires `activated_at` is NOT NULL
- Only one model can be `is_active = TRUE` at a time

---

## Data Mapping Summary

### Source to Transformed Mapping

| Source Field (CSV) | Destination Table | Destination Field | Transformation |
|-------------------|------------------|-------------------|----------------|
| store.csv::Store | Store | store_id | Direct |
| store.csv::StoreType | Store | store_type | Direct |
| store.csv::Assortment | Store | assortment | Direct |
| store.csv::CompetitionDistance | Store | competition_distance | Direct |
| store.csv::CompetitionOpenSinceMonth | Store | competition_open_since_month | Direct |
| store.csv::CompetitionOpenSinceYear | Store | competition_open_since_year | Direct |
| train.csv::Store | Sales Record | store_id | FK to Store |
| train.csv::Date | Sales Record | date | Date parse |
| train.csv::Sales | Sales Record | sales | Direct |
| train.csv::Customers | Sales Record | customers | Direct |
| train.csv::Open | Sales Record | open | Boolean conversion |
| train.csv::Promo | Sales Record | promo | Boolean conversion |
| train.csv::StateHoliday | Sales Record | state_holiday | Direct |
| train.csv::SchoolHoliday | Sales Record | school_holiday | Boolean conversion |

### Transformed to Analytical Mapping

| Source Table | Destination Table | Aggregation | Key Fields |
|--------------|------------------|--------------|-------------|
| Sales Record | Daily KPI Mart | SUM(sales), AVG(customers) | store_id, date |
| Daily KPI Mart | Weekly KPI Mart | SUM(total_sales), AVG(avg_daily_sales) | store_id, year, week |
| Weekly KPI Mart | Monthly KPI Mart | SUM(total_sales), AVG(avg_daily_sales) | store_id, year, month |
| Weekly KPI Mart | Store Comparison Mart | SUM(total_sales) | store_id, period |
| Forecast Result | (API output) | No aggregation | store_id, forecast_date |

---

## Row-Level Security Policies

### Store Access Policy

**Policy Name**: `store_access_policy`

**Description**: Users can only access data for stores in their `store_access` table.

**Applies To**:
- Sales Record
- Daily KPI Mart
- Weekly KPI Mart
- Monthly KPI Mart
- Forecast Result

**SQL Logic**:
```sql
-- Only admins bypass this policy
CREATE POLICY store_access_policy ON sales_records
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM store_access
      WHERE store_access.user_id = auth.uid()
      AND store_access.store_id = sales_records.store_id
    )
    OR (SELECT role FROM users WHERE user_id = auth.uid()) = 'admin'
  );
```

### User Data Policy

**Policy Name**: `user_self_policy`

**Description**: Users can only read their own user record.

**Applies To**:
- User

**SQL Logic**:
```sql
CREATE POLICY user_self_policy ON users
  FOR SELECT
  USING (user_id = auth.uid());
```

---

## Migration Strategy

### Migration Files

Migration files are stored in `supabase/migrations/` and named with timestamp prefix:

```
supabase/migrations/
├── 20260306_001_create_stores_table.sql
├── 20260306_002_create_sales_records_table.sql
├── 20260306_003_create_users_view.sql
├── 20260306_004_create_store_access_table.sql
├── 20260306_005_create_kpi_daily_mart.sql
├── 20260306_006_create_kpi_weekly_mart.sql
├── 20260306_007_create_kpi_monthly_mart.sql
├── 20260306_008_create_forecast_results_table.sql
├── 20260306_009_create_forecast_metadata_table.sql
├── 20260306_010_create_store_comparison_mart.sql
├── 20260306_011_create_indexes.sql
├── 20260306_012_create_rls_policies.sql
└── 20260306_013_insert_seed_data.sql
```

### Rollback Strategy

Each migration file includes a corresponding `down` migration:

```
supabase/migrations/
├── 20260306_001_create_stores_table.sql
└── 20260306_001_drop_stores_table.sql  -- Rollback
```

---

## Data Quality Validation

### Validation Rules

| Rule | Table | Check | Action |
|-------|--------|--------|---------|
| Duplicate Check | Sales Record | No duplicate (store_id, date) pairs | Reject record |
| Date Range Check | Sales Record | date between 2013-01-01 and 2015-07-31 | Flag warning |
| Sales Negative Check | Sales Record | sales >= 0 | Reject record |
| Customers Negative Check | Sales Record | customers >= 0 | Reject record |
| Store Exists Check | Sales Record | store_id in Store table | Reject record |
| KPI Consistency Check | Daily KPI Mart | total_sales matches SUM(sales) for period | Flag error |
| Forecast Future Check | Forecast Result | forecast_date >= generated_at | Reject record |
| Confidence Order Check | Forecast Result | confidence_lower <= predicted_sales <= confidence_upper | Reject record |

### Data Quality Dashboard

A simple dashboard endpoint at `/api/v1/data-quality` returns:
- Total records by table
- Missing value counts
- Outlier counts
- Last validation timestamp
- Data freshness indicator
