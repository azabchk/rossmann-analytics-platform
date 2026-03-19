from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Thin repository base to keep database access behind backend abstractions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
