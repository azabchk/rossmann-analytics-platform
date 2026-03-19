from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.db.session import get_db_session


def get_settings_dependency() -> Settings:
    return get_settings()


async def get_database_session(
    session: AsyncIterator[AsyncSession] = Depends(get_db_session),
) -> AsyncIterator[AsyncSession]:
    async for item in session:
        yield item
