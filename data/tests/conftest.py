"""Shared fixtures for data module tests."""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest
import pytest_asyncio
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _get_async_postgres_url() -> str | None:
    raw_url = os.getenv("KPI_TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not raw_url or "postgres" not in raw_url:
        return None
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_url


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    database_url = _get_async_postgres_url()
    if not database_url:
        pytest.skip("PostgreSQL DATABASE_URL or KPI_TEST_DATABASE_URL is required for KPI mart integration tests")

    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
    except SQLAlchemyError as exc:
        pytest.skip(f"PostgreSQL test database is unavailable: {exc}")
    finally:
        await engine.dispose()


@pytest.fixture
def sample_train_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Store": [1, 1, 2],
            "DayOfWeek": [5, 4, 5],
            "Date": pd.to_datetime(["2015-07-31", "2015-07-30", "2015-07-31"]),
            "Sales": [5263, 5020, 6064],
            "Customers": [555, 534, 625],
            "Open": [1, 1, 1],
            "Promo": [1, 1, 1],
            "StateHoliday": ["0", "0", "0"],
            "SchoolHoliday": [1, 1, 1],
        }
    )


@pytest.fixture
def sample_store_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Store": [1, 2],
            "StoreType": ["c", "a"],
            "Assortment": ["a", "a"],
            "CompetitionDistance": [1270.0, 570.0],
            "CompetitionOpenSinceMonth": [9, 11],
            "CompetitionOpenSinceYear": [2008, 2007],
            "Promo2": [0, 1],
            "Promo2SinceWeek": [pd.NA, 13],
            "Promo2SinceYear": [pd.NA, 2010],
            "PromoInterval": [pd.NA, "Jan,Apr,Jul,Oct"],
        }
    )
