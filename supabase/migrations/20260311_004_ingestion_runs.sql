begin;

create extension if not exists "pgcrypto";

alter table if exists internal.stores
  add column if not exists competition_open_since_month integer,
  add column if not exists competition_open_since_year integer,
  add column if not exists promo2_since_week integer,
  add column if not exists promo2_since_year integer,
  add column if not exists promo_interval text;

alter table if exists internal.sales_records
  add column if not exists day_of_week integer;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'stores_competition_open_since_month_check'
  ) then
    alter table internal.stores
      add constraint stores_competition_open_since_month_check
      check (
        competition_open_since_month is null
        or competition_open_since_month between 1 and 12
      );
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'stores_promo2_since_week_check'
  ) then
    alter table internal.stores
      add constraint stores_promo2_since_week_check
      check (
        promo2_since_week is null
        or promo2_since_week between 1 and 52
      );
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'sales_records_day_of_week_check'
  ) then
    alter table internal.sales_records
      add constraint sales_records_day_of_week_check
      check (day_of_week between 1 and 7);
  end if;
end $$;

create table if not exists internal.ingestion_runs (
  run_id uuid primary key default gen_random_uuid(),
  status text not null check (
    status in ('pending', 'running', 'validating', 'transforming', 'loading', 'completed', 'failed', 'cancelled')
  ),
  train_csv_path text,
  store_csv_path text,
  train_record_count integer not null default 0,
  store_record_count integer not null default 0,
  records_normalized integer not null default 0,
  records_loaded integer not null default 0,
  records_failed integer not null default 0,
  error_message text,
  error_traceback text,
  triggered_by text,
  parameters jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  duration_seconds numeric(12, 3),
  has_validation_errors boolean not null default false,
  total_error_count integer not null default 0,
  total_warning_count integer not null default 0,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_ingestion_runs_status on internal.ingestion_runs(status);
create index if not exists idx_ingestion_runs_started_at on internal.ingestion_runs(started_at desc);

create table if not exists internal.ingestion_validation_results (
  result_id uuid primary key default gen_random_uuid(),
  run_id uuid not null references internal.ingestion_runs(run_id) on delete cascade,
  table_name text not null,
  total_records integer not null default 0,
  valid_records integer not null default 0,
  error_count integer not null default 0,
  warning_count integer not null default 0,
  issues jsonb not null default '[]'::jsonb,
  warnings jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  unique (run_id, table_name)
);

create table if not exists internal.ingestion_validation_issues (
  issue_id uuid primary key default gen_random_uuid(),
  result_id uuid not null references internal.ingestion_validation_results(result_id) on delete cascade,
  run_id uuid not null references internal.ingestion_runs(run_id) on delete cascade,
  issue_type text not null,
  severity text not null check (severity in ('error', 'warning', 'info')),
  table_name text not null,
  row_identifier text,
  field_name text,
  actual_value text,
  expected_value text,
  message text not null,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_ingestion_validation_results_run_id
  on internal.ingestion_validation_results(run_id);
create index if not exists idx_ingestion_validation_issues_run_id
  on internal.ingestion_validation_issues(run_id);
create index if not exists idx_ingestion_validation_issues_severity
  on internal.ingestion_validation_issues(severity);

create table if not exists internal.stores_staging (
  store_id integer primary key,
  store_type text not null check (store_type in ('A', 'B', 'C', 'D')),
  assortment text not null check (assortment in ('a', 'b', 'c')),
  competition_distance integer not null check (competition_distance >= 0),
  competition_open_since_month integer null check (
    competition_open_since_month is null
    or competition_open_since_month between 1 and 12
  ),
  competition_open_since_year integer null,
  promo2 boolean not null default false,
  promo2_since_week integer null check (
    promo2_since_week is null
    or promo2_since_week between 1 and 52
  ),
  promo2_since_year integer null,
  promo_interval text null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists internal.sales_records_staging (
  sales_record_id bigserial primary key,
  store_id integer not null references internal.stores_staging(store_id) on delete cascade,
  sales_date date not null,
  day_of_week integer not null check (day_of_week between 1 and 7),
  sales integer not null check (sales >= 0),
  customers integer null check (customers is null or customers >= 0),
  is_open boolean not null,
  promo boolean not null,
  state_holiday text null,
  school_holiday boolean not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (store_id, sales_date)
);

create index if not exists idx_stores_store_type on internal.stores(store_type);
create index if not exists idx_stores_staging_store_type on internal.stores_staging(store_type);
create index if not exists idx_sales_records_staging_store_date
  on internal.sales_records_staging(store_id, sales_date);

comment on table internal.ingestion_runs is 'Run-level metadata for Rossmann ingestion executions.';
comment on table internal.ingestion_validation_results is 'Aggregated validation outcome per logical table.';
comment on table internal.ingestion_validation_issues is 'Detailed validation issues per ingestion run.';
comment on table internal.stores_staging is 'Restricted staging table for normalized store metadata.';
comment on table internal.sales_records_staging is 'Restricted staging table for normalized sales records.';
comment on column internal.stores.competition_open_since_month is 'Normalized competitor opening month from Rossmann store.csv.';
comment on column internal.stores.competition_open_since_year is 'Normalized competitor opening year from Rossmann store.csv.';
comment on column internal.stores.promo2_since_week is 'Normalized Promo2 start week from Rossmann store.csv.';
comment on column internal.stores.promo2_since_year is 'Normalized Promo2 start year from Rossmann store.csv.';
comment on column internal.stores.promo_interval is 'Normalized Promo2 interval string from Rossmann store.csv.';
comment on column internal.sales_records.day_of_week is 'ISO weekday derived from the sales_date column.';

commit;
