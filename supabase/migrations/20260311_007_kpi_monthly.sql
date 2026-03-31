begin;

create table if not exists analytics.kpi_monthly (
  kpi_id bigserial primary key,
  store_id integer not null references internal.stores(store_id) on delete cascade,
  year integer not null check (year >= 2013 and year <= 2099),
  month integer not null check (month between 1 and 12),
  month_name text not null check (
    month_name in (
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    )
  ),
  total_sales numeric(14, 2) not null default 0 check (total_sales >= 0),
  total_customers integer not null default 0 check (total_customers >= 0),
  total_transactions integer not null default 0 check (total_transactions >= 0),
  avg_daily_sales numeric(12, 2),
  avg_daily_customers numeric(12, 2),
  avg_daily_transactions numeric(12, 2),
  days_in_month integer not null check (days_in_month between 28 and 31),
  promo_days_count integer not null default 0 check (promo_days_count >= 0),
  holiday_days_count integer not null default 0 check (holiday_days_count >= 0),
  open_days_count integer not null default 0 check (open_days_count >= 0),
  closed_days_count integer not null default 0 check (closed_days_count >= 0),
  active_weeks_count integer not null default 0 check (active_weeks_count between 1 and 6),
  best_sales_day_date date,
  best_sales_amount numeric(14, 2),
  worst_sales_day_date date,
  worst_sales_amount numeric(14, 2),
  mom_sales_growth_pct numeric(8, 2),
  mom_customers_growth_pct numeric(8, 2),
  yoy_sales_growth_pct numeric(8, 2),
  yoy_customers_growth_pct numeric(8, 2),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (store_id, year, month)
);

create index if not exists idx_kpi_monthly_store_month on analytics.kpi_monthly(store_id, year desc, month desc);
create index if not exists idx_kpi_monthly_year_month on analytics.kpi_monthly(year, month);

alter table analytics.kpi_monthly enable row level security;

drop policy if exists kpi_monthly_access_filter on analytics.kpi_monthly;
create policy kpi_monthly_access_filter
  on analytics.kpi_monthly
  for select
  using (
    exists (
      select 1
      from internal.store_access sa
      where sa.user_id = auth.uid()
        and sa.store_id = analytics.kpi_monthly.store_id
    )
  );

create or replace function analytics.touch_kpi_monthly_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists touch_kpi_monthly_updated_at on analytics.kpi_monthly;
create trigger touch_kpi_monthly_updated_at
  before update on analytics.kpi_monthly
  for each row
  execute function analytics.touch_kpi_monthly_updated_at();

comment on table analytics.kpi_monthly is 'Monthly KPI mart derived from analytics.kpi_daily.';

commit;
