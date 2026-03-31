"""Normalization and cleaning for Rossmann store metadata."""

from __future__ import annotations

import pandas as pd


REQUIRED_STORE_COLUMNS = [
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

NO_COMPETITION_SENTINEL = 999999


def _normalize_promo_interval(value: object) -> str | None:
    if pd.isna(value):
        return None

    normalized = str(value).strip()
    if not normalized or normalized == "0":
        return None

    parts = [part.strip().title() for part in normalized.split(",") if part.strip()]
    return ",".join(parts) if parts else None


def normalize_stores(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize store metadata for controlled operational loading."""

    cleaned = df.copy()
    missing_columns = set(REQUIRED_STORE_COLUMNS) - set(cleaned.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    cleaned["Store"] = pd.to_numeric(cleaned["Store"], errors="coerce").astype("Int64")
    cleaned = cleaned[cleaned["Store"].notna()].copy()

    cleaned["StoreType"] = (
        cleaned["StoreType"].astype("string").str.strip().str.upper().replace({"nan": None, "": None})
    )
    cleaned["Assortment"] = (
        cleaned["Assortment"].astype("string").str.strip().str.lower().replace({"nan": None, "": None})
    )
    cleaned["CompetitionDistance"] = (
        pd.to_numeric(cleaned["CompetitionDistance"], errors="coerce").clip(lower=0).round().astype("Int64")
    )
    cleaned["CompetitionOpenSinceMonth"] = (
        pd.to_numeric(cleaned["CompetitionOpenSinceMonth"], errors="coerce")
        .clip(lower=1, upper=12)
        .astype("Int64")
    )
    cleaned["CompetitionOpenSinceYear"] = (
        pd.to_numeric(cleaned["CompetitionOpenSinceYear"], errors="coerce").astype("Int64")
    )
    cleaned["Promo2"] = (
        pd.to_numeric(cleaned["Promo2"], errors="coerce").fillna(0).clip(lower=0, upper=1).astype("Int64")
    )
    cleaned["Promo2SinceWeek"] = (
        pd.to_numeric(cleaned["Promo2SinceWeek"], errors="coerce")
        .clip(lower=1, upper=52)
        .astype("Int64")
    )
    cleaned["Promo2SinceYear"] = (
        pd.to_numeric(cleaned["Promo2SinceYear"], errors="coerce").astype("Int64")
    )
    cleaned["PromoInterval"] = cleaned["PromoInterval"].map(_normalize_promo_interval)

    cleaned["CompetitionDistance"] = cleaned["CompetitionDistance"].fillna(NO_COMPETITION_SENTINEL)
    promo2_disabled = cleaned["Promo2"] == 0
    cleaned.loc[promo2_disabled, "Promo2SinceWeek"] = pd.NA
    cleaned.loc[promo2_disabled, "Promo2SinceYear"] = pd.NA
    cleaned.loc[promo2_disabled, "PromoInterval"] = None

    cleaned = cleaned.drop_duplicates(subset=["Store"], keep="last")
    cleaned = cleaned.sort_values("Store").reset_index(drop=True)
    return cleaned


def create_store_operational_columns() -> list[str]:
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
    """Map normalized store columns to the operational schema."""

    mapped = df.rename(
        columns={
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
    ).copy()

    mapped["promo2"] = mapped["promo2"].astype(bool)
    return mapped[create_store_operational_columns()]


def get_store_cleaning_summary(
    original_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
) -> dict[str, object]:
    """Return a compact summary of store normalization."""

    competition_column = (
        "competition_distance" if "competition_distance" in cleaned_df.columns else "CompetitionDistance"
    )
    promo2_column = "promo2" if "promo2" in cleaned_df.columns else "Promo2"
    original_count = len(original_df)
    cleaned_count = len(cleaned_df)

    return {
        "original_record_count": original_count,
        "cleaned_record_count": cleaned_count,
        "records_removed": original_count - cleaned_count,
        "stores_with_competition": int((cleaned_df[competition_column] < NO_COMPETITION_SENTINEL).sum()),
        "stores_with_promo2": int((cleaned_df[promo2_column].astype(int) == 1).sum()),
    }
