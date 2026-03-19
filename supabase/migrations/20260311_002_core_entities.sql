begin;

create table if not exists internal.user_profiles (
  user_id uuid primary key,
  email text not null unique,
  role text not null check (role in ('admin', 'store_manager', 'marketing_manager', 'data_analyst', 'academic_demo')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists internal.stores (
  store_id integer primary key,
  store_type text not null check (store_type in ('A', 'B', 'C', 'D')),
  assortment text not null check (assortment in ('a', 'b', 'c')),
  competition_distance integer not null check (competition_distance >= 0),
  promo2 boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists internal.store_access (
  access_id bigserial primary key,
  user_id uuid not null,
  store_id integer not null references internal.stores(store_id) on delete cascade,
  created_at timestamptz not null default timezone('utc', now()),
  unique (user_id, store_id)
);

create table if not exists internal.sales_records (
  sales_record_id bigserial primary key,
  store_id integer not null references internal.stores(store_id) on delete cascade,
  sales_date date not null,
  sales integer not null check (sales >= 0),
  customers integer null check (customers is null or customers >= 0),
  is_open boolean not null,
  promo boolean not null default false,
  state_holiday text null,
  school_holiday boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (store_id, sales_date)
);

create index if not exists idx_store_access_user_id on internal.store_access(user_id);
create index if not exists idx_store_access_store_id on internal.store_access(store_id);
create index if not exists idx_sales_records_store_date on internal.sales_records(store_id, sales_date);

commit;
