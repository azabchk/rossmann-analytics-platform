from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import text

from src.repositories.base import BaseRepository


@dataclass(slots=True)
class LocalAuthUser:
    user_id: str
    email: str
    role: str
    password_hash: str


class LocalAuthRepository(BaseRepository):
    async def ensure_auth_tables(self) -> None:
        await self.session.execute(text("CREATE SCHEMA IF NOT EXISTS internal"))
        await self.session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS internal.user_profiles (
                  user_id uuid PRIMARY KEY,
                  email text NOT NULL UNIQUE,
                  role text NOT NULL CHECK (
                    role IN ('admin', 'store_manager', 'marketing_manager', 'data_analyst', 'academic_demo')
                  ),
                  created_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
                  updated_at timestamptz NOT NULL DEFAULT timezone('utc', now())
                )
                """
            )
        )
        await self.session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS internal.local_auth_credentials (
                  user_id uuid PRIMARY KEY REFERENCES internal.user_profiles(user_id) ON DELETE CASCADE,
                  password_hash text NOT NULL,
                  created_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
                  updated_at timestamptz NOT NULL DEFAULT timezone('utc', now())
                )
                """
            )
        )
        await self.session.commit()

    async def get_user_by_email(self, email: str) -> LocalAuthUser | None:
        await self.ensure_auth_tables()
        result = await self.session.execute(
            text(
                """
                SELECT
                  up.user_id::text,
                  up.email,
                  up.role,
                  lac.password_hash
                FROM internal.user_profiles up
                JOIN internal.local_auth_credentials lac ON lac.user_id = up.user_id
                WHERE lower(up.email) = lower(:email)
                """
            ),
            {"email": email},
        )
        row = result.fetchone()
        if row is None:
            return None
        return LocalAuthUser(
            user_id=row[0],
            email=row[1],
            role=row[2],
            password_hash=row[3],
        )

    async def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        role: str = "data_analyst",
    ) -> LocalAuthUser:
        await self.ensure_auth_tables()
        user_id = str(uuid4())

        await self.session.execute(
            text(
                """
                INSERT INTO internal.user_profiles (
                  user_id,
                  email,
                  role
                )
                VALUES (
                  CAST(:user_id AS uuid),
                  :email,
                  :role
                )
                """
            ),
            {
                "user_id": user_id,
                "email": email,
                "role": role,
            },
        )
        await self.session.execute(
            text(
                """
                INSERT INTO internal.local_auth_credentials (
                  user_id,
                  password_hash
                )
                VALUES (
                  CAST(:user_id AS uuid),
                  :password_hash
                )
                """
            ),
            {
                "user_id": user_id,
                "password_hash": password_hash,
            },
        )
        await self._grant_default_store_access(user_id=user_id, store_id=1)
        await self.session.commit()
        return LocalAuthUser(
            user_id=user_id,
            email=email,
            role=role,
            password_hash=password_hash,
        )

    async def _grant_default_store_access(self, *, user_id: str, store_id: int) -> None:
        stores_table_exists = bool(
            (
                await self.session.execute(
                    text(
                        """
                        SELECT EXISTS (
                          SELECT 1
                          FROM information_schema.tables
                          WHERE table_schema = 'internal'
                            AND table_name = 'stores'
                        )
                        """
                    )
                )
            ).scalar()
        )
        store_access_table_exists = bool(
            (
                await self.session.execute(
                    text(
                        """
                        SELECT EXISTS (
                          SELECT 1
                          FROM information_schema.tables
                          WHERE table_schema = 'internal'
                            AND table_name = 'store_access'
                        )
                        """
                    )
                )
            ).scalar()
        )
        if not stores_table_exists or not store_access_table_exists:
            return

        await self.session.execute(
            text(
                """
                INSERT INTO internal.store_access (
                  user_id,
                  store_id
                )
                SELECT
                  CAST(:user_id AS uuid),
                  :store_id
                WHERE EXISTS (
                  SELECT 1
                  FROM internal.stores
                  WHERE store_id = :store_id
                )
                ON CONFLICT (user_id, store_id) DO NOTHING
                """
            ),
            {
                "user_id": user_id,
                "store_id": store_id,
            },
        )
