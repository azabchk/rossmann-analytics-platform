# Forecasts API

This document defines the approved Phase 5 forecast API surface for the Analytical Platform for an Online Store with Sales Forecasting. It documents how persisted forecast outputs, model metadata, and low-data warnings are served through the FastAPI boundary. The frontend and any analyst-facing clients must use these endpoints instead of connecting directly to Supabase tables or Storage.

## Architectural Role

The forecasts API exists to expose governed forecast results that have already been generated and persisted by the offline ML workflow. This is a deliberate architectural decision. Training, model evaluation, active-model selection, and publication happen offline in the `ml` module. User-facing retrieval happens online in the backend API. This separation keeps forecast-serving predictable, auditable, and secure.

The API therefore serves three distinct concerns. First, it returns published forecast points with confidence bounds and model metadata for authorized stores. Second, it exposes low-data warnings and evaluation metrics so users can understand when predictions should be interpreted cautiously. Third, it supports a bounded backend-controlled generation trigger for approved operational use, without turning the user-facing API into an experimentation surface.

## Security and Access Model

All forecast endpoints are authenticated. Store-scoped retrieval must respect the same backend-first authorization rules used elsewhere in the platform. A caller may only retrieve forecasts or warnings for stores they are authorized to access, unless they hold an administrator role with broader operational permissions. This rule is enforced in the backend service layer and must not be delegated to the frontend.

The API does not expose privileged database credentials, service-role keys, or direct access to the `ml` schema. Persisted forecasts remain in controlled storage and are projected outward through validated response models. This preserves the locked architecture decision that the frontend consumes business data only through FastAPI.

## Endpoint Summary

### `GET /api/v1/forecasts/stores/{store_id}`

Returns the published forecast for one authorized store. The response includes the store identifier, forecast horizon dates, model metadata, optional evaluation metrics, paginated forecast points, and pagination metadata. Optional query parameters allow narrowing the served range:

- `start_date`
- `end_date`
- `limit`
- `offset`

If no published forecast is available for the requested store and date range, the endpoint returns `404 Not Found`. This is an intentional signal that forecast publication has not yet produced a governed output for the request, not that the API itself is malfunctioning.

### `POST /api/v1/forecasts/batch`

Returns governed forecast results for multiple authorized stores in one request. The request body contains:

- `store_ids`
- optional `forecast_start_date`
- optional `forecast_end_date`

The response groups forecasts by store and returns any active low-data warnings alongside them. This endpoint is suitable for summary or multi-store use cases, but it still respects authorization boundaries and returns only stores the caller is allowed to access.

### `GET /api/v1/forecasts/models/{model_type}/active`

Returns the active published model metadata for a supported model type:

- `baseline`
- `prophet`
- `xgboost`

This endpoint exists to make the active model selection explicit and inspectable. It supports academic defensibility by allowing reviewers and maintainers to see which model type is currently serving predictions.

### `GET /api/v1/forecasts/warnings/{store_id}`

Returns active warning records for a specific authorized store. Warnings are currently focused on low-data conditions such as insufficient historical coverage. These warnings are not decorative; they are part of the forecast-governance model and help communicate forecast limitations clearly.

### `GET /api/v1/forecasts/accuracy/{model_id}`

Returns evaluation metrics for a published model, including MAPE, RMSE, and MAE where available. These metrics come from persisted evaluation records rather than on-the-fly recalculation. This keeps forecast retrieval lightweight while preserving traceability to the offline evaluation process.

### `POST /api/v1/forecasts/generate`

Accepts a bounded generation request for approved operational roles. The request body contains:

- `store_ids`
- `horizon_weeks`
- optional `force_retrain`

In the approved MVP path, this trigger is implemented as a controlled publication workflow that writes governed outputs into the `ml` schema. It must not become an unrestricted user-driven retraining interface. The purpose of this endpoint is operational publication, not open-ended experimentation.

## Response Expectations

Forecast responses should always include enough context to explain the prediction source and the reliability signal:

- forecast dates
- predicted sales
- lower and upper confidence bounds where available
- confidence level
- model metadata
- evaluation metrics where available
- low-data warnings when relevant

This is especially important for thesis defense. The platform is not designed to emit unexplained numbers. Every published prediction should be paired with enough metadata to justify how it was produced and how strongly it should be trusted.

## Error Handling

The forecasts API uses the shared backend error envelope for application-level failures. Typical cases include:

- `401` for missing or invalid authentication
- `403` for unauthorized store access or restricted generation rights
- `404` when no published forecast or evaluation is available
- `400` for backend-level validation failures
- `422` for request-shape validation enforced by FastAPI and Pydantic

Frontend behavior should distinguish between these cases. In particular, `404` for missing forecast data should typically be shown as an empty governed state rather than a generic connectivity failure.
