import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — provides .ini file values
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging (unless suppressed)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import all models so Alembic can discover metadata for autogenerate
# ---------------------------------------------------------------------------
from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401 — side-effect: registers all models

target_metadata = Base.metadata

# Override sqlalchemy.url from alembic.ini with the one from pydantic-settings
# (replaces asyncpg driver with standard psycopg for Alembic sync operations)
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("+asyncpg", ""),  # Alembic needs sync URL
)


# ---------------------------------------------------------------------------
# Offline migration mode
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL only)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode (async)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async SQLAlchemy engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
