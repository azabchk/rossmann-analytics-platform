"""Integration tests for ingestion pipeline failure scenarios.

These tests validate that the ingestion pipeline properly detects
and reports various data quality issues, malformed input files,
and edge cases that should prevent successful data loading.
"""

import io
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.ingest import read_train_csv, read_store_csv
from src.quality import validate_sales_records, validate_store_records
from src.transform import normalize_sales, normalize_stores, map_sales_columns, map_store_columns


class TestMalformedTrainCSV:
    """Tests for handling malformed train CSV files."""

    def test_missing_required_columns_raises_error(self, tmp_path: Path):
        """Test that missing required columns raises ValueError."""
        csv_content = """Store,DayOfWeek,Date,Sales
1,5,2015-07-31,5263
"""
        csv_file = tmp_path / "train_invalid.csv"
        csv_file.write_text(csv_content)
        with pytest.raises(ValueError, match="Missing expected columns"):
            read_train_csv(csv_file)

    def test_empty_csv_raises_error(self, tmp_path: Path):
        """Test that empty CSV raises ValueError."""
        csv_content = ""
        csv_file = tmp_path / "train_empty.csv"
        csv_file.write_text(csv_content)
        with pytest.raises(ValueError, match="Train CSV file is empty"):
            read_train_csv(csv_file)

    def test_nonexistent_file_raises_error(self, tmp_path: Path):
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Train CSV file not found"):
            read_train_csv(tmp_path / "nonexistent.csv")

    def test_invalid_date_format_raises_error(self, tmp_path: Path):
        """Test that invalid date format is handled."""
        csv_content = """Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday
1,5,invalid-date,5263,555,1,1,0,1
"""
        csv_file = tmp_path / "train_invalid_date.csv"
        csv_file.write_text(csv_content)
        df = read_train_csv(csv_file)
        # Invalid dates should be converted to NaT
        assert pd.isna(df.loc[0, "Date"])


class TestMalformedStoreCSV:
    """Tests for handling malformed store CSV files."""

    def test_missing_required_columns_raises_error(self, tmp_path: Path):
        """Test that missing required columns raises ValueError."""
        csv_content = """Store,StoreType
1,c
"""
        csv_file = tmp_path / "store_invalid.csv"
        csv_file.write_text(csv_content)
        with pytest.raises(ValueError, match="Missing expected columns"):
            read_store_csv(csv_file)

    def test_empty_csv_raises_error(self, tmp_path: Path):
        """Test that empty CSV raises ValueError."""
        csv_content = ""
        csv_file = tmp_path / "store_empty.csv"
        csv_file.write_text(csv_content)
        with pytest.raises(ValueError, match="Store CSV file is empty"):
            read_store_csv(csv_file)

    def test_nonexistent_file_raises_error(self, tmp_path: Path):
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Store CSV file not found"):
            read_store_csv(tmp_path / "nonexistent.csv")


class TestSalesValidationFailures:
    """Tests for sales record validation error detection."""

    @pytest.fixture
    def base_sales_df(self) -> pd.DataFrame:
        """Return a base valid sales DataFrame."""
        return pd.DataFrame({
            "Store": [1, 1, 2],
            "DayOfWeek": [5, 4, 5],
            "Date": pd.to_datetime(["2015-07-31", "2015-07-30", "2015-07-31"]),
            "Sales": [5000, 4500, 6000],
            "Customers": [500, 450, 600],
            "Open": [1, 1, 1],
            "Promo": [1, 1, 1],
            "StateHoliday": ["0", "0", "0"],
            "SchoolHoliday": [1, 1, 1],
        })

    def test_negative_sales_detected(self, base_sales_df: pd.DataFrame):
        """Test that negative sales are detected."""
        base_sales_df.loc[0, "Sales"] = -100

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert result.error_count >= 1

    def test_negative_customers_detected(self, base_sales_df: pd.DataFrame):
        """Test that negative customers are detected."""
        base_sales_df.loc[0, "Customers"] = -50

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("negative_customers" in issue.issue_type.value for issue in result.issues)

    def test_sales_when_closed_detected(self, base_sales_df: pd.DataFrame):
        """Test that sales when store is closed are detected."""
        base_sales_df.loc[0, "Open"] = 0
        base_sales_df.loc[0, "Sales"] = 100

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("sales_when_closed" in issue.issue_type.value for issue in result.issues)

    def test_customers_when_closed_detected(self, base_sales_df: pd.DataFrame):
        """Test that customers when store is closed are detected."""
        base_sales_df.loc[0, "Open"] = 0
        base_sales_df.loc[0, "Customers"] = 50

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("customers_when_closed" in issue.issue_type.value for issue in result.issues)

    def test_invalid_open_flag_detected(self, base_sales_df: pd.DataFrame):
        """Test that invalid open flag is detected."""
        base_sales_df.loc[0, "Open"] = 2

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("invalid_open_flag" in issue.issue_type.value for issue in result.issues)

    def test_invalid_promo_flag_detected(self, base_sales_df: pd.DataFrame):
        """Test that invalid promo flag is detected."""
        base_sales_df.loc[0, "Promo"] = 2

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("invalid_promo_flag" in issue.issue_type.value for issue in result.issues)

    def test_invalid_school_holiday_flag_detected(self, base_sales_df: pd.DataFrame):
        """Test that invalid school holiday flag is detected."""
        base_sales_df.loc[0, "SchoolHoliday"] = 2

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("invalid_holiday_flag" in issue.issue_type.value for issue in result.issues)

    def test_invalid_day_of_week_detected(self, base_sales_df: pd.DataFrame):
        """Test that invalid day of week is detected."""
        base_sales_df.loc[0, "DayOfWeek"] = 8

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("invalid_day_of_week" in issue.issue_type.value for issue in result.issues)

    def test_invalid_day_of_week_below_range(self, base_sales_df: pd.DataFrame):
        """Test that day of week below 1 is detected."""
        base_sales_df.loc[0, "DayOfWeek"] = 0

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("invalid_day_of_week" in issue.issue_type.value for issue in result.issues)

    def test_out_of_range_date_detected(self, base_sales_df: pd.DataFrame):
        """Test that dates outside the expected range are detected."""
        base_sales_df.loc[0, "Date"] = pd.Timestamp("2010-01-01")

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("invalid_date_range" in issue.issue_type.value for issue in result.issues)

    def test_future_date_detected(self, base_sales_df: pd.DataFrame):
        """Test that future dates are detected."""
        base_sales_df.loc[0, "Date"] = pd.Timestamp("2025-01-01")

        result = validate_sales_records(base_sales_df, strict=False)

        assert result.has_errors
        assert any("invalid_date_range" in issue.issue_type.value for issue in result.issues)

    def test_duplicate_records_detected(self, base_sales_df: pd.DataFrame):
        """Test that duplicate store/date combinations are detected."""
        duplicate_row = base_sales_df.iloc[0].copy()
        df_with_dupes = pd.concat([base_sales_df, pd.DataFrame([duplicate_row])], ignore_index=True)

        result = validate_sales_records(df_with_dupes, strict=False)

        assert result.has_errors
        assert any("duplicate_record" in issue.issue_type.value for issue in result.issues)

    def test_extreme_outlier_detected(self, base_sales_df: pd.DataFrame):
        """Test that extreme sales outliers are detected as warnings."""
        base_sales_df.loc[0, "Sales"] = 50000

        result = validate_sales_records(base_sales_df, strict=False, check_outliers=True)

        # Extreme outliers should be warnings, not errors
        assert not result.has_errors
        assert result.warning_count >= 1
        assert any("extreme_outlier" in issue.issue_type.value for issue in result.warnings)

    def test_zero_sales_when_open_warning(self, base_sales_df: pd.DataFrame):
        """Test that zero sales when store is open is a warning."""
        base_sales_df.loc[0, "Open"] = 1
        base_sales_df.loc[0, "Sales"] = 0

        result = validate_sales_records(base_sales_df, strict=False)

        # Zero sales when open should be a warning
        assert not result.has_errors
        assert result.warning_count >= 1
        assert any("zero_sales_when_open" in issue.issue_type.value for issue in result.warnings)


class TestStoreValidationFailures:
    """Tests for store record validation error detection."""

    @pytest.fixture
    def base_store_df(self) -> pd.DataFrame:
        """Return a base valid store DataFrame."""
        return pd.DataFrame({
            "Store": [1, 2],
            "StoreType": ["c", "a"],
            "Assortment": ["a", "a"],
            "CompetitionDistance": [1270.0, 570.0],
            "CompetitionOpenSinceMonth": [9, 11],
            "CompetitionOpenSinceYear": [2008, 2007],
            "Promo2": [0, 1],
            "Promo2SinceWeek": [None, 13],
            "Promo2SinceYear": [None, 2010],
            "PromoInterval": [None, "Jan,Apr,Jul,Oct"],
        })

    def test_invalid_store_type_detected(self, base_store_df: pd.DataFrame):
        """Test that invalid store type is detected."""
        base_store_df.loc[0, "StoreType"] = "x"

        result = validate_store_records(base_store_df, strict=False)

        assert result.has_errors
        assert any("invalid_store_type" in issue.issue_type.value for issue in result.issues)

    def test_invalid_assortment_detected(self, base_store_df: pd.DataFrame):
        """Test that invalid assortment is detected."""
        base_store_df.loc[0, "Assortment"] = "x"

        result = validate_store_records(base_store_df, strict=False)

        assert result.has_errors
        assert any("invalid_assortment" in issue.issue_type.value for issue in result.issues)

    def test_negative_competition_distance_detected(self, base_store_df: pd.DataFrame):
        """Test that negative competition distance is detected."""
        base_store_df.loc[0, "CompetitionDistance"] = -100.0

        result = validate_store_records(base_store_df, strict=False)

        assert result.has_errors
        assert any("negative_competition_distance" in issue.issue_type.value for issue in result.issues)

    def test_invalid_promo2_flag_detected(self, base_store_df: pd.DataFrame):
        """Test that invalid promo2 flag is detected."""
        base_store_df.loc[0, "Promo2"] = 2

        result = validate_store_records(base_store_df, strict=False)

        assert result.has_errors
        assert any("invalid_promo2_flag" in issue.issue_type.value for issue in result.issues)

    def test_invalid_competition_open_month_detected(self, base_store_df: pd.DataFrame):
        """Test that invalid competition open month is detected."""
        base_store_df.loc[0, "CompetitionOpenSinceMonth"] = 13

        result = validate_store_records(base_store_df, strict=False)

        assert result.has_errors
        assert any("invalid_competition_open_month" in issue.issue_type.value for issue in result.issues)

    def test_invalid_competition_open_month_below_range(self, base_store_df: pd.DataFrame):
        """Test that competition open month below 1 is detected."""
        base_store_df.loc[0, "CompetitionOpenSinceMonth"] = 0

        result = validate_store_records(base_store_df, strict=False)

        assert result.has_errors
        assert any("invalid_competition_open_month" in issue.issue_type.value for issue in result.issues)

    def test_incomplete_promo2_dates_detected(self, base_store_df: pd.DataFrame):
        """Test that incomplete promo2 dates are detected."""
        base_store_df.loc[1, "Promo2"] = 1
        base_store_df.loc[1, "Promo2SinceWeek"] = None

        result = validate_store_records(base_store_df, strict=False)

        assert result.has_errors
        assert any("incomplete_promo2_dates" in issue.issue_type.value for issue in result.issues)

    def test_duplicate_store_id_detected(self, base_store_df: pd.DataFrame):
        """Test that duplicate store IDs are detected."""
        duplicate_row = base_store_df.iloc[0].copy()
        df_with_dupes = pd.concat([base_store_df, pd.DataFrame([duplicate_row])], ignore_index=True)

        result = validate_store_records(df_with_dupes, strict=False)

        assert result.has_errors
        assert any("duplicate_store_id" in issue.issue_type.value for issue in result.issues)


class TestTransformationEdgeCases:
    """Tests for transformation with edge cases."""

    def test_normalize_sales_with_all_missing_values(self):
        """Test normalization with all missing values."""
        df = pd.DataFrame({
            "Store": [1, 2],
            "DayOfWeek": [5, 4],
            "Date": pd.to_datetime(["2015-07-31", "2015-07-30"]),
            "Sales": [None, None],
            "Customers": [None, None],
            "Open": [1, 1],
            "Promo": [0, 0],
            "StateHoliday": ["0", "0"],
            "SchoolHoliday": [0, 0],
        })

        normalized = normalize_sales(df)
        mapped = map_sales_columns(normalized)

        # Missing values should be filled
        assert mapped["sales"].notna().all()
        assert mapped["customers"].notna().all()

    def test_normalize_sales_with_all_closed_stores(self):
        """Test normalization with all stores closed."""
        df = pd.DataFrame({
            "Store": [1, 2],
            "DayOfWeek": [5, 4],
            "Date": pd.to_datetime(["2015-07-31", "2015-07-30"]),
            "Sales": [100, 50],
            "Customers": [10, 5],
            "Open": [0, 0],
            "Promo": [0, 0],
            "StateHoliday": ["0", "0"],
            "SchoolHoliday": [0, 0],
        })

        normalized = normalize_sales(df)
        mapped = map_sales_columns(normalized)

        # Sales and customers should be set to 0
        assert (mapped["sales"] == 0).all()
        assert (mapped["customers"] == 0).all()

    def test_normalize_stores_with_all_missing_competition(self):
        """Test normalization with all stores missing competition data."""
        df = pd.DataFrame({
            "Store": [1, 2],
            "StoreType": ["c", "a"],
            "Assortment": ["a", "a"],
            "CompetitionDistance": [None, None],
            "CompetitionOpenSinceMonth": [None, None],
            "CompetitionOpenSinceYear": [None, None],
            "Promo2": [0, 0],
            "Promo2SinceWeek": [None, None],
            "Promo2SinceYear": [None, None],
            "PromoInterval": [None, None],
        })

        normalized = normalize_stores(df)
        mapped = map_store_columns(normalized)

        # Missing competition distance should be filled with sentinel
        assert mapped["competition_distance"].notna().all()


class TestErrorReporting:
    """Tests for error reporting and messaging."""

    def test_validation_error_messages_are_descriptive(self):
        """Test that validation errors have descriptive messages."""
        df = pd.DataFrame({
            "Store": [1],
            "DayOfWeek": [5],
            "Date": pd.to_datetime(["2015-07-31"]),
            "Sales": [-100],
            "Customers": [50],
            "Open": [1],
            "Promo": [0],
            "StateHoliday": ["0"],
            "SchoolHoliday": [0],
        })

        result = validate_sales_records(df, strict=False)

        assert result.has_errors
        assert len(result.issues) > 0

        # Check that error messages contain relevant information
        issue = result.issues[0]
        assert issue.message is not None
        assert len(issue.message) > 0
        assert issue.expected is not None

    def test_error_rate_calculation(self):
        """Test that error rate is calculated correctly."""
        df = pd.DataFrame({
            "Store": [1, 2, 3],
            "DayOfWeek": [5, 4, 5],
            "Date": pd.to_datetime(["2015-07-31", "2015-07-30", "2015-07-29"]),
            "Sales": [-100, 5000, 6000],
            "Customers": [50, 450, 600],
            "Open": [1, 1, 1],
            "Promo": [0, 0, 0],
            "StateHoliday": ["0", "0", "0"],
            "SchoolHoliday": [0, 0, 0],
        })

        result = validate_sales_records(df, strict=False)

        # One error out of three records
        assert result.total_records == 3
        expected_error_rate = (1 / 3) * 100
        assert abs(result.error_rate - expected_error_rate) < 0.01
