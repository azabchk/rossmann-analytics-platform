"""Integration tests for successful ingestion pipeline.

These tests validate that the ingestion pipeline can successfully:
1. Read Rossmann CSV files
2. Validate data without critical errors
3. Normalize and clean data
4. Load into database tables
5. Track run metadata
"""

import io
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Module imports
from src.ingest import read_train_csv, read_store_csv
from src.quality import validate_sales_records, validate_store_records
from src.transform import normalize_sales, normalize_stores, map_sales_columns, map_store_columns
from src.runs.models import IngestionRun, IngestionRunStatus, TableValidationResult


@pytest.fixture
def sample_train_csv_content() -> str:
    """Return content for a valid sample train CSV file."""
    return """Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday
1,5,2015-07-31,5263,555,1,1,0,1
1,4,2015-07-30,5020,534,1,1,0,1
1,3,2015-07-29,4782,499,1,1,0,1
2,5,2015-07-31,6064,625,1,1,0,1
2,4,2015-07-30,5602,581,1,1,0,1
"""


@pytest.fixture
def sample_store_csv_content() -> str:
    """Return content for a valid sample store CSV file."""
    return """Store,StoreType,Assortment,CompetitionDistance,CompetitionOpenSinceMonth,CompetitionOpenSinceYear,Promo2,Promo2SinceWeek,Promo2SinceYear,PromoInterval
1,c,a,1270,9,2008,0,0,0,0,
2,a,a,570,11,2007,1,13,2010,"Jan,Apr,Jul,Oct"
"""


@pytest.fixture
def sample_train_df(sample_train_csv_content: str) -> pd.DataFrame:
    """Return a DataFrame from sample train CSV content."""
    df = pd.read_csv(io.StringIO(sample_train_csv_content))
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@pytest.fixture
def sample_store_df(tmp_path: Path, sample_store_csv_content: str) -> pd.DataFrame:
    """Return a DataFrame from sample store CSV content."""
    csv_file = tmp_path / "store.csv"
    csv_file.write_text(sample_store_csv_content)
    return read_store_csv(csv_file)


class TestTrainCSVReading:
    """Tests for reading train.csv file."""

    def test_read_train_csv_from_file(self, sample_train_csv_content: str, tmp_path: Path):
        """Test reading train CSV from file."""
        csv_file = tmp_path / "train.csv"
        csv_file.write_text(sample_train_csv_content)

        df = read_train_csv(csv_file)

        assert df is not None
        assert len(df) == 5
        assert "Store" in df.columns
        assert "Date" in df.columns
        assert "Sales" in df.columns

    def test_read_train_csv_column_types(self, sample_train_df: pd.DataFrame):
        """Test that train CSV has expected column types."""
        assert sample_train_df["Store"].dtype in ["int64", "Int64"]
        assert sample_train_df["DayOfWeek"].dtype in ["int64", "Int8"]
        assert pd.api.types.is_datetime64_any_dtype(sample_train_df["Date"])


class TestStoreCSVReading:
    """Tests for reading store.csv file."""

    def test_read_store_csv_from_file(self, sample_store_csv_content: str, tmp_path: Path):
        """Test reading store CSV from file."""
        csv_file = tmp_path / "store.csv"
        csv_file.write_text(sample_store_csv_content)

        df = read_store_csv(csv_file)

        assert df is not None
        assert len(df) == 2
        assert "Store" in df.columns
        assert "StoreType" in df.columns
        assert "Assortment" in df.columns

    def test_read_store_csv_column_types(self, sample_store_df: pd.DataFrame):
        """Test that store CSV has expected column types."""
        assert sample_store_df["Store"].dtype in ["int64", "Int64"]
        assert sample_store_df["StoreType"].dtype in ["object", "string"]
        assert sample_store_df["Assortment"].dtype in ["object", "string"]


class TestSalesValidation:
    """Tests for sales record validation."""

    def test_validate_valid_sales_records(self, sample_train_df: pd.DataFrame):
        """Test that valid sales records pass validation."""
        result = validate_sales_records(sample_train_df, strict=False)

        assert result.total_records == 5
        assert result.valid_records == 5
        assert not result.has_errors

    def test_validate_detects_negative_sales(self, sample_train_df: pd.DataFrame):
        """Test that negative sales are detected."""
        sample_train_df.loc[0, "Sales"] = -100

        result = validate_sales_records(sample_train_df, strict=False)

        assert result.has_errors
        assert any(
            "negative_sales" in issue.issue_type.value
            for issue in result.issues
        )

    def test_validate_detects_sales_when_closed(self, sample_train_df: pd.DataFrame):
        """Test that sales when store is closed are detected."""
        sample_train_df.loc[0, "Open"] = 0
        sample_train_df.loc[0, "Sales"] = 500

        result = validate_sales_records(sample_train_df, strict=False)

        assert result.has_errors
        assert any(
            "sales_when_closed" in issue.issue_type.value
            for issue in result.issues
        )

    def test_validate_detects_invalid_day_of_week(self, sample_train_df: pd.DataFrame):
        """Test that invalid day of week is detected."""
        sample_train_df.loc[0, "DayOfWeek"] = 8

        result = validate_sales_records(sample_train_df, strict=False)

        assert result.has_errors
        assert any(
            "invalid_day_of_week" in issue.issue_type.value
            for issue in result.issues
        )


class TestStoreValidation:
    """Tests for store record validation."""

    def test_validate_valid_store_records(self, sample_store_df: pd.DataFrame):
        """Test that valid store records pass validation."""
        result = validate_store_records(sample_store_df, strict=False)

        assert result.total_records == 2
        assert result.valid_records == 2
        assert not result.has_errors

    def test_validate_detects_invalid_store_type(self, sample_store_df: pd.DataFrame):
        """Test that invalid store type is detected."""
        sample_store_df.loc[0, "StoreType"] = "x"

        result = validate_store_records(sample_store_df, strict=False)

        assert result.has_errors
        assert any(
            "invalid_store_type" in issue.issue_type.value
            for issue in result.issues
        )

    def test_validate_detects_negative_competition_distance(self, sample_store_df: pd.DataFrame):
        """Test that negative competition distance is detected."""
        sample_store_df.loc[0, "CompetitionDistance"] = -100

        result = validate_store_records(sample_store_df, strict=False)

        assert result.has_errors
        assert any(
            "negative_competition_distance" in issue.issue_type.value
            for issue in result.issues
        )

    def test_validate_detects_invalid_promo2_flag(self, sample_store_df: pd.DataFrame):
        """Test that invalid promo2 flag is detected."""
        sample_store_df.loc[0, "Promo2"] = 2

        result = validate_store_records(sample_store_df, strict=False)

        assert result.has_errors
        assert any(
            "invalid_promo2_flag" in issue.issue_type.value
            for issue in result.issues
        )


class TestSalesTransformation:
    """Tests for sales record transformation."""

    def test_normalize_sales_basic(self, sample_train_df: pd.DataFrame):
        """Test basic sales normalization."""
        normalized = normalize_sales(sample_train_df)
        mapped = map_sales_columns(normalized)

        assert mapped is not None
        assert len(mapped) == 5
        assert "store_id" in mapped.columns
        assert "date" in mapped.columns
        assert "sales" in mapped.columns

    def test_normalize_sales_handles_missing_values(self, sample_train_df: pd.DataFrame):
        """Test that missing values are handled."""
        sample_train_df.loc[0, "Sales"] = None

        normalized = normalize_sales(sample_train_df)
        mapped = map_sales_columns(normalized)

        # Missing sales should be filled
        assert mapped["sales"].notna().all()

    def test_normalize_sales_removes_invalid_records(self, sample_train_df: pd.DataFrame):
        """Test that invalid records are removed."""
        # Add a record with sales when closed
        new_row = sample_train_df.iloc[0].copy()
        new_row["Open"] = 0
        new_row["Sales"] = 100
        df_with_invalid = pd.concat([sample_train_df, pd.DataFrame([new_row])], ignore_index=True)

        normalized = normalize_sales(df_with_invalid)

        # The invalid record should be removed
        assert len(normalized) == 5

    def test_map_sales_columns(self, sample_train_df: pd.DataFrame):
        """Test that columns are mapped to operational schema."""
        normalized = normalize_sales(sample_train_df)
        mapped = map_sales_columns(normalized)

        assert "store_id" in mapped.columns
        assert "date" in mapped.columns
        assert "day_of_week" in mapped.columns
        assert "sales" in mapped.columns
        assert "customers" in mapped.columns
        assert "open" in mapped.columns
        assert "promo" in mapped.columns
        assert "state_holiday" in mapped.columns
        assert "school_holiday" in mapped.columns


class TestStoreTransformation:
    """Tests for store record transformation."""

    def test_normalize_stores_basic(self, sample_store_df: pd.DataFrame):
        """Test basic store normalization."""
        normalized = normalize_stores(sample_store_df)
        mapped = map_store_columns(normalized)

        assert mapped is not None
        assert len(mapped) == 2
        assert "store_id" in mapped.columns
        assert "store_type" in mapped.columns
        assert "assortment" in mapped.columns

    def test_normalize_stores_handles_missing_competition_distance(self, sample_store_df: pd.DataFrame):
        """Test that missing competition distance is handled."""
        sample_store_df.loc[1, "CompetitionDistance"] = None

        normalized = normalize_stores(sample_store_df)
        mapped = map_store_columns(normalized)

        # Missing distance should be filled with sentinel value
        assert mapped["competition_distance"].notna().all()

    def test_normalize_stores_clears_promo2_fields_when_disabled(self, sample_store_df: pd.DataFrame):
        """Test that promo2 fields are cleared when promo2=0."""
        sample_store_df.loc[0, "Promo2"] = 0

        normalized = normalize_stores(sample_store_df)

        # Promo2 fields should be None
        assert pd.isna(normalized.loc[0, "promo2_since_week"])
        assert pd.isna(normalized.loc[0, "promo2_since_year"])

    def test_map_store_columns(self, sample_store_df: pd.DataFrame):
        """Test that columns are mapped to operational schema."""
        normalized = normalize_stores(sample_store_df)
        mapped = map_store_columns(normalized)

        assert "store_id" in mapped.columns
        assert "store_type" in mapped.columns
        assert "assortment" in mapped.columns
        assert "competition_distance" in mapped.columns
        assert "promo2" in mapped.columns
        assert "promo2_since_week" in mapped.columns
        assert "promo2_since_year" in mapped.columns
        assert "promo_interval" in mapped.columns


class TestIngestionRunModel:
    """Tests for ingestion run model."""

    def test_create_ingestion_run(self):
        """Test creating an ingestion run."""
        run = IngestionRun(
            train_csv_path="/path/to/train.csv",
            store_csv_path="/path/to/store.csv",
        )

        assert run.run_id is not None
        assert run.status == IngestionRunStatus.PENDING
        assert run.train_csv_path == "/path/to/train.csv"
        assert run.store_csv_path == "/path/to/store.csv"

    def test_start_run(self):
        """Test starting a run."""
        run = IngestionRun()
        run.start()

        assert run.status == IngestionRunStatus.RUNNING
        assert run.started_at is not None

    def test_complete_run(self):
        """Test completing a run."""
        run = IngestionRun()
        run.start()
        run.complete()

        assert run.status == IngestionRunStatus.COMPLETED
        assert run.completed_at is not None
        assert run.duration_seconds is not None
        assert run.duration_seconds > 0

    def test_fail_run(self):
        """Test failing a run."""
        run = IngestionRun()
        run.start()
        run.fail("Test error", "Test traceback")

        assert run.status == IngestionRunStatus.FAILED
        assert run.completed_at is not None
        assert run.error_message == "Test error"
        assert run.error_traceback == "Test traceback"

    def test_add_validation_result(self):
        """Test adding validation result."""
        run = IngestionRun()
        result = TableValidationResult(
            table_name="sales",
            total_records=100,
            valid_records=98,
        )

        run.add_validation_result(result)

        assert "sales" in run.validation_results
        assert run.validation_results["sales"] == result

    def test_has_validation_errors(self):
        """Test checking for validation errors."""
        run = IngestionRun()
        result_with_errors = TableValidationResult(
            table_name="sales",
            total_records=100,
            valid_records=95,
        )
        result_without_errors = TableValidationResult(
            table_name="stores",
            total_records=10,
            valid_records=10,
        )

        run.add_validation_result(result_with_errors)
        run.add_validation_result(result_without_errors)

        assert run.has_validation_errors


class TestValidationReport:
    """Tests for validation report generation."""

    def test_create_validation_report(self):
        """Test creating a validation report."""
        run = IngestionRun()
        run.train_record_count = 100
        run.store_record_count = 10
        run.start()

        result = TableValidationResult(
            table_name="sales",
            total_records=100,
            valid_records=98,
        )
        run.add_validation_result(result)

        from src.runs.reporting import create_validation_report

        report = create_validation_report(run)

        assert report.run_id == run.run_id
        assert report.total_records == 110
        assert report.total_valid == 108
        assert report.total_errors == 2

    def test_report_to_markdown(self):
        """Test converting report to Markdown."""
        run = IngestionRun()
        run.train_record_count = 100
        run.store_record_count = 10
        run.start()

        result = TableValidationResult(
            table_name="sales",
            total_records=100,
            valid_records=98,
        )
        run.add_validation_result(result)

        from src.runs.reporting import create_validation_report

        report = create_validation_report(run)
        markdown = report.to_markdown()

        assert "# Ingestion Validation Report" in markdown
        assert str(run.run_id) in markdown
        assert "Validation Summary" in markdown
