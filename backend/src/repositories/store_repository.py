"""Store repository for governed store access and metadata queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from src.repositories.base import BaseRepository


@dataclass(slots=True)
class Store:
    store_id: int
    store_type: str
    assortment: str
    competition_distance: int
    promo2: bool


class StoreRepository(BaseRepository):
    """Repository for store metadata and access lookups."""

    @staticmethod
    def _map_store_rows(rows) -> list[Store]:
        return [
            Store(
                store_id=row[0],
                store_type=row[1],
                assortment=row[2],
                competition_distance=row[3],
                promo2=row[4],
            )
            for row in rows
        ]

    async def get_all_stores(self) -> list[Store]:
        result = await self.session.execute(
            text(
                """
                SELECT
                    store_id,
                    store_type,
                    assortment,
                    competition_distance,
                    promo2
                FROM internal.stores
                ORDER BY store_id
                """
            )
        )
        return self._map_store_rows(result.fetchall())

    async def get_accessible_stores(self, user_id: str) -> list[Store]:
        result = await self.session.execute(
            text(
                """
                SELECT
                    s.store_id,
                    s.store_type,
                    s.assortment,
                    s.competition_distance,
                    s.promo2
                FROM internal.stores s
                JOIN internal.store_access sa ON sa.store_id = s.store_id
                WHERE sa.user_id = :user_id
                ORDER BY s.store_id
                """
            ),
            {"user_id": user_id},
        )
        return self._map_store_rows(result.fetchall())

    async def get_store_by_id(self, store_id: int) -> Store | None:
        result = await self.session.execute(
            text(
                """
                SELECT
                    store_id,
                    store_type,
                    assortment,
                    competition_distance,
                    promo2
                FROM internal.stores
                WHERE store_id = :store_id
                """
            ),
            {"store_id": store_id},
        )
        row = result.fetchone()
        if row is None:
            return None
        return Store(
            store_id=row[0],
            store_type=row[1],
            assortment=row[2],
            competition_distance=row[3],
            promo2=row[4],
        )

    async def can_user_access_store(self, user_id: str, store_id: int) -> bool:
        result = await self.session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM internal.store_access
                    WHERE user_id = :user_id
                      AND store_id = :store_id
                )
                """
            ),
            {"user_id": user_id, "store_id": store_id},
        )
        return bool(result.scalar())

    async def get_store_summary(self, user_id: str) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                """
                SELECT
                    count(distinct s.store_id)::integer AS total_stores,
                    count(distinct case when s.store_type = 'A' then s.store_id end)::integer AS type_a_count,
                    count(distinct case when s.store_type = 'B' then s.store_id end)::integer AS type_b_count,
                    count(distinct case when s.store_type = 'C' then s.store_id end)::integer AS type_c_count,
                    count(distinct case when s.store_type = 'D' then s.store_id end)::integer AS type_d_count,
                    avg(s.competition_distance)::numeric AS avg_competition_distance,
                    count(distinct case when s.promo2 then s.store_id end)::integer AS stores_with_promo2
                FROM internal.stores s
                JOIN internal.store_access sa ON sa.store_id = s.store_id
                WHERE sa.user_id = :user_id
                """
            ),
            {"user_id": user_id},
        )
        row = result.fetchone()
        return {
            "total_stores": row[0] if row else 0,
            "type_a_count": row[1] if row else 0,
            "type_b_count": row[2] if row else 0,
            "type_c_count": row[3] if row else 0,
            "type_d_count": row[4] if row else 0,
            "avg_competition_distance": float(row[5]) if row and row[5] is not None else 0.0,
            "stores_with_promo2": row[6] if row else 0,
        }
