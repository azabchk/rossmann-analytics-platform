begin;

create table if not exists analytics.kpi_weekly (
  kpi_id bigserial primary key,
  store_id integer not null references internal.stores(store_id) on delete cascade,
  week_start_date date not null,
  week_end_date date not null,
  iso_week integer not null check (iso_week between 1 and 53),
  year integer not null,
  total_sales numeric(14, 2) not null default 0 check (total_sales >= 0),
  total_customers integer not null default 0 check (total_customers >= 0),
  total_transactions integer not null default 0 check (total_transactions >= 0),
  avg_daily_sales numeric(12, 2),
  avg_daily_customers numeric(12, 2),
  avg_daily_transactions numeric(12, 2),
  promo_days_count integer not null default 0 check (promo_days_count >= 0),
  holiday_days_count integer not null default 0 check (holiday_days_count >= 0),
  open_days_count integer not null default 0 check (open_days_count >= 0),
  closed_days_count integer not null default 0 check (closed_days_count >= 0),
  best_sales_day_date date,
  best_sales_amount numeric(14, 2),
  worst_sales_day_date date,
  worst_sales_amount numeric(14, 2),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (store_id, week_start_date)
);

create index if not exists idx_kpi_weekly_store_week on analytics.kpi_weekly(store_id, week_start_date desc);
create index if not exists idx_kpi_weekly_year_week on analytics.kpi_weekly(year, iso_week);

alter table analytics.kpi_weekly enable row level security;

drop policy if exists kpi_weekly_access_filter on analytics.kpi_weekly;
create policy kpi_weekly_access_filter
  on analytics.kpi_weekly
  for select
  using (
    exists (
      select 1
      from internal.store_access sa
      where sa.user_id = auth.uid()
        and sa.store_id = analytics.kpi_weekly.store_id
    )
  );

create or replace function analytics.touch_kpi_weekly_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists touch_kpi_weekly_updated_at on analytics.kpi_weekly;
create trigger touch_kpi_weekly_updated_at
  before update on analytics.kpi_weekly
  for each row
  execute function analytics.touch_kpi_weekly_updated_at();

comment on table analytics.kpi_weekly is 'Weekly KPI mart derived from analytics.kpi_daily.';

commit;
