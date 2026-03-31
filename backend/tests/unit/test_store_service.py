from dataclasses import dataclass

import pytest

from src.core.errors import AuthorizationError
from src.services.store_service import StoreService


@dataclass(slots=True)
class _Store:
    store_id: int
    store_type: str
    assortment: str
    competition_distance: int
    promo2: bool


class _RepositoryStub:
    def __init__(self) -> None:
        self._stores = {
            1: _Store(1, "A", "a", 1000, False),
            2: _Store(2, "B", "b", 750, True),
        }

    async def get_all_stores(self):
        return list(self._stores.values())

    async def get_accessible_stores(self, user_id: str):
        if user_id == "manager":
            return [self._stores[1]]
        return []

    async def get_store_by_id(self, store_id: int):
        return self._stores.get(store_id)

    async def can_user_access_store(self, user_id: str, store_id: int):
        return user_id == "manager" and store_id == 1


def _build_service() -> StoreService:
    service = StoreService.__new__(StoreService)
    service.store_repo = _RepositoryStub()
    return service


@pytest.mark.asyncio
async def test_admin_get_accessible_stores_returns_all_stores() -> None:
    service = _build_service()

    response = await service.get_accessible_stores("admin-user", role="admin")

    assert response.count == 2
    assert {store.store_id for store in response.stores} == {1, 2}


@pytest.mark.asyncio
async def test_admin_can_access_existing_store_without_mapping() -> None:
    service = _build_service()

    granted = await service.can_access_store("admin-user", 2, role="admin")

    assert granted is True


@pytest.mark.asyncio
async def test_non_admin_still_requires_store_mapping() -> None:
    service = _build_service()

    with pytest.raises(AuthorizationError):
        await service.get_store_by_id("manager", 2, role="store_manager")
