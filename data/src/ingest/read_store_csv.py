"""Reader for Rossmann store.csv dataset.

This module reads the store metadata from the Rossmann Store Sales
competition, which contains static information about each store.

Expected columns:
- Store: Store ID (integer)
- StoreType: Type of store (a, b, c, d)
- Assortment: Level of assortment (a=basic, b=extra, c=extended)
- CompetitionDistance: Distance to nearest competitor (meters, may be NA)
- CompetitionOpenSinceMonth: Month when nearest competitor opened (1-12, may be NA)
- CompetitionOpenSinceYear: Year when nearest competitor opened (may be NA)
- Promo2: Whether store has ongoing promotion (0=no, 1=yes)
- Promo2SinceWeek: Week when the continuous promotion started (may be NA)
- Promo2SinceYear: Year when the continuous promotion started (may be NA)
- PromoInterval: Consecutive intervals Promo2 is started (e.g., "Feb,May,Aug,Nov")
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd


@dataclass
class StoreRecord:
    """A single store metadata record."""

    store: int
    store_type: str | None
    assortment: str | None
    competition_distance: float | None
    competition_open_since_month: int | None
    competition_open_since_year: int | None
    promo2: int
    promo2_since_week: int | None
    promo2_since_year: int | None
    promo_interval: str | None


def read_store_csv(
    file_path: str | Path,
    parse_dates: bool = False,
) -> pd.DataFrame:
    """Read the store.csv file into a pandas DataFrame.

    Args:
        file_path: Path to the store.csv file
        parse_dates: Whether to parse date columns as datetime

    Returns:
        DataFrame containing the store metadata

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file structure is invalid
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Store CSV file not found: {file_path}")

    # Define expected columns for validation
    expected_columns = [
        "Store",
        "StoreType",
        "Assortment",
        "CompetitionDistance",
        "CompetitionOpenSinceMonth",
        "CompetitionOpenSinceYear",
        "Promo2",
        "Promo2SinceWeek",
        "Promo2SinceYear",
        "PromoInterval",
    ]

    try:
        # Read the CSV without dtype first to avoid pandas parsing issues
        df = pd.read_csv(file_path)

        # Convert numeric columns to proper types after reading
        # Use try-except to handle missing columns
        for col in ["Store", "CompetitionDistance", "CompetitionOpenSinceMonth", "CompetitionOpenSinceYear", "Promo2", "Promo2SinceWeek", "Promo2SinceYear"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                # Set correct dtype
                if col == "Store":
                    df[col] = df[col].astype("Int64")
                elif col in ["CompetitionDistance"]:
                    df[col] = df[col].astype("Float64")
                elif col in ["CompetitionOpenSinceMonth", "CompetitionOpenSinceYear", "Promo2SinceWeek", "Promo2SinceYear"]:
                    df[col] = df[col].astype("Int64")
                elif col == "Promo2":
                    df[col] = df[col].astype("Int8")

        # Validate column structure
        missing_columns = set(expected_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(
                f"Missing expected columns in store.csv: {missing_columns}"
            )

        return df

    except pd.errors.EmptyDataError as e:
        raise ValueError("Store CSV file is empty") from e
    except pd.errors.ParserError as e:
        raise ValueError(f"Failed to parse store CSV: {e}") from e


def read_store_csv_as_records(
    file_path: str | Path,
) -> list[StoreRecord]:
    """Read store.csv and return as StoreRecord objects.

    Args:
        file_path: Path to the store.csv file

    Returns:
        List of StoreRecord objects
    """
    df = read_store_csv(file_path)

    records = []
    for _, row in df.iterrows():
        records.append(
            StoreRecord(
                store=int(row["Store"]),
                store_type=row["StoreType"] if pd.notna(row["StoreType"]) else None,
                assortment=row["Assortment"] if pd.notna(row["Assortment"]) else None,
                competition_distance=(
                    float(row["CompetitionDistance"])
                    if pd.notna(row["CompetitionDistance"])
                    else None
                ),
                competition_open_since_month=(
                    int(row["CompetitionOpenSinceMonth"])
                    if pd.notna(row["CompetitionOpenSinceMonth"])
                    else None
                ),
                competition_open_since_year=(
                    int(row["CompetitionOpenSinceYear"])
                    if pd.notna(row["CompetitionOpenSinceYear"])
                    else None
                ),
                promo2=int(row["Promo2"]),
                promo2_since_week=(
                    int(row["Promo2SinceWeek"])
                    if pd.notna(row["Promo2SinceWeek"])
                    else None
                ),
                promo2_since_year=(
                    int(row["Promo2SinceYear"])
                    if pd.notna(row["Promo2SinceYear"])
                    else None
                ),
                promo_interval=row["PromoInterval"] if pd.notna(row["PromoInterval"]) else None,
            )
        )

    return records


def get_store_csv_schema() -> dict[str, str]:
    """Get the expected schema for store.csv.

    Returns:
        Dictionary mapping column names to their expected types
    """
    return {
        "Store": "integer (unique store ID)",
        "StoreType": "string (a, b, c, or d)",
        "Assortment": "string (a=basic, b=extra, c=extended)",
        "CompetitionDistance": "float (meters, may be NA)",
        "CompetitionOpenSinceMonth": "integer (1-12, may be NA)",
        "CompetitionOpenSinceYear": "integer (may be NA)",
        "Promo2": "integer (0 or 1)",
        "Promo2SinceWeek": "integer (may be NA)",
        "Promo2SinceYear": "integer (may be NA)",
        "PromoInterval": "string (comma-separated months, may be NA)",
    }
