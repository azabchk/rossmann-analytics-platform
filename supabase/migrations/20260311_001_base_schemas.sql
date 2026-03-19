begin;

create schema if not exists internal;
create schema if not exists analytics;
create schema if not exists ml;

revoke create on schema public from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    execute 'revoke all on schema public from anon';
    execute 'revoke all on schema internal from anon';
    execute 'revoke all on schema analytics from anon';
    execute 'revoke all on schema ml from anon';
  end if;

  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    execute 'revoke all on schema public from authenticated';
    execute 'revoke all on schema internal from authenticated';
    execute 'revoke all on schema analytics from authenticated';
    execute 'revoke all on schema ml from authenticated';
  end if;

  if exists (select 1 from pg_roles where rolname = 'service_role') then
    execute 'grant usage on schema public to service_role';
    execute 'grant usage on schema internal to service_role';
    execute 'grant usage on schema analytics to service_role';
    execute 'grant usage on schema ml to service_role';
  end if;
end
$$;

comment on schema internal is 'Restricted operational schema for validated source-aligned data and pipeline state.';
comment on schema analytics is 'Controlled analytical schema for KPI marts and read-optimized views.';
comment on schema ml is 'Restricted ML schema for model metadata and persisted forecast outputs.';

commit;
