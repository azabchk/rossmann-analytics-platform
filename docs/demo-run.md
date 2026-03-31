# Demo Runbook

This runbook is the minimum verified local path for the thesis demo MVP. It focuses on the working end-to-end slice:

```text
Rossmann CSVs -> ingestion -> internal tables -> daily KPIs -> baseline forecast publication -> FastAPI -> Next.js pages
```

## Prerequisites

- PostgreSQL available locally
- Python 3 with a virtual environment
- Node.js and npm
- Rossmann dataset files present as [`data/train.csv`](/home/azab-22/Desktop/DIPLOMA/data/train.csv) and [`data/store.csv`](/home/azab-22/Desktop/DIPLOMA/data/store.csv)

## Verified Environment

The local verification run used:

```text
database: rossmann_demo_ready_3
db user: rossmann_user
backend url: http://127.0.0.1:8010
frontend url: http://127.0.0.1:3000
jwt secret: demo-secret
```

You can use a different database name, but keep the same command structure.

## 1. Install Dependencies

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install
cd ..
```

## 2. Create the Database

```bash
createdb rossmann_demo_ready
for file in $(find supabase/migrations -maxdepth 1 -type f | sort); do
  psql -d rossmann_demo_ready -f "$file"
done
psql -d rossmann_demo_ready -f supabase/seed/roles.sql
psql -d rossmann_demo_ready -f supabase/seed/demo_users.sql
```

If you need explicit credentials:

```bash
PGPASSWORD=change_me psql -h localhost -U rossmann_user -d postgres -c 'create database rossmann_demo_ready;'
```

## 3. Ingest Rossmann Data

This is the approved data preparation entrypoint:

```bash
PYTHONPATH="$PWD/data" backend/.venv/bin/python - <<'PY'
from src.runs.run_ingestion import run_ingestion

run = run_ingestion(
    train_csv_path="data/train.csv",
    store_csv_path="data/store.csv",
    database_url="postgresql+psycopg2://rossmann_user:change_me@localhost:5432/rossmann_demo_ready",
    use_staging=True,
    upsert=False,
    promote_after_staging=True,
    triggered_by="demo-run",
)

print({
    "run_id": str(run.run_id),
    "status": run.status.value,
    "records_loaded": run.records_loaded,
})
PY
```

Expected result:
- status `completed`
- `internal.stores` populated
- `internal.sales_records` populated

## 4. Refresh Daily KPIs

Use the daily-only path for the demo:

```bash
PYTHONPATH="$PWD/data" backend/.venv/bin/python - <<'PY'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.marts.refresh_kpis import refresh_kpis

DATABASE_URL = "postgresql+asyncpg://rossmann_user:change_me@localhost:5432/rossmann_demo_ready"

async def main() -> None:
    engine = create_async_engine(DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await refresh_kpis(session, skip_periodic=True)
        print(result.to_dict())
    await engine.dispose()

asyncio.run(main())
PY
```

Expected result:
- `success: True`
- daily KPI rows inserted into `analytics.kpi_daily`

## 5. Publish Baseline Forecasts

This writes a governed model record plus published forecast rows into the `ml` schema:

```bash
backend/.venv/bin/python -m ml.src.publishing.run_baseline_publication \
  --database-url 'postgresql+psycopg2://rossmann_user:change_me@localhost:5432/rossmann_demo_ready' \
  --store-id 1 \
  --horizon-weeks 6 \
  --triggered-by demo-run
```

Expected result:
- one completed `ml.training_runs` row
- one active `ml.model_registry` baseline row
- one `ml.forecast_metadata` publication job row
- published rows in `ml.forecast_results`
- optional `ml.model_evaluations` row
- optional `ml.low_data_warnings` rows for undersized stores

## 6. Start the Backend

Run from [`backend/`](/home/azab-22/Desktop/DIPLOMA/backend):

```bash
SUPABASE_JWT_SECRET='demo-secret' \
DATABASE_URL='postgresql+asyncpg://rossmann_user:change_me@localhost:5432/rossmann_demo_ready' \
ENABLE_LOCAL_DEMO_AUTH=true \
.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8010
```

## 7. Start the Frontend

Run from [`frontend/`](/home/azab-22/Desktop/DIPLOMA/frontend):

```bash
NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8010' npm run dev
```

## 8. Use the Browser Login Helper

Open `http://127.0.0.1:3000/login` and click `Use local analyst demo access`.

This stores the seeded analyst token in browser storage for the protected MVP pages:
- `/dashboard`
- `/forecasts`

## 9. Mint a Demo JWT Manually

Example admin token:

```bash
backend/.venv/bin/python - <<'PY'
import jwt

payload = {
    "sub": "00000000-0000-0000-0000-000000000001",
    "email": "admin@example.com",
    "aud": "authenticated",
    "app_metadata": {"role": "admin"},
}

print(jwt.encode(payload, "demo-secret", algorithm="HS256"))
PY
```

Example analyst token:

```bash
backend/.venv/bin/python - <<'PY'
import jwt

payload = {
    "sub": "00000000-0000-0000-0000-000000000002",
    "email": "analyst@example.com",
    "aud": "authenticated",
    "app_metadata": {"role": "data_analyst"},
}

print(jwt.encode(payload, "demo-secret", algorithm="HS256"))
PY
```

Use the analyst token for the thesis demo flow if you want the least-privileged presentation path. The admin token is also valid for store-scoped backend reads and operational actions in the current backend.

## 10. Smoke-Test the API

Set the token once:

```bash
export TOKEN='paste-your-jwt-here'
```

Then run:

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8010/api/v1/stores
curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8010/api/v1/kpis?store_id=1&aggregation=daily&page=1&page_size=5"
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8010/api/v1/forecasts/stores/1
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8010/api/v1/forecasts/models/baseline/active
```

Admin or analyst can also trigger publication through FastAPI:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8010/api/v1/forecasts/generate \
  -d '{"store_ids":[1],"horizon_weeks":6,"force_retrain":false}'
```

## Available Pages

- `http://127.0.0.1:3000/`
- `http://127.0.0.1:3000/login`
- `http://127.0.0.1:3000/dashboard`
- `http://127.0.0.1:3000/forecasts`

## Known Limitations

- The demo path is intentionally daily-KPI-only. Weekly and monthly KPI refresh are not required for the current thesis MVP.
- The forecast generation path is the baseline model publication workflow only.
- The login page is a local demo helper and is not a full Supabase auth UI.
- Store comparison is not implemented in this frozen scope.
