begin;

insert into internal.stores (store_id, store_type, assortment, competition_distance, promo2)
values (1, 'A', 'a', 500, false)
on conflict (store_id) do nothing;

insert into internal.store_access (user_id, store_id)
values
  ('00000000-0000-0000-0000-000000000002', 1),
  ('00000000-0000-0000-0000-000000000003', 1)
on conflict (user_id, store_id) do nothing;

commit;
