"""Access-aware store service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import AuthorizationError, NotFoundError
from src.observability.analytics_logging import event_logger
from src.repositories.store_repository import StoreRepository
from src.schemas.stores import StoreListResponse, StoreResponse


class StoreService:
    """Business logic for store retrieval and access checks."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.store_repo = StoreRepository(db_session)

    async def get_accessible_stores(
        self,
        user_id: str,
        role: str | None = None,
    ) -> StoreListResponse:
        stores = await self._get_authorized_stores(user_id=user_id, role=role)
        return StoreListResponse(
            stores=[StoreResponse.model_validate(store) for store in stores],
            count=len(stores),
            total=len(stores),
        )

    async def get_accessible_store_ids(
        self,
        user_id: str,
        role: str | None = None,
    ) -> list[int]:
        stores = await self._get_authorized_stores(user_id=user_id, role=role)
        return [store.store_id for store in stores]

    async def get_store_by_id(
        self,
        user_id: str,
        store_id: int,
        role: str | None = None,
    ) -> StoreResponse:
        store = await self.store_repo.get_store_by_id(store_id)
        if store is None:
            raise NotFoundError(f"Store {store_id} was not found")

        granted = self._is_admin(role) or await self.store_repo.can_user_access_store(user_id, store_id)
        event_logger.log_store_access(
            user_id=user_id,
            store_id=store_id,
            granted=granted,
            reason=(
                "admin_role_bypass"
                if granted and self._is_admin(role)
                else None if granted else "store_access_mapping_missing"
            ),
        )
        if not granted:
            raise AuthorizationError(f"You do not have access to store {store_id}")
        return StoreResponse.model_validate(store)

    async def can_access_store(
        self,
        user_id: str,
        store_id: int,
        role: str | None = None,
    ) -> bool:
        if self._is_admin(role):
            granted = await self.store_repo.get_store_by_id(store_id) is not None
            event_logger.log_store_access(
                user_id=user_id,
                store_id=store_id,
                granted=granted,
                reason="admin_role_bypass" if granted else "store_not_found",
            )
            return granted

        granted = await self.store_repo.can_user_access_store(user_id, store_id)
        event_logger.log_store_access(
            user_id=user_id,
            store_id=store_id,
            granted=granted,
            reason=None if granted else "store_access_mapping_missing",
        )
        return granted

    async def get_store_summary(
        self,
        user_id: str,
        role: str | None = None,
    ) -> dict[str, Any]:
        stores = await self._get_authorized_stores(user_id=user_id, role=role)
        return self._build_store_summary(stores)

    async def _get_authorized_stores(self, user_id: str, role: str | None = None):
        if self._is_admin(role):
            return await self.store_repo.get_all_stores()
        return await self.store_repo.get_accessible_stores(user_id)

    @staticmethod
    def _is_admin(role: str | None) -> bool:
        return role == "admin"

    @staticmethod
    def _build_store_summary(stores: list) -> dict[str, Any]:
        total_stores = len(stores)
        competition_distances = [store.competition_distance for store in stores]
        return {
            "total_stores": total_stores,
            "type_a_count": sum(1 for store in stores if store.store_type == "A"),
            "type_b_count": sum(1 for store in stores if store.store_type == "B"),
            "type_c_count": sum(1 for store in stores if store.store_type == "C"),
            "type_d_count": sum(1 for store in stores if store.store_type == "D"),
            "avg_competition_distance": (
                float(sum(competition_distances) / total_stores) if competition_distances else 0.0
            ),
            "stores_with_promo2": sum(1 for store in stores if store.promo2),
        }
