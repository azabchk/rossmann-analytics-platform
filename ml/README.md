# ML

Machine learning module for offline forecast preparation, model evaluation, and
forecast publication.

**Current status**: Phase 1 package scaffolding only. Model logic is deferred to
the forecasting phase.

## Responsibility Boundary

- Feature preparation from governed data
- Baseline and stronger candidate model training
- Evaluation and active-model selection
- Forecast publication and artifact metadata persistence

## Must Not Do

- Expose a separate public API
- Bypass backend business boundaries
- Write experimental outputs directly to user-facing endpoints

## Planned Model Strategy

- Baseline statistical fallback for low-data or failure scenarios
- Prophet and/or XGBoost candidate models
- Persisted forecast outputs served through the backend

## Next Planned Work

- Feature engineering
- Baseline model training
- Candidate model evaluation
- Artifact publication to Supabase Storage
