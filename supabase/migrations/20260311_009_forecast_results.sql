begin;

-- Forecast results table for storing generated predictions
create table if not exists ml.forecast_results (
  forecast_id uuid primary key default gen_random_uuid(),
  model_id uuid references ml.model_registry(model_id) on delete cascade,
  store_id integer not null references internal.stores(store_id) on delete cascade,
  forecast_date date not null,
  predicted_sales numeric(12, 2) not null check (predicted_sales >= 0),
  lower_bound numeric(12, 2) check (lower_bound is null or lower_bound >= 0),
  upper_bound numeric(12, 2) check (upper_bound is null or upper_bound >= 0),
  confidence_level numeric(5, 2) check (confidence_level > 0 and confidence_level <= 100),
  is_published boolean not null default false,
  generation_timestamp timestamptz not null default timezone('utc', now()),
  created_at timestamptz not null default timezone('utc', now()),
  unique (model_id, store_id, forecast_date)
);

-- Forecast metadata for tracking forecast generation jobs
create table if not exists ml.forecast_metadata (
  forecast_job_id uuid primary key default gen_random_uuid(),
  model_id uuid references ml.model_registry(model_id) on delete cascade,
  forecast_horizon_days integer not null,
  forecast_start_date date not null,
  forecast_end_date date not null,
  stores_included integer[] not null,
  total_forecasts_generated integer not null,
  job_status text not null check (job_status in ('pending', 'running', 'completed', 'failed')),
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz,
  error_message text,
  created_at timestamptz not null default timezone('utc', now())
);

-- Low data warning table for stores with insufficient historical data
create table if not exists ml.low_data_warnings (
  warning_id uuid primary key default gen_random_uuid(),
  store_id integer references internal.stores(store_id) on delete cascade,
  warning_type text not null check (warning_type in ('insufficient_history', 'sparse_data', 'high_variance')),
  days_of_history integer,
  warning_message text,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now())
);

-- Indexes for common query patterns
create index if not exists idx_forecast_results_model on ml.forecast_results(model_id);
create index if not exists idx_forecast_results_store_date on ml.forecast_results(store_id, forecast_date);
create index if not exists idx_forecast_results_is_published on ml.forecast_results(is_published);
create index if not exists idx_forecast_metadata_status on ml.forecast_metadata(job_status);
create index if not exists idx_forecast_metadata_model on ml.forecast_metadata(model_id);
create index if not exists idx_low_data_warnings_store on ml.low_data_warnings(store_id);
create index if not exists idx_low_data_warnings_active on ml.low_data_warnings(is_active);
create unique index if not exists uq_low_data_warnings_active_store_type
  on ml.low_data_warnings(store_id, warning_type)
  where is_active = true;

-- Index for efficient forecast retrieval by store and date range
create index if not exists idx_forecast_results_store_date_range
  on ml.forecast_results(store_id, forecast_date)
  where is_published = true;

comment on table ml.forecast_results is 'Stores generated forecast predictions with confidence intervals.';
comment on table ml.forecast_metadata is 'Metadata for forecast generation jobs tracking.';
comment on table ml.low_data_warnings is 'Warnings for stores with insufficient historical data for reliable forecasting.';

commit;
