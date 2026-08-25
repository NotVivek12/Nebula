from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create async database engine
# pool_pre_ping ensures stale connections are recycled
engine = create_async_engine(
    settings.ASYNC_DATABASE_URI,
    pool_pre_ping=True,
    future=True,
    echo=False,  # Set to True for debugging SQL queries
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator to yield an asynchronous database session.

    Ensures the session is cleanly closed after request completion.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
