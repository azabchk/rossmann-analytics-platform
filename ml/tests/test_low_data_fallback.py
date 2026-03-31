"""Tests for low data fallback behavior."""

import pytest
import pandas as pd
import numpy as np
from datetime import date


class TestActiveModelSelection:
    """Tests for active model selection logic."""

    def test_select_primary_model_with_good_performance(self):
        """Test selecting primary model when it performs well."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult
        from ml.src.evaluation.select_active_model import (
            select_active_model,
        )

        evaluations = [
            ModelEvaluationResult(
                model_type="xgboost",
                model_id="model_xgb_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=10.0,  # Below threshold
                rmse=50.0,
                mae=40.0,
            ),
            ModelEvaluationResult(
                model_type="baseline",
                model_id="model_base_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=20.0,
                rmse=80.0,
                mae=60.0,
            ),
        ]

        selection = select_active_model(
            evaluations,
            primary_preference="xgboost",
            mape_threshold=15.0,
        )

        assert selection.selected_model_type == "xgboost"
        assert selection.fallback_used is False
        assert "performs well" in selection.selection_reason.lower()

    def test_select_best_model_when_primary_performs_poorly(self):
        """Test selecting best alternative when primary performs poorly."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult
        from ml.src.evaluation.select_active_model import (
            select_active_model,
        )

        evaluations = [
            ModelEvaluationResult(
                model_type="xgboost",
                model_id="model_xgb_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=20.0,  # Above threshold
                rmse=80.0,
                mae=60.0,
            ),
            ModelEvaluationResult(
                model_type="prophet",
                model_id="model_prophet_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=10.0,  # Below threshold
                rmse=50.0,
                mae=40.0,
            ),
        ]

        selection = select_active_model(
            evaluations,
            primary_preference="xgboost",
            mape_threshold=15.0,
        )

        assert selection.selected_model_type == "prophet"
        assert selection.fallback_used is False
        assert "best performance" in selection.selection_reason.lower()

    def test_fallback_to_baseline_when_all_perform_poorly(self):
        """Test fallback to baseline when all models perform poorly."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult
        from ml.src.evaluation.select_active_model import (
            select_active_model,
        )

        evaluations = [
            ModelEvaluationResult(
                model_type="xgboost",
                model_id="model_xgb_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=25.0,  # Above threshold
                rmse=100.0,
                mae=80.0,
            ),
            ModelEvaluationResult(
                model_type="prophet",
                model_id="model_prophet_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=30.0,  # Above threshold
                rmse=120.0,
                mae=90.0,
            ),
            ModelEvaluationResult(
                model_type="baseline",
                model_id="model_base_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=18.0,  # Above threshold but baseline
                rmse=90.0,
                mae=70.0,
            ),
        ]

        selection = select_active_model(
            evaluations,
            primary_preference="xgboost",
            mape_threshold=15.0,
        )

        assert selection.selected_model_type == "baseline"
        assert selection.fallback_used is True
        assert selection.fallback_model_type == "baseline"
        assert "fallback" in selection.selection_reason.lower()

    def test_fallback_with_insufficient_evaluations(self):
        """Test fallback when there are insufficient evaluations."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult
        from ml.src.evaluation.select_active_model import (
            select_active_model,
        )

        evaluations = []  # Empty list

        selection = select_active_model(
            evaluations,
            primary_preference="xgboost",
            mape_threshold=15.0,
            min_evaluations=1,
        )

        assert selection.selected_model_type == "baseline"
        assert selection.fallback_used is True
        assert "insufficient evaluations" in selection.selection_reason.lower()


class TestShouldUseFallback:
    """Tests for should_use_fallback function."""

    def test_use_fallback_with_high_mape(self):
        """Test that high MAPE triggers fallback."""
        from ml.src.evaluation.select_active_model import should_use_fallback

        assert should_use_fallback(mape=20.0, threshold=15.0) is True

    def test_no_fallback_with_low_mape(self):
        """Test that low MAPE does not trigger fallback."""
        from ml.src.evaluation.select_active_model import should_use_fallback

        assert should_use_fallback(mape=10.0, threshold=15.0) is False

    def test_no_fallback_at_threshold(self):
        """Test that MAPE at threshold does not trigger fallback."""
        from ml.src.evaluation.select_active_model import should_use_fallback

        assert should_use_fallback(mape=15.0, threshold=15.0) is False


class TestRankModelsByPerformance:
    """Tests for ranking models by performance."""

    def test_rank_by_mape(self):
        """Test ranking models by MAPE."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult
        from ml.src.evaluation.select_active_model import (
            rank_models_by_performance,
        )

        evaluations = [
            ModelEvaluationResult(
                model_type="baseline",
                model_id="model_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=20.0,
                rmse=80.0,
                mae=60.0,
            ),
            ModelEvaluationResult(
                model_type="prophet",
                model_id="model_2",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=10.0,
                rmse=50.0,
                mae=40.0,
            ),
            ModelEvaluationResult(
                model_type="xgboost",
                model_id="model_3",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=15.0,
                rmse=60.0,
                mae=50.0,
            ),
        ]

        ranked = rank_models_by_performance(evaluations, metric="mape")

        assert len(ranked) == 3
        assert ranked[0].model_type == "prophet"
        assert ranked[1].model_type == "xgboost"
        assert ranked[2].model_type == "baseline"

    def test_rank_by_rmse(self):
        """Test ranking models by RMSE."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult
        from ml.src.evaluation.select_active_model import (
            rank_models_by_performance,
        )

        evaluations = [
            ModelEvaluationResult(
                model_type="baseline",
                model_id="model_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=20.0,
                rmse=90.0,
                mae=60.0,
            ),
            ModelEvaluationResult(
                model_type="prophet",
                model_id="model_2",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=10.0,
                rmse=50.0,
                mae=40.0,
            ),
        ]

        ranked = rank_models_by_performance(evaluations, metric="rmse")

        assert len(ranked) == 2
        assert ranked[0].model_type == "prophet"
        assert ranked[1].model_type == "baseline"

    def test_rank_filters_nan_metrics(self):
        """Test that ranking filters out NaN metrics."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult
        from ml.src.evaluation.select_active_model import (
            rank_models_by_performance,
        )

        evaluations = [
            ModelEvaluationResult(
                model_type="baseline",
                model_id="model_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=20.0,
                rmse=80.0,
                mae=60.0,
            ),
            ModelEvaluationResult(
                model_type="prophet",
                model_id="model_2",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=float("nan"),
                rmse=float("nan"),
                mae=float("nan"),
            ),
        ]

        ranked = rank_models_by_performance(evaluations, metric="mape")

        assert len(ranked) == 1
        assert ranked[0].model_type == "baseline"
