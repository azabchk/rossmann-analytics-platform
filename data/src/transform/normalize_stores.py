"""Normalization and cleaning for store records.

This module handles data cleaning and normalization of store metadata from
the Rossmann store data, preparing them for loading into operational tables.
"""

from typing import Literal

import pandas as pd


def normalize_stores(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and clean store records from store.csv.

    This function performs the following transformations:
    - Ensures all required columns are present and properly typed
    - Handles missing values according to business rules
    - Normalizes categorical values to standard formats
    - Converts date components to proper types

    Args:
        df: Raw DataFrame from store.csv

    Returns:
        Normalized DataFrame ready for loading

    Raises:
        ValueError: If the DataFrame structure is invalid
    """
    # Create a copy to avoid modifying the original
    df_clean = df.copy()

    # Validate required columns
    required_columns = [
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

    missing_columns = set(required_columns) - set(df_clean.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Normalize Store - ensure integer type
    df_clean["Store"] = pd.to_numeric(df_clean["Store"], errors="coerce").astype("Int64")

    # Normalize StoreType - ensure lowercase and valid values
    df_clean["StoreType"] = df_clean["StoreType"].astype(str).str.lower()
    # Convert "nan" string to None
    df_clean["StoreType"] = df_clean["StoreType"].replace("nan", None)

    # Normalize Assortment - ensure lowercase
    df_clean["Assortment"] = df_clean["Assortment"].astype(str).str.lower()
    # Convert "nan" string to None
    df_clean["Assortment"] = df_clean["Assortment"].replace("nan", None)

    # Normalize CompetitionDistance - ensure numeric, non-negative
    df_clean["CompetitionDistance"] = pd.to_numeric(
        df_clean["CompetitionDistance"], errors="coerce"
    )
    df_clean["CompetitionDistance"] = df_clean["CompetitionDistance"].clip(lower=0)

    # Normalize CompetitionOpenSinceMonth - ensure integer 1-12
    df_clean["CompetitionOpenSinceMonth"] = pd.to_numeric(
        df_clean["CompetitionOpenSinceMonth"], errors="coerce"
    ).astype("Int64")
    df_clean["CompetitionOpenSinceMonth"] = df_clean["CompetitionOpenSinceMonth"].clip(
        lower=1, upper=12
    )

    # Normalize CompetitionOpenSinceYear - ensure integer
    df_clean["CompetitionOpenSinceYear"] = pd.to_numeric(
        df_clean["CompetitionOpenSinceYear"], errors="coerce"
    ).astype("Int64")

    # Normalize Promo2 - ensure integer type (0 or 1)
    df_clean["Promo2"] = pd.to_numeric(df_clean["Promo2"], errors="coerce").fillna(0).astype("Int64")
    df_clean["Promo2"] = df_clean["Promo2"].clip(lower=0, upper=1)

    # Normalize Promo2SinceWeek - ensure integer 1-53
    df_clean["Promo2SinceWeek"] = pd.to_numeric(
        df_clean["Promo2SinceWeek"], errors="coerce"
    ).astype("Int64")
    df_clean["Promo2SinceWeek"] = df_clean["Promo2SinceWeek"].clip(lower=1, upper=53)

    # Normalize Promo2SinceYear - ensure integer
    df_clean["Promo2SinceYear"] = pd.to_numeric(
        df_clean["Promo2SinceYear"], errors="coerce"
    ).astype("Int64")

    # Normalize PromoInterval - ensure string and trim whitespace
    df_clean["PromoInterval"] = df_clean["PromoInterval"].astype(str).str.strip()
    df_clean["PromoInterval"] = df_clean["PromoInterval"].replace("nan", None)

    # Handle missing CompetitionDistance
    # Stores without competition have NA distance - fill with large sentinel value
    # This distinguishes "no competition" from "unknown distance"
    df_clean["CompetitionDistance"] = df_clean["CompetitionDistance"].fillna(999999)

    # For stores with Promo2=0, clear the related fields
    df_clean.loc[df_clean["Promo2"] == 0, "Promo2SinceWeek"] = None
    df_clean.loc[df_clean["Promo2"] == 0, "Promo2SinceYear"] = None
    df_clean.loc[df_clean["Promo2"] == 0, "PromoInterval"] = None

    # Remove records with missing Store ID (these can't be processed)
    df_clean = df_clean[df_clean["Store"].notna()].copy()

    # Sort by store ID for consistent ordering
    df_clean = df_clean.sort_values("Store").reset_index(drop=True)

    return df_clean


def create_store_operational_columns() -> list[str]:
    """Get the column names for the operational store table.

    Returns:
        List of column names in the correct order
    """
    return [
        "store_id",
        "store_type",
        "assortment",
        "competition_distance",
        "competition_open_since_month",
        "competition_open_since_year",
        "promo2",
        "promo2_since_week",
        "promo2_since_year",
        "promo_interval",
    ]


def map_store_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map DataFrame columns to operational table column names.

    Args:
        df: Normalized DataFrame with source column names

    Returns:
        DataFrame with operational column names
    """
    column_mapping = {
        "Store": "store_id",
        "StoreType": "store_type",
        "Assortment": "assortment",
        "CompetitionDistance": "competition_distance",
        "CompetitionOpenSinceMonth": "competition_open_since_month",
        "CompetitionOpenSinceYear": "competition_open_since_year",
        "Promo2": "promo2",
        "Promo2SinceWeek": "promo2_since_week",
        "Promo2SinceYear": "promo2_since_year",
        "PromoInterval": "promo_interval",
    }

    df_mapped = df.rename(columns=column_mapping)
    return df_mapped[create_store_operational_columns()]


def get_store_cleaning_summary(original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> dict:
    """Get a summary of cleaning operations performed.

    Args:
        original_df: DataFrame before cleaning
        cleaned_df: DataFrame after cleaning

    Returns:
        Dictionary containing cleaning summary statistics
    """
    original_count = len(original_df)
    cleaned_count = len(cleaned_df)
    removed_count = original_count - cleaned_count

    # Count NA values before and after for key fields
    original_na_store_type = original_df["StoreType"].isna().sum()
    original_na_assortment = original_df["Assortment"].isna().sum()

    # Count stores with competition info
    has_competition = (cleaned_df["competition_distance"] < 999999).sum()
    has_promo2 = (cleaned_df["promo2"] == 1).sum()

    # Store type distribution
    store_type_dist = cleaned_df["store_type"].value_counts().to_dict() if "store_type" in cleaned_df.columns else {}

    # Assortment distribution
    assortment_dist = cleaned_df["assortment"].value_counts().to_dict() if "assortment" in cleaned_df.columns else {}

    return {
        "original_record_count": original_count,
        "cleaned_record_count": cleaned_count,
        "records_removed": removed_count,
        "removal_rate_pct": (removed_count / original_count * 100) if original_count > 0 else 0,
        "missing_store_type_before": original_na_store_type,
        "missing_assortment_before": original_na_assortment,
        "stores_with_competition": int(has_competition),
        "stores_with_promo2": int(has_promo2),
        "store_type_distribution": store_type_dist,
        "assortment_distribution": assortment_dist,
    }
