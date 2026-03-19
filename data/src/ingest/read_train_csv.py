"""Reader for Rossmann train.csv dataset.

This module reads the raw training data from the Rossmann Store Sales
competition, which contains daily sales records for all stores.

Expected columns:
- Store: Store ID (integer)
- DayOfWeek: Day of week (1-7)
- Date: Date in YYYY-MM-DD format
- Sales: Sales amount for the day (non-negative integer)
- Customers: Number of customers (non-negative integer)
- Open: Whether store was open (0=closed, 1=open)
- Promo: Whether store had a promotion (0=no, 1=yes)
- StateHoliday: State holiday indicator
- SchoolHoliday: Whether it was a school holiday (0=no, 1=yes)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd


@dataclass
class TrainRecord:
    """A single record from the training data."""

    store: int
    day_of_week: int
    date: pd.Timestamp
    sales: int | None
    customers: int | None
    open: int
    promo: int
    state_holiday: str
    school_holiday: int


def read_train_csv(
    file_path: str | Path,
    chunk_size: int | None = None,
    parse_dates: bool = True,
) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """Read the train.csv file into a pandas DataFrame.

    Args:
        file_path: Path to the train.csv file
        chunk_size: If provided, return an iterator of DataFrames with this many rows
        parse_dates: Whether to parse the Date column as datetime

    Returns:
        DataFrame or iterator of DataFrames containing the training data

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file structure is invalid
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Train CSV file not found: {file_path}")

    # Define expected columns for validation
    expected_columns = [
        "Store",
        "DayOfWeek",
        "Date",
        "Sales",
        "Customers",
        "Open",
        "Promo",
        "StateHoliday",
        "SchoolHoliday",
    ]

    try:
        # Read the CSV with type hints
        dtype = {
            "Store": "Int64",
            "DayOfWeek": "Int8",
            "Sales": "Int64",
            "Customers": "Int64",
            "Open": "Int8",
            "Promo": "Int8",
            "StateHoliday": "string",
            "SchoolHoliday": "Int8",
        }

        if chunk_size:
            return pd.read_csv(
                file_path,
                dtype=dtype,
                parse_dates=["Date"] if parse_dates else None,
                chunksize=chunk_size,
            )
        else:
            df = pd.read_csv(
                file_path,
                dtype=dtype,
                parse_dates=["Date"] if parse_dates else None,
            )

            # Validate column structure
            missing_columns = set(expected_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(
                    f"Missing expected columns in train.csv: {missing_columns}"
                )

            # Ensure invalid dates are converted to NaT
            if parse_dates and "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

            return df

    except pd.errors.EmptyDataError as e:
        raise ValueError("Train CSV file is empty") from e
    except pd.errors.ParserError as e:
        raise ValueError(f"Failed to parse train CSV: {e}") from e


def read_train_csv_as_records(
    file_path: str | Path,
    limit: int | None = None,
) -> list[TrainRecord]:
    """Read train.csv and return as TrainRecord objects.

    Args:
        file_path: Path to the train.csv file
        limit: Maximum number of records to read (None for all)

    Returns:
        List of TrainRecord objects
    """
    df = read_train_csv(file_path)

    if limit:
        df = df.head(limit)

    records = []
    for _, row in df.iterrows():
        records.append(
            TrainRecord(
                store=int(row["Store"]),
                day_of_week=int(row["DayOfWeek"]),
                date=pd.to_datetime(row["Date"]),
                sales=int(row["Sales"]) if pd.notna(row["Sales"]) else None,
                customers=int(row["Customers"]) if pd.notna(row["Customers"]) else None,
                open=int(row["Open"]),
                promo=int(row["Promo"]),
                state_holiday=str(row["StateHoliday"]),
                school_holiday=int(row["SchoolHoliday"]),
            )
        )

    return records


def get_train_csv_schema() -> dict[str, str]:
    """Get the expected schema for train.csv.

    Returns:
        Dictionary mapping column names to their expected types
    """
    return {
        "Store": "integer",
        "DayOfWeek": "integer (1-7)",
        "Date": "date (YYYY-MM-DD)",
        "Sales": "integer (non-negative)",
        "Customers": "integer (non-negative)",
        "Open": "integer (0 or 1)",
        "Promo": "integer (0 or 1)",
        "StateHoliday": "string",
        "SchoolHoliday": "integer (0 or 1)",
    }
