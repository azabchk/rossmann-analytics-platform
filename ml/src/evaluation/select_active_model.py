"""Active model selection logic.

This module provides functions for selecting the active forecasting model
based on evaluation results and performance criteria.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

import numpy as np

from .evaluate_models import ModelEvaluationResult


@dataclass
class ActiveModelSelection:
    """Result of active model selection."""

    selected_model_type: str
    selected_model_id: str
    selection_reason: str
    fallback_used: bool
    fallback_model_type: Optional[str] = None


def select_active_model(
    evaluations: List[ModelEvaluationResult],
    primary_preference: str = "xgboost",
    fallback_model: str = "baseline",
    mape_threshold: float = 15.0,
    min_evaluations: int = 1,
) -> ActiveModelSelection:
    """Select the active model based on evaluation results.

    Selection logic:
    1. If primary preference exists and performs well (MAPE < threshold), use it
    2. Otherwise, check if any model performs well
    3. If no model performs well, use baseline as fallback

    Args:
        evaluations: List of evaluation results
        primary_preference: Preferred model type (e.g., 'xgboost', 'prophet')
        fallback_model: Fallback model type
        mape_threshold: Maximum acceptable MAPE
        min_evaluations: Minimum evaluations required for selection

    Returns:
        ActiveModelSelection with selected model
    """
    if len(evaluations) < min_evaluations:
        return ActiveModelSelection(
            selected_model_type=fallback_model,
            selected_model_id=f"model_{fallback_model}",
            selection_reason=f"Insufficient evaluations ({len(evaluations)} < {min_evaluations})",
            fallback_used=True,
            fallback_model_type=fallback_model,
        )

    # Group evaluations by model type
    evals_by_type: Dict[str, List[ModelEvaluationResult]] = {}
    for eval_result in evaluations:
        if eval_result.model_type not in evals_by_type:
            evals_by_type[eval_result.model_type] = []
        evals_by_type[eval_result.model_type].append(eval_result)

    # Calculate average performance by model type
    avg_mape_by_type: Dict[str, float] = {}
    for model_type, evals in evals_by_type.items():
        valid_mapes = [e.mape for e in evals if not np.isnan(e.mape)]
        if valid_mapes:
            avg_mape_by_type[model_type] = np.mean(valid_mapes)

    # Check if primary preference is available and performs well
    if primary_preference in avg_mape_by_type:
        primary_mape = avg_mape_by_type[primary_preference]
        if primary_mape < mape_threshold:
            # Find the evaluation result for the primary model
            primary_eval = next(
                (e for e in evaluations if e.model_type == primary_preference),
                evaluations[0],
            )
            return ActiveModelSelection(
                selected_model_type=primary_preference,
                selected_model_id=primary_eval.model_id,
                selection_reason=f"Primary model performs well (MAPE: {primary_mape:.2f}%)",
                fallback_used=False,
            )

    # Try to find any model that performs well
    for model_type, mape in sorted(avg_mape_by_type.items(), key=lambda x: x[1]):
        if mape < mape_threshold:
            model_eval = next(
                (e for e in evaluations if e.model_type == model_type),
                evaluations[0],
            )
            return ActiveModelSelection(
                selected_model_type=model_type,
                selected_model_id=model_eval.model_id,
                selection_reason=f"Model selected based on best performance (MAPE: {mape:.2f}%)",
                fallback_used=False,
            )

    # No model performs well, use baseline as fallback
    fallback_eval = next(
        (e for e in evaluations if e.model_type == fallback_model),
        evaluations[0] if evaluations else None,
    )

    if fallback_eval:
        fallback_mape = avg_mape_by_type.get(fallback_model, np.nan)
        reason = f"All models above threshold ({mape_threshold}%), using {fallback_model} fallback (MAPE: {fallback_mape:.2f}%)"
    else:
        reason = f"No evaluations available, using {fallback_model} fallback"

    return ActiveModelSelection(
        selected_model_type=fallback_model,
        selected_model_id=fallback_eval.model_id if fallback_eval else f"model_{fallback_model}",
        selection_reason=reason,
        fallback_used=True,
        fallback_model_type=fallback_model,
    )


def should_use_fallback(
    mape: float,
    rmse: float | None = None,
    mape_threshold: float = 15.0,
    threshold: float | None = None,
) -> bool:
    """Determine if fallback should be used based on metrics.

    Args:
        mape: Mean Absolute Percentage Error
        rmse: Root Mean Squared Error
        mape_threshold: MAPE threshold for acceptable performance

    Returns:
        True if fallback should be used
    """
    if threshold is not None:
        mape_threshold = threshold
    return mape > mape_threshold


def rank_models_by_performance(
    evaluations: List[ModelEvaluationResult],
    metric: str = "mape",
) -> List[ModelEvaluationResult]:
    """Rank models by performance metric.

    Args:
        evaluations: List of evaluation results
        metric: Metric to rank by ('mape', 'rmse', or 'mae')

    Returns:
        List of evaluations sorted by performance (best first)
    """
    if metric not in ["mape", "rmse", "mae"]:
        raise ValueError(f"Unknown metric: {metric}")

    valid_evals = [e for e in evaluations if not np.isnan(getattr(e, metric))]
    return sorted(valid_evals, key=lambda x: getattr(x, metric))
