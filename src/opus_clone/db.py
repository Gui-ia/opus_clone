import threading
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from opus_clone.config import get_settings

# Thread-local storage for engine + session factory
# Each Dramatiq worker thread gets its own engine, avoiding event-loop conflicts
_local = threading.local()


def get_engine():
    if not hasattr(_local, "engine") or _local.engine is None:
        settings = get_settings()
        _local.engine = create_async_engine(
            settings.database_url_async,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=settings.app_env == "development",
        )
    return _local.engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if not hasattr(_local, "session_factory") or _local.session_factory is None:
        _local.session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _local.session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with get_db_session() as session:
        yield session


async def dispose_engine() -> None:
    if hasattr(_local, "engine") and _local.engine is not None:
        await _local.engine.dispose()
        _local.engine = None
        _local.session_factory = None


def reset_engine() -> None:
    """Reset the thread-local engine so it gets recreated in the current event loop.
    Call this at the start of asyncio.run() in workers."""
    _local.engine = None
    _local.session_factory = None


@asynccontextmanager
async def get_worker_db_session() -> AsyncGenerator[AsyncSession, None]:
    """DB session for Dramatiq workers — creates a fresh engine per call
    to avoid event-loop conflicts with asyncio.run()."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url_async,
        pool_size=2,
        max_overflow=3,
        pool_pre_ping=True,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await engine.dispose()
