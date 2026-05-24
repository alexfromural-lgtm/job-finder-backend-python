from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ---------------------------------------------------------------------------
# Engine — uses asyncpg driver for full async I/O
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,  # Log SQL in dev, silent in prod
    pool_pre_ping=True,            # Verify connections before using from pool
    pool_size=10,
    max_overflow=20,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Keep objects accessible after commit
)


# ---------------------------------------------------------------------------
# Declarative base — all models inherit from this
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a session and ensures it is closed after use
# ---------------------------------------------------------------------------
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
