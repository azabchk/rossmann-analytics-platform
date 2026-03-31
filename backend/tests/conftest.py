import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["SUPABASE_JWT_SECRET"] = "test-secret"
os.environ["SUPABASE_JWT_ISSUER"] = "https://example.supabase.co/auth/v1"
os.environ["SUPABASE_JWT_AUDIENCE"] = "authenticated"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

from src.core.config import get_settings  # noqa: E402
from src.core.errors import AuthorizationError, NotFoundError  # noqa: E402
from src.main import create_app  # noqa: E402
from src.schemas.forecasts import (  # noqa: E402
    AccuracyMetrics,
    ForecastGenerationResponse,
    ForecastPoint,
    ForecastResponse,
    LowDataWarning,
    ModelMetadata,
    PublishedForecastResponse,
    StoreForecast,
)
from src.schemas.kpis import (  # noqa: E402
    DailyKPIResponse,
    KPIListResponse,
    KPISummaryResponse,
    MonthlyKPIResponse,
    WeeklyKPIResponse,
)
from src.schemas.stores import StoreListResponse, StoreResponse  # noqa: E402


STORE_ONE = StoreResponse(
    store_id=1,
    store_type="A",
    assortment="a",
    competition_distance=1000,
    promo2=False,
)
STORE_TWO = StoreResponse(
    store_id=2,
    store_type="B",
    assortment="b",
    competition_distance=750,
    promo2=True,
)
STORE_BY_ID = {1: STORE_ONE, 2: STORE_TWO}


def _create_token(
    *,
    user_id: str,
    role: str,
    email: str,
) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "app_metadata": {"role": role},
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def _accessible_store_ids_for_user(user_id: str) -> list[int]:
    if user_id.endswith("009"):
        return []
    if user_id.endswith("004"):
        return [1, 2]
    return [1]


def _authorized_store_ids_for_request(user_id: str, role: str | None = None) -> list[int]:
    if role == "admin":
        return sorted(STORE_BY_ID)
    return _accessible_store_ids_for_user(user_id)


def _build_daily_kpi_payload(store_id: int = 1) -> list[DailyKPIResponse]:
    return [
        DailyKPIResponse(
            kpi_id=101,
            store_id=store_id,
            kpi_date=date(2025, 2, 1),
            day_of_week=6,
            total_sales=1250.0,
            total_customers=200,
            transactions=1,
            avg_sales_per_transaction=1250.0,
            sales_per_customer=6.25,
            is_promo_day=True,
            has_state_holiday=False,
            has_school_holiday=False,
            is_store_open=True,
        ),
        DailyKPIResponse(
            kpi_id=102,
            store_id=store_id,
            kpi_date=date(2025, 2, 2),
            day_of_week=7,
            total_sales=1325.0,
            total_customers=210,
            transactions=1,
            avg_sales_per_transaction=1325.0,
            sales_per_customer=6.31,
            is_promo_day=False,
            has_state_holiday=False,
            has_school_holiday=True,
            is_store_open=True,
        ),
    ]


def _build_weekly_kpi_payload(store_id: int = 1) -> list[WeeklyKPIResponse]:
    return [
        WeeklyKPIResponse(
            kpi_id=201,
            store_id=store_id,
            week_start_date=date(2025, 1, 27),
            week_end_date=date(2025, 2, 2),
            iso_week=5,
            year=2025,
            total_sales=2575.0,
            total_customers=410,
            total_transactions=2,
            avg_daily_sales=1287.5,
            avg_daily_customers=205.0,
            avg_daily_transactions=1.0,
            promo_days_count=1,
            holiday_days_count=1,
            open_days_count=2,
            closed_days_count=0,
        )
    ]


def _build_monthly_kpi_payload(store_id: int = 1) -> list[MonthlyKPIResponse]:
    return [
        MonthlyKPIResponse(
            kpi_id=301,
            store_id=store_id,
            year=2025,
            month=2,
            month_name="February",
            total_sales=2575.0,
            total_customers=410,
            total_transactions=2,
            avg_daily_sales=1287.5,
            avg_daily_customers=205.0,
            avg_daily_transactions=1.0,
            days_in_month=28,
            promo_days_count=1,
            holiday_days_count=1,
            open_days_count=2,
            closed_days_count=0,
            active_weeks_count=1,
            mom_sales_growth_pct=None,
            mom_customers_growth_pct=None,
            yoy_sales_growth_pct=None,
            yoy_customers_growth_pct=None,
        )
    ]


@pytest.fixture(autouse=True)
def reset_settings_cache() -> None:
    get_settings.cache_clear()


def _build_test_app():
    app = create_app()

    mock_store_service = MagicMock()

    async def mock_get_accessible_stores(user_id: str, role: str | None = None):
        store_ids = _authorized_store_ids_for_request(user_id, role)
        stores = [STORE_BY_ID[store_id] for store_id in store_ids if store_id in STORE_BY_ID]
        return StoreListResponse(stores=stores, count=len(stores), total=len(stores))

    async def mock_get_store_by_id(user_id: str, store_id: int, role: str | None = None):
        if store_id not in STORE_BY_ID:
            raise NotFoundError(f"Store {store_id} was not found")
        if store_id not in _authorized_store_ids_for_request(user_id, role):
            raise AuthorizationError(f"You do not have access to store {store_id}")
        return STORE_BY_ID[store_id]

    async def mock_can_access_store(
        user_id: str,
        store_id: int,
        role: str | None = None,
    ) -> bool:
        return store_id in _authorized_store_ids_for_request(user_id, role)

    async def mock_get_store_summary(user_id: str, role: str | None = None):
        accessible_ids = _authorized_store_ids_for_request(user_id, role)
        return {
            "total_stores": len(accessible_ids),
            "type_a_count": 1 if 1 in accessible_ids else 0,
            "type_b_count": 1 if 2 in accessible_ids else 0,
            "type_c_count": 0,
            "type_d_count": 0,
            "avg_competition_distance": 875.0 if accessible_ids == [1, 2] else 1000.0 if accessible_ids else 0.0,
            "stores_with_promo2": 1 if 2 in accessible_ids else 0,
        }

    async def mock_get_accessible_store_ids(user_id: str, role: str | None = None):
        return _authorized_store_ids_for_request(user_id, role)

    mock_store_service.get_accessible_stores = AsyncMock(side_effect=mock_get_accessible_stores)
    mock_store_service.get_store_by_id = AsyncMock(side_effect=mock_get_store_by_id)
    mock_store_service.can_access_store = AsyncMock(side_effect=mock_can_access_store)
    mock_store_service.get_store_summary = AsyncMock(side_effect=mock_get_store_summary)
    mock_store_service.get_accessible_store_ids = AsyncMock(side_effect=mock_get_accessible_store_ids)

    mock_kpi_service = MagicMock()

    async def mock_get_daily_kpis(
        *,
        user_id: str,
        role: str | None = None,
        store_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 100,
    ):
        accessible_ids = _authorized_store_ids_for_request(user_id, role)
        if store_id is not None and store_id not in accessible_ids:
            raise AuthorizationError(f"You do not have access to store {store_id}")
        if not accessible_ids:
            return KPIListResponse(kpis=[], count=0, total=0, summary=None)

        target_store = store_id or accessible_ids[0]
        payload = _build_daily_kpi_payload(target_store)
        if start_date is not None:
            payload = [item for item in payload if item.kpi_date >= start_date]
        if end_date is not None:
            payload = [item for item in payload if item.kpi_date <= end_date]
        payload = payload[(page - 1) * page_size : (page - 1) * page_size + page_size]

        summary = None
        if payload:
            summary = KPISummaryResponse(
                total_records=len(payload),
                total_sales=sum(item.total_sales for item in payload),
                total_customers=sum(item.total_customers for item in payload),
                avg_daily_sales=sum(item.total_sales for item in payload) / len(payload),
                promo_days=sum(1 for item in payload if item.is_promo_day),
                holiday_days=sum(
                    1
                    for item in payload
                    if item.has_state_holiday or item.has_school_holiday
                ),
            )
        return KPIListResponse(
            kpis=payload,
            count=len(payload),
            total=len(payload),
            summary=summary,
        )

    async def mock_get_weekly_kpis(
        *,
        user_id: str,
        role: str | None = None,
        store_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 52,
    ):
        accessible_ids = _authorized_store_ids_for_request(user_id, role)
        if store_id is not None and store_id not in accessible_ids:
            raise AuthorizationError(f"You do not have access to store {store_id}")
        if not accessible_ids:
            return KPIListResponse(kpis=[], count=0, total=0, summary=None)

        payload = _build_weekly_kpi_payload(store_id or accessible_ids[0])
        return KPIListResponse(kpis=payload[:page_size], count=len(payload[:page_size]), total=len(payload), summary=None)

    async def mock_get_monthly_kpis(
        *,
        user_id: str,
        role: str | None = None,
        store_id: int | None = None,
        year: int | None = None,
        page: int = 1,
        page_size: int = 12,
    ):
        accessible_ids = _authorized_store_ids_for_request(user_id, role)
        if store_id is not None and store_id not in accessible_ids:
            raise AuthorizationError(f"You do not have access to store {store_id}")
        if not accessible_ids:
            return KPIListResponse(kpis=[], count=0, total=0, summary=None)

        payload = _build_monthly_kpi_payload(store_id or accessible_ids[0])
        if year is not None:
            payload = [item for item in payload if item.year == year]
        return KPIListResponse(kpis=payload[:page_size], count=len(payload[:page_size]), total=len(payload), summary=None)

    async def mock_get_daily_summary(
        *,
        user_id: str,
        role: str | None = None,
        store_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        response = await mock_get_daily_kpis(
            user_id=user_id,
            role=role,
            store_id=store_id,
            start_date=start_date,
            end_date=end_date,
        )
        if response.summary is None:
            raise NotFoundError(f"No KPI data found for store {store_id}")
        return response.summary

    mock_kpi_service.get_daily_kpis = AsyncMock(side_effect=mock_get_daily_kpis)
    mock_kpi_service.get_weekly_kpis = AsyncMock(side_effect=mock_get_weekly_kpis)
    mock_kpi_service.get_monthly_kpis = AsyncMock(side_effect=mock_get_monthly_kpis)
    mock_kpi_service.get_daily_summary = AsyncMock(side_effect=mock_get_daily_summary)

    sample_sales_records = [
        {
            "sales_record_id": 1001,
            "store_id": 1,
            "sales_date": date(2025, 2, 2),
            "day_of_week": 7,
            "sales": 1325,
            "customers": 210,
            "is_open": True,
            "promo": False,
            "state_holiday": "0",
            "school_holiday": True,
        },
        {
            "sales_record_id": 1002,
            "store_id": 2,
            "sales_date": date(2025, 2, 1),
            "day_of_week": 6,
            "sales": 2575,
            "customers": 410,
            "is_open": True,
            "promo": True,
            "state_holiday": "0",
            "school_holiday": False,
        },
    ]

    def _filter_sales_records(
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        records = [record for record in sample_sales_records if record["store_id"] in store_ids]
        if start_date is not None:
            records = [record for record in records if record["sales_date"] >= start_date]
        if end_date is not None:
            records = [record for record in records if record["sales_date"] <= end_date]
        return records

    mock_sales_repository = MagicMock()

    async def mock_get_sales_records(
        *,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        records = _filter_sales_records(store_ids, start_date, end_date)
        return records[offset : offset + limit]

    async def mock_count_sales_records(
        *,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        return len(_filter_sales_records(store_ids, start_date, end_date))

    async def mock_get_sales_summary(
        *,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        records = _filter_sales_records(store_ids, start_date, end_date)
        if not records:
            return None
        total_sales = sum(record["sales"] for record in records)
        total_customers = sum(record["customers"] or 0 for record in records)
        return {
            "total_sales": total_sales,
            "total_customers": total_customers,
            "total_transactions": sum(1 for record in records if record["is_open"]),
            "avg_daily_sales": total_sales / len(records),
            "avg_daily_customers": total_customers / len(records),
            "promo_days": sum(1 for record in records if record["promo"]),
            "holiday_days": sum(
                1
                for record in records
                if record["school_holiday"] or record["state_holiday"] not in {None, "0"}
            ),
        }

    mock_sales_repository.get_sales_records = AsyncMock(side_effect=mock_get_sales_records)
    mock_sales_repository.count_sales_records = AsyncMock(side_effect=mock_count_sales_records)
    mock_sales_repository.get_sales_summary = AsyncMock(side_effect=mock_get_sales_summary)

    sample_model = ModelMetadata(
        model_id="model-baseline-active",
        model_name="baseline-demo",
        model_type="baseline",
        version="2026.03.27",
        is_active=True,
        published_at=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
    )
    sample_accuracy = AccuracyMetrics(mape=12.4, rmse=845.2, mae=602.8)
    sample_points = [
        ForecastPoint(
            forecast_date=date(2026, 3, 28),
            predicted_sales=5321.0,
            lower_bound=4800.0,
            upper_bound=5800.0,
            confidence_level=95.0,
        ),
        ForecastPoint(
            forecast_date=date(2026, 3, 29),
            predicted_sales=5488.0,
            lower_bound=4950.0,
            upper_bound=6010.0,
            confidence_level=95.0,
        ),
    ]

    mock_forecast_service = MagicMock()

    async def mock_get_published_forecasts(
        store_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        if store_id != 1:
            raise NotFoundError(f"No published forecasts found for store {store_id}")
        return PublishedForecastResponse(
            store_id=1,
            model_type="baseline",
            forecast_start_date=sample_points[0].forecast_date,
            forecast_end_date=sample_points[-1].forecast_date,
            model_metadata=sample_model,
            accuracy_metrics=sample_accuracy,
            forecasts=sample_points,
            total=len(sample_points),
            offset=offset,
            limit=limit,
        )

    async def mock_get_forecasts_for_stores(
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        forecasts = []
        warnings = []
        if 1 in store_ids:
            forecasts.append(
                StoreForecast(
                    store_id=1,
                    model_metadata=sample_model,
                    accuracy_metrics=sample_accuracy,
                    forecasts=sample_points,
                )
            )
        if 2 in store_ids:
            warnings.append(
                LowDataWarning(
                    store_id=2,
                    warning_type="insufficient_history",
                    warning_message="Insufficient history for reliable forecasting",
                    days_of_history=21,
                )
            )
        return ForecastResponse(forecasts=forecasts, warnings=warnings)

    async def mock_get_active_model(model_type: str):
        if model_type == "baseline":
            return sample_model
        return None

    async def mock_get_store_warnings(store_ids: list[int]):
        if 1 in store_ids:
            return []
        return [
            LowDataWarning(
                store_id=2,
                warning_type="insufficient_history",
                warning_message="Insufficient history for reliable forecasting",
                days_of_history=21,
            )
        ]

    async def mock_get_model_accuracy(model_id: str):
        if model_id == "missing-model":
            raise NotFoundError("No evaluations found for model missing-model")
        return sample_accuracy

    async def mock_generate_forecasts(
        store_ids: list[int],
        horizon_weeks: int,
        triggered_by: str | None,
    ):
        return ForecastGenerationResponse(
            job_id="job-123",
            status="completed",
            stores_requested=store_ids,
            estimated_completion_time=datetime.now(timezone.utc) + timedelta(seconds=1),
            message="Published 2 forecast points using model model-baseline-active",
        )

    mock_forecast_service.get_published_forecasts = AsyncMock(side_effect=mock_get_published_forecasts)
    mock_forecast_service.get_forecasts_for_stores = AsyncMock(side_effect=mock_get_forecasts_for_stores)
    mock_forecast_service.get_active_model = AsyncMock(side_effect=mock_get_active_model)
    mock_forecast_service.get_store_warnings = AsyncMock(side_effect=mock_get_store_warnings)
    mock_forecast_service.get_model_accuracy = AsyncMock(side_effect=mock_get_model_accuracy)
    mock_forecast_service.generate_forecasts = AsyncMock(side_effect=mock_generate_forecasts)

    from src.api.v1 import forecasts as forecasts_api
    from src.api.v1 import kpis as kpis_api
    from src.api.v1 import sales as sales_api
    from src.api.v1 import stores as stores_api

    async def override_kpi_service():
        return mock_kpi_service

    async def override_store_service():
        return mock_store_service

    async def override_forecast_service():
        return mock_forecast_service

    async def override_sales_repository():
        return mock_sales_repository

    app.dependency_overrides[kpis_api.get_kpi_service] = override_kpi_service
    app.dependency_overrides[sales_api.get_sales_repository] = override_sales_repository
    app.dependency_overrides[sales_api.get_store_service] = override_store_service
    app.dependency_overrides[stores_api.get_store_service] = override_store_service
    app.dependency_overrides[forecasts_api.get_store_service] = override_store_service
    app.dependency_overrides[forecasts_api.get_forecast_service] = override_forecast_service

    return app


@pytest.fixture()
def app():
    test_app = _build_test_app()
    yield test_app
    test_app.dependency_overrides = {}


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def auth_token() -> str:
    return _create_token(
        user_id="00000000-0000-0000-0000-000000000001",
        role="admin",
        email="admin@example.com",
    )


@pytest_asyncio.fixture()
async def async_client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest_asyncio.fixture()
async def authenticated_client(async_client: AsyncClient):
    async_client.headers["Authorization"] = (
        f"Bearer {_create_token(user_id='00000000-0000-0000-0000-000000000001', role='admin', email='admin@example.com')}"
    )
    yield async_client
    async_client.headers.clear()


@pytest_asyncio.fixture()
async def admin_client(async_client: AsyncClient):
    async_client.headers["Authorization"] = (
        f"Bearer {_create_token(user_id='00000000-0000-0000-0000-000000000001', role='admin', email='admin@example.com')}"
    )
    yield async_client
    async_client.headers.clear()


@pytest_asyncio.fixture()
async def store_manager_client(async_client: AsyncClient):
    async_client.headers["Authorization"] = (
        f"Bearer {_create_token(user_id='00000000-0000-0000-0000-000000000003', role='store_manager', email='manager@example.com')}"
    )
    yield async_client
    async_client.headers.clear()


@pytest.fixture()
def test_store_manager_user():
    return {"user_id": "00000000-0000-0000-0000-000000000003", "role": "store_manager"}


@pytest.fixture()
def test_analyst_user():
    return {"user_id": "00000000-0000-0000-0000-000000000002", "role": "data_analyst"}


@pytest.fixture()
def test_admin_user():
    return {"user_id": "00000000-0000-0000-0000-000000000001", "role": "admin"}
