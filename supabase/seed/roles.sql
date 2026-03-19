begin;

insert into internal.user_profiles (user_id, email, role)
values
  ('00000000-0000-0000-0000-000000000001', 'admin@example.com', 'admin'),
  ('00000000-0000-0000-0000-000000000002', 'analyst@example.com', 'data_analyst'),
  ('00000000-0000-0000-0000-000000000003', 'demo@example.com', 'academic_demo')
on conflict (user_id) do update
set
  email = excluded.email,
  role = excluded.role,
  updated_at = timezone('utc', now());

commit;
