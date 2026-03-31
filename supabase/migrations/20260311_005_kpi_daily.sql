begin;

create table if not exists analytics.kpi_daily (
  kpi_id bigserial primary key,
  store_id integer not null references internal.stores(store_id) on delete cascade,
  kpi_date date not null,
  day_of_week integer not null check (day_of_week between 1 and 7),
  total_sales numeric(14, 2) not null default 0 check (total_sales >= 0),
  total_customers integer not null default 0 check (total_customers >= 0),
  transactions integer not null default 0 check (transactions >= 0),
  avg_sales_per_transaction numeric(12, 2),
  sales_per_customer numeric(12, 2),
  is_promo_day boolean not null default false,
  has_state_holiday boolean not null default false,
  has_school_holiday boolean not null default false,
  is_store_open boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (store_id, kpi_date)
);

create index if not exists idx_kpi_daily_store_date on analytics.kpi_daily(store_id, kpi_date desc);
create index if not exists idx_kpi_daily_date on analytics.kpi_daily(kpi_date desc);
create index if not exists idx_kpi_daily_day_of_week on analytics.kpi_daily(day_of_week);

alter table analytics.kpi_daily enable row level security;

drop policy if exists kpi_daily_access_filter on analytics.kpi_daily;
create policy kpi_daily_access_filter
  on analytics.kpi_daily
  for select
  using (
    exists (
      select 1
      from internal.store_access sa
      where sa.user_id = auth.uid()
        and sa.store_id = analytics.kpi_daily.store_id
    )
  );

create or replace function analytics.touch_kpi_daily_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists touch_kpi_daily_updated_at on analytics.kpi_daily;
create trigger touch_kpi_daily_updated_at
  before update on analytics.kpi_daily
  for each row
  execute function analytics.touch_kpi_daily_updated_at();

comment on table analytics.kpi_daily is 'Daily KPI mart for dashboard and KPI API retrieval.';
comment on column analytics.kpi_daily.transactions is 'Count of operational sales rows contributing to the day.';

commit;
