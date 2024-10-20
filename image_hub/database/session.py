from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from image_hub.config import get_settings


def get_engine() -> AsyncEngine:
    if not hasattr(get_engine, 'engine'):
        get_engine.engine = create_async_engine(get_settings().database_url, echo=True, future=True)

    return get_engine.engine



async def get_session() -> AsyncSession:
    engine = get_engine()
    async with AsyncSession(engine) as session:
        yield session
