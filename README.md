# Analytical Platform for an Online Store with Sales Forecasting

## Current Status

Status on March 28, 2026: minimum thesis MVP stabilized for demo use.

Verified MVP scope:
- Rossmann CSV ingestion into governed PostgreSQL tables
- Daily KPI mart refresh for dashboard analytics
- Baseline forecast publication from prepared data into persisted `ml` tables
- FastAPI endpoints for auth context, stores, KPIs, sales history, and forecasts
- Next.js pages for home, local demo login helper, dashboard, and forecasts

Frozen out of this finish pass:
- store comparison
- advanced API enhancements outside the forecast path
- nonessential refactors and broad UI polish

## Architecture

The project keeps the approved headless modular monolith architecture:
- `data/` handles ingestion, validation, normalization, and KPI mart refresh
- `ml/` handles offline forecasting and publication
- `backend/` is the only business API boundary
- `frontend/` is a thin presentation layer that consumes FastAPI only
- `supabase/` contains PostgreSQL-compatible migrations, policies, and seeds

The frontend does not talk directly to privileged schemas. Forecasts and KPI data are served through FastAPI.

## Repository Layout

```text
DIPLOMA/
├── backend/     FastAPI backend and API tests
├── data/        Rossmann ingestion and KPI mart builders
├── docs/        Architecture, API, and demo run documentation
├── frontend/    Next.js presentation layer
├── ml/          Forecast training, evaluation, and publication
├── specs/       Spec Kit scope and task tracking
└── supabase/    Migrations, policies, and seed SQL
```

## Quick Start

### 1. Install dependencies

Backend, data, and ML share the backend virtual environment in the verified local path:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install
```

### 2. Configure environment

Start from [`.env.example`](/home/azab-22/Desktop/DIPLOMA/.env.example) and set at minimum:

```dotenv
DATABASE_URL=postgresql+asyncpg://rossmann_user:change_me@localhost:5432/rossmann_demo_ready
SUPABASE_JWT_SECRET=replace-with-local-jwt-secret
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8010
```

### 3. Prepare the database

Apply migrations and seed demo data:

```bash
createdb rossmann_demo_ready
for file in $(find supabase/migrations -maxdepth 1 -type f | sort); do
  psql -d rossmann_demo_ready -f "$file"
done
psql -d rossmann_demo_ready -f supabase/seed/roles.sql
psql -d rossmann_demo_ready -f supabase/seed/demo_users.sql
```

### 4. Ingest Rossmann data

Place `train.csv` and `store.csv` in [`data/`](/home/azab-22/Desktop/DIPLOMA/data), then run:

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
    triggered_by="local-demo",
)
print(run.run_id, run.status.value, run.records_loaded)
PY
```

### 5. Refresh dashboard KPIs

Use the verified daily-only refresh path:

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

### 6. Publish baseline forecasts

```bash
backend/.venv/bin/python -m ml.src.publishing.run_baseline_publication \
  --database-url 'postgresql+psycopg2://rossmann_user:change_me@localhost:5432/rossmann_demo_ready' \
  --store-id 1 \
  --horizon-weeks 6 \
  --triggered-by local-demo
```

### 7. Start the backend

```bash
cd backend
SUPABASE_JWT_SECRET='replace-with-local-jwt-secret' \
DATABASE_URL='postgresql+asyncpg://rossmann_user:change_me@localhost:5432/rossmann_demo_ready' \
ENABLE_LOCAL_DEMO_AUTH=true \
.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8010
```

### 8. Start the frontend

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8010' npm run dev
```

## Demo Pages

Available pages in the current MVP:
- `/`
- `/login`
- `/dashboard`
- `/forecasts`

## API Surface

Current demo-relevant endpoints:
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/demo-token` local-only helper when `ENABLE_LOCAL_DEMO_AUTH=true`
- `GET /api/v1/stores`
- `GET /api/v1/stores/{store_id}`
- `GET /api/v1/sales`
- `GET /api/v1/sales/summary`
- `GET /api/v1/kpis`
- `GET /api/v1/kpis/daily`
- `GET /api/v1/kpis/summary`
- `GET /api/v1/forecasts/stores/{store_id}`
- `POST /api/v1/forecasts/batch`
- `GET /api/v1/forecasts/models/{model_type}/active`
- `GET /api/v1/forecasts/warnings/{store_id}`
- `GET /api/v1/forecasts/accuracy/{model_id}`
- `POST /api/v1/forecasts/generate`

API details: [docs/api/README.md](/home/azab-22/Desktop/DIPLOMA/docs/api/README.md)

## Demo Runbook

Exact local demo steps: [docs/demo-run.md](/home/azab-22/Desktop/DIPLOMA/docs/demo-run.md)

## Known Limitations

- The verified dashboard demo uses daily KPIs only. Weekly and monthly KPI refresh are not part of the approved demo path.
- Forecast generation currently publishes the baseline model path only.
- The frontend login page offers a local demo helper only and does not implement a full Supabase auth UI.
- Store comparison is intentionally out of scope for this frozen MVP.
