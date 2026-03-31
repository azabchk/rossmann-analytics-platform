begin;

-- Training runs table to track model training execution
create table if not exists ml.training_runs (
  run_id uuid primary key default gen_random_uuid(),
  run_name text not null,
  model_type text not null check (model_type in ('baseline', 'prophet', 'xgboost')),
  status text not null check (status in ('pending', 'running', 'completed', 'failed')),
  dataset_version text not null,
  feature_version text,
  parameters jsonb,
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz,
  error_message text,
  created_at timestamptz not null default timezone('utc', now())
);

-- Model registry table for tracking published models
create table if not exists ml.model_registry (
  model_id uuid primary key default gen_random_uuid(),
  model_name text not null unique,
  model_type text not null check (model_type in ('baseline', 'prophet', 'xgboost')),
  training_run_id uuid references ml.training_runs(run_id) on delete set null,
  is_active boolean not null default false,
  version text not null,
  artifact_path text,
  artifact_hash text,
  metadata jsonb,
  published_at timestamptz not null default timezone('utc', now()),
  created_at timestamptz not null default timezone('utc', now())
);

-- Model evaluation metrics table
create table if not exists ml.model_evaluations (
  evaluation_id uuid primary key default gen_random_uuid(),
  model_id uuid references ml.model_registry(model_id) on delete cascade,
  evaluation_period_start date not null,
  evaluation_period_end date not null,
  mape numeric(10, 4) check (mape >= 0),
  rmse numeric(15, 4) check (rmse >= 0),
  mae numeric(15, 4) check (mae >= 0),
  eval_metrics jsonb,
  evaluation_date timestamptz not null default timezone('utc', now()),
  created_at timestamptz not null default timezone('utc', now())
);

-- Indexes for common query patterns
create index if not exists idx_training_runs_status on ml.training_runs(status);
create index if not exists idx_training_runs_model_type on ml.training_runs(model_type);
create index if not exists idx_model_registry_type on ml.model_registry(model_type);
create index if not exists idx_model_registry_is_active on ml.model_registry(is_active);
create index if not exists idx_model_evaluations_model on ml.model_evaluations(model_id);

-- Ensure only one active model per model type
create unique index if not exists idx_unique_active_model_type
  on ml.model_registry(model_type)
  where is_active = true;

comment on table ml.training_runs is 'Tracks execution of ML model training jobs with status and parameters.';
comment on table ml.model_registry is 'Registry of trained models with artifact references and active flags.';
comment on table ml.model_evaluations is 'Stores evaluation metrics for models on holdout test sets.';

commit;
