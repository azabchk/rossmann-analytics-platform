# API Overview

This document describes the minimum API surface that is part of the thesis demo MVP as of March 28, 2026. The backend is the only supported business boundary. The frontend, scripts, and any demo clients must call FastAPI instead of querying privileged database schemas directly.

## Base URL

Local verified backend base URL:

```text
http://127.0.0.1:8010/api/v1
```

All protected endpoints require a Bearer token signed with `SUPABASE_JWT_SECRET`.

## Authentication

### `GET /auth/me`

Returns the authenticated user context resolved from the JWT.

Response fields:
- `user_id`
- `email`
- `role`

### `POST /auth/demo-token`

Returns the seeded analyst demo token for local browser use when `ENABLE_LOCAL_DEMO_AUTH=true`.

Response fields:
- `access_token`
- `token_type`
- `user_id`
- `email`
- `role`

## Stores

### `GET /stores`

Returns stores accessible to the authenticated user.

Note:
- access is driven by `internal.store_access`
- admin requests are handled as privileged backend access and are not limited by explicit store mappings

### `GET /stores/{store_id}`

Returns one authorized store.

## Sales

### `GET /sales`

Returns governed historical sales from `internal.sales_records`.

Supported query parameters:
- `store_id`
- `start_date`
- `end_date`
- `page`
- `page_size`

### `GET /sales/summary`

Returns summary metrics for one authorized store.

Supported query parameters:
- `store_id`
- `start_date`
- `end_date`

## KPIs

The dashboard MVP is built on `analytics.kpi_daily`.

### `GET /kpis`

Returns KPI rows based on the requested aggregation.

Supported query parameters:
- `aggregation`
- `store_id`
- `start_date`
- `end_date`
- `year`
- `page`
- `page_size`

Verified demo value:
- `aggregation=daily`

### `GET /kpis/daily`

Daily KPI rows for authorized stores.

### `GET /kpis/summary`

Daily KPI summary for one authorized store.

Supported query parameters:
- `store_id`
- `start_date`
- `end_date`

## Forecasts

The forecasting MVP serves published forecast outputs only. Training and evaluation stay in the offline `ml` module; retrieval and controlled generation are exposed through FastAPI.

### `GET /forecasts/stores/{store_id}`

Returns the published forecast for one authorized store.

Response fields include:
- `store_id`
- `model_type`
- `forecast_start_date`
- `forecast_end_date`
- `model_metadata`
- `accuracy_metrics`
- `forecasts`
- `total`
- `offset`
- `limit`

Supported query parameters:
- `start_date`
- `end_date`
- `limit`
- `offset`

### `POST /forecasts/batch`

Returns published forecasts for multiple authorized stores.

Request body:

```json
{
  "store_ids": [1, 2],
  "forecast_start_date": "2015-08-01",
  "forecast_end_date": "2015-08-14"
}
```

### `GET /forecasts/models/{model_type}/active`

Returns the active published model metadata.

Supported model types:
- `baseline`
- `prophet`
- `xgboost`

Verified demo value:
- `baseline`

### `GET /forecasts/warnings/{store_id}`

Returns low-data warnings for one authorized store.

### `GET /forecasts/accuracy/{model_id}`

Returns persisted model evaluation metrics.

### `POST /forecasts/generate`

Triggers the bounded forecast publication workflow.

Allowed roles:
- `admin`
- `data_analyst`

Request body:

```json
{
  "store_ids": [1],
  "horizon_weeks": 6,
  "force_retrain": false
}
```

Current MVP behavior:
- `force_retrain` is accepted by the schema but not used by the baseline publication path
- the verified demo path publishes baseline forecasts from prepared database data

Detailed forecast design notes: [forecasts.md](/home/azab-22/Desktop/DIPLOMA/docs/api/forecasts.md)

## Available Frontend Pages

The current frontend is intentionally thin and API-driven.

Available pages:
- `/`
- `/login`
- `/dashboard`
- `/forecasts`

## Known Limitations

- Weekly and monthly KPI endpoints exist, but daily KPIs are the only verified demo-ready dashboard path.
- Forecast generation in the MVP uses the baseline publication workflow only.
- The login page provides a local demo helper only and does not implement full browser-side auth flows.
