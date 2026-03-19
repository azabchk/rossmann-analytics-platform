begin;

alter table internal.user_profiles enable row level security;
alter table internal.store_access enable row level security;
alter table internal.stores enable row level security;
alter table internal.sales_records enable row level security;

drop policy if exists user_profiles_self_select on internal.user_profiles;
create policy user_profiles_self_select
  on internal.user_profiles
  for select
  using (auth.uid() = user_id);

drop policy if exists store_access_self_select on internal.store_access;
create policy store_access_self_select
  on internal.store_access
  for select
  using (auth.uid() = user_id);

drop policy if exists stores_access_select on internal.stores;
create policy stores_access_select
  on internal.stores
  for select
  using (
    exists (
      select 1
      from internal.store_access sa
      where sa.user_id = auth.uid()
        and sa.store_id = internal.stores.store_id
    )
  );

drop policy if exists sales_records_access_select on internal.sales_records;
create policy sales_records_access_select
  on internal.sales_records
  for select
  using (
    exists (
      select 1
      from internal.store_access sa
      where sa.user_id = auth.uid()
        and sa.store_id = internal.sales_records.store_id
    )
  );

commit;
