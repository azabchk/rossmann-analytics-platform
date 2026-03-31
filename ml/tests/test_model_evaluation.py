"""Tests for model evaluation."""

import pytest
import pandas as pd
import numpy as np
from datetime import date


class TestCalculateMetrics:
    """Tests for metric calculation functions."""

    def test_calculate_mape(self):
        """Test MAPE calculation."""
        from ml.src.evaluation.evaluate_models import calculate_mape

        actual = np.array([100, 200, 150, 180, 220])
        predicted = np.array([110, 190, 160, 170, 210])

        mape = calculate_mape(actual, predicted)

        assert 0 <= mape <= 100  # MAPE should be reasonable

    def test_calculate_mape_with_zeros(self):
        """Test MAPE calculation handles zeros in actual."""
        from ml.src.evaluation.evaluate_models import calculate_mape

        actual = np.array([0, 100, 200, 0, 150])
        predicted = np.array([10, 110, 190, 5, 160])

        mape = calculate_mape(actual, predicted)

        assert mape != np.inf  # Should handle zeros gracefully

    def test_calculate_rmse(self):
        """Test RMSE calculation."""
        from ml.src.evaluation.evaluate_models import calculate_rmse

        actual = np.array([100, 200, 150, 180, 220])
        predicted = np.array([110, 190, 160, 170, 210])

        rmse = calculate_rmse(actual, predicted)

        assert rmse >= 0

    def test_calculate_mae(self):
        """Test MAE calculation."""
        from ml.src.evaluation.evaluate_models import calculate_mae

        actual = np.array([100, 200, 150, 180, 220])
        predicted = np.array([110, 190, 160, 170, 210])

        mae = calculate_mae(actual, predicted)

        assert mae >= 0


class TestEvaluateForecast:
    """Tests for evaluate_forecast function."""

    def test_evaluate_forecast_basic(self):
        """Test basic forecast evaluation."""
        from ml.src.evaluation.evaluate_models import evaluate_forecast

        actual_df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=14),
            "sales": [100, 200, 150, 180, 220, 250, 200,
                       180, 210, 230, 240, 220, 260, 250],
        })

        forecast_df = pd.DataFrame({
            "forecast_date": pd.date_range("2023-01-01", periods=14),
            "predicted_sales": [110, 190, 160, 170, 210, 240, 190,
                            170, 200, 220, 230, 210, 250, 240],
        })

        metrics = evaluate_forecast(actual_df, forecast_df)

        assert "mape" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert metrics["mape"] >= 0
        assert metrics["rmse"] >= 0
        assert metrics["mae"] >= 0

    def test_evaluate_forecast_with_no_overlap(self):
        """Test evaluation with no date overlap returns NaN."""
        from ml.src.evaluation.evaluate_models import evaluate_forecast

        actual_df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=7),
            "sales": [100, 200, 150, 180, 220, 250, 200],
        })

        forecast_df = pd.DataFrame({
            "forecast_date": pd.date_range("2023-02-01", periods=7),
            "predicted_sales": [110, 190, 160, 170, 210, 240, 190],
        })

        metrics = evaluate_forecast(actual_df, forecast_df)

        assert np.isnan(metrics["mape"])
        assert np.isnan(metrics["rmse"])
        assert np.isnan(metrics["mae"])


class TestModelEvaluationResult:
    """Tests for ModelEvaluationResult dataclass."""

    def test_model_evaluation_result_creation(self):
        """Test creation of ModelEvaluationResult."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult

        result = ModelEvaluationResult(
            model_type="baseline",
            model_id="model_123",
            store_id=1,
            evaluation_period_start=date(2023, 1, 1),
            evaluation_period_end=date(2023, 1, 14),
            mape=10.5,
            rmse=50.2,
            mae=40.0,
        )

        assert result.model_type == "baseline"
        assert result.mape == 10.5
        assert result.rmse == 50.2
        assert result.mae == 40.0

    def test_model_evaluation_result_to_dict(self):
        """Test conversion to dictionary."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult

        result = ModelEvaluationResult(
            model_type="baseline",
            model_id="model_123",
            store_id=1,
            evaluation_period_start=date(2023, 1, 1),
            evaluation_period_end=date(2023, 1, 14),
            mape=10.5,
            rmse=50.2,
            mae=40.0,
        )

        result_dict = result.to_dict()

        assert result_dict["model_type"] == "baseline"
        assert result_dict["mape"] == 10.5
        assert result_dict["evaluation_period_start"] == "2023-01-01"


class TestCompareModels:
    """Tests for model comparison functions."""

    def test_compare_models(self):
        """Test comparing multiple models."""
        from ml.src.evaluation.evaluate_models import ModelEvaluationResult, compare_models

        evaluations = [
            ModelEvaluationResult(
                model_type="baseline",
                model_id="model_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=15.0,
                rmse=60.0,
                mae=50.0,
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
                mape=8.0,
                rmse=45.0,
                mae=35.0,
            ),
        ]

        comparison = compare_models(evaluations)

        assert "best_mape" in comparison
        assert "best_rmse" in comparison
        assert "best_mae" in comparison
        assert comparison["best_mape"].model_type == "xgboost"
        assert comparison["best_rmse"].model_type == "xgboost"
        assert comparison["best_mae"].model_type == "xgboost"

    def test_compare_models_empty_list(self):
        """Test comparing empty list returns empty dict."""
        from ml.src.evaluation.evaluate_models import compare_models

        comparison = compare_models([])

        assert comparison == {}


class TestCreateEvaluationSummary:
    """Tests for create_evaluation_summary function."""

    def test_create_evaluation_summary(self):
        """Test creating evaluation summary."""
        from ml.src.evaluation.evaluate_models import (
            ModelEvaluationResult,
            create_evaluation_summary,
        )

        evaluations = [
            ModelEvaluationResult(
                model_type="baseline",
                model_id="model_1",
                store_id=1,
                evaluation_period_start=date(2023, 1, 1),
                evaluation_period_end=date(2023, 1, 14),
                mape=15.0,
                rmse=60.0,
                mae=50.0,
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

        summary = create_evaluation_summary(evaluations)

        assert summary["count"] == 2
        assert "baseline" in summary["by_model_type"]
        assert "prophet" in summary["by_model_type"]
        assert summary["best_by_mape"]["model_type"] == "prophet"
