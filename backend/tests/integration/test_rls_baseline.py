from pathlib import Path


def test_base_schema_migration_defines_controlled_schemas():
    content = Path("supabase/migrations/20260311_001_base_schemas.sql").read_text()

    assert "create schema if not exists internal" in content.lower()
    assert "create schema if not exists analytics" in content.lower()
    assert "create schema if not exists ml" in content.lower()
    assert "revoke all on schema internal" in content.lower()


def test_rls_migration_enables_policies_for_internal_tables():
    content = Path("supabase/migrations/20260311_003_rls_baseline.sql").read_text().lower()

    assert "enable row level security" in content
    assert "create policy user_profiles_self_select" in content
    assert "create policy store_access_self_select" in content
