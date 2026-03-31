# ML

Machine learning module for offline forecast preparation, model evaluation, and
forecast publication.

**Current status**: Phase 5 forecast workflow is implemented for the approved
MVP path. The module now supports governed feature preparation, baseline model
training and publication, candidate-model interfaces, model evaluation, active
model selection, and persisted forecast output publication.

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

## Implemented Workflow

1. Prepared sales data is read from the governed operational layer.
2. Forecast features are generated in the `features` module.
3. A baseline model is trained first as the minimum dependable forecast path.
4. Candidate model workflows for Prophet and XGBoost remain separated from the
   online serving boundary.
5. Evaluation metrics are persisted and used for active-model selection.
6. Published forecasts, low-data warnings, and model metadata are written to
   the controlled `ml` schema.
7. Backend forecast endpoints serve only persisted outputs and metadata.

## Publication Expectations

- Training is offline and reproducible, not request-driven from the frontend.
- Published models must carry version, evaluation, and artifact metadata.
- Forecast outputs must be persisted before the backend serves them.
- Low-data conditions must be recorded explicitly rather than hidden.
- Artifact handling must remain within trusted backend, data, or ML paths.
