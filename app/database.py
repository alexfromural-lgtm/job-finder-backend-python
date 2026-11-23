# =============================================================================
# app/database.py  —  DATABASE CONNECTION & SESSION FACTORY
# =============================================================================
# This module sets up the async SQLAlchemy connection to PostgreSQL.
# It provides two things every other module needs:
#   1. `Base`           – the declarative base class all ORM models inherit from.
#   2. `get_db()`       – a FastAPI dependency that yields a database session.
#
# LEARNING CONCEPT ► ORM (Object-Relational Mapper)
#   An ORM lets you work with database tables as Python classes instead of
#   writing raw SQL.  SQLAlchemy is Python's most popular ORM.
#
#   Without ORM (raw SQL):
#       cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#       row = cursor.fetchone()
#       name = row[0]
#
#   With SQLAlchemy ORM:
#       user = await db.get(User, user_id)
#       name = user.name
#
# LEARNING CONCEPT ► Async vs Sync DB access
#   Traditional SQLAlchemy is synchronous (blocks the thread while waiting
#   for the DB).  For FastAPI (which is async/non-blocking) we use the async
#   extension with `asyncpg` as the PostgreSQL driver.
# =============================================================================

# `create_async_engine` creates a connection pool to the database.
# `AsyncSession` is the async version of SQLAlchemy's Session object.
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# `AsyncSessionLocal` is a session factory — calling it returns a new session.
from sqlalchemy.orm import sessionmaker

# `DeclarativeBase` is the base class for all ORM models.
# Every model class inherits from `Base` and gets table-mapping for free.
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# =============================================================================
# 1. DECLARATIVE BASE
# =============================================================================
# `Base` is the foundation of the ORM mapping system.  When a class inherits
# from `Base` and defines `__tablename__`, SQLAlchemy knows how to:
#   • map Python attributes → database columns
#   • generate INSERT / SELECT / UPDATE / DELETE SQL automatically
#
# LEARNING EXAMPLE ► minimal model using this Base:
#   class Tag(Base):
#       __tablename__ = "tags"
#       id: Mapped[int] = mapped_column(Integer, primary_key=True)
#       name: Mapped[str] = mapped_column(String)
# =============================================================================
class Base(DeclarativeBase):
    pass


# =============================================================================
# 2. ASYNC ENGINE
# =============================================================================
# `create_async_engine` establishes a connection POOL to the database.
# A pool keeps several connections open and reuses them — much faster than
# opening a fresh connection for every request.
#
# `echo=True` logs every SQL statement to stdout (useful for debugging,
# disable in production or it creates enormous logs).
#
# LEARNING NOTE ► asyncpg vs psycopg2:
#   The URL prefix `postgresql+asyncpg://` tells SQLAlchemy to use the asyncpg
#   driver instead of the synchronous psycopg2.
# =============================================================================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,  # log SQL only in dev
)

# =============================================================================
# 3. SESSION FACTORY
# =============================================================================
# `sessionmaker` returns a class (not an instance).  Calling
# `AsyncSessionLocal()` returns a new `AsyncSession` bound to our engine.
#
# Options explained:
#   class_=AsyncSession     → produce async sessions
#   expire_on_commit=False  → keep ORM objects usable after commit()
#                             (the default expires them so attributes raise
#                             errors unless you re-query — inconvenient in async)
#   bind=engine             → which database connection pool to use
#
# LEARNING EXAMPLE ► manual usage (without FastAPI dependency injection):
#   async with AsyncSessionLocal() as session:
#       result = await session.execute(select(User))
#       users = result.scalars().all()
# =============================================================================
AsyncSessionLocal = sessionmaker(  # type: ignore[call-overload]
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# =============================================================================
# 4. FASTAPI DEPENDENCY  —  `get_db`
# =============================================================================
# FastAPI's dependency injection system calls `get_db()` automatically before
# the route handler runs.  The `yield` turns this into a "context manager
# dependency" — code after `yield` runs as cleanup after the response is sent.
#
# LEARNING CONCEPT ► `yield` dependencies (like a try/finally block):
#   def get_db():
#       db = Session()
#       try:
#           yield db       ← route handler receives this value
#       finally:
#           db.close()     ← always runs, even if the handler raised an exception
#
# USAGE IN A ROUTE:
#   @router.get("/users")
#   async def list_users(db: AsyncSession = Depends(get_db)):
#       result = await db.execute(select(User))
#       return result.scalars().all()
#
# The `Depends(get_db)` syntax tells FastAPI:
#   "Before calling list_users, call get_db() and pass its yielded value as `db`."
# =============================================================================
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session          # ← handed to the route handler
        except Exception:
            await session.rollback()  # undo any uncommitted changes on error
            raise
        finally:
            await session.close()  # always close the session when done
