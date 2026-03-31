from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.services.forecast_service import ForecastService


class _RepositoryStub:
    def __init__(self, model_row: dict | None) -> None:
        self._model_row = model_row

    async def get_active_model(self, model_type: str) -> dict | None:
        return self._model_row


@pytest.mark.asyncio
async def test_get_active_model_casts_uuid_model_id_to_string() -> None:
    model_id = uuid4()
    service = ForecastService(
        _RepositoryStub(
            {
                "model_id": model_id,
                "model_name": "baseline-demo",
                "model_type": "baseline",
                "version": "2026.03.28",
                "is_active": True,
                "published_at": datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
            }
        )
    )

    model = await service.get_active_model("baseline")

    assert model is not None
    assert model.model_id == str(model_id)
    assert isinstance(model.model_id, str)
