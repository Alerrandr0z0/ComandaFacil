import asyncio
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.settings import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Dynamic ORM model discovery ──────────────────────────────────────────
# Every `app/{context}/infrastructure/orm_models.py` is auto-imported
# so Alembic detects its tables. No manual import list to maintain.
from pathlib import Path  # noqa: E402

import app  # noqa: E402

_context_dir = Path(app.__file__).resolve().parent
for _orm_path in sorted(_context_dir.glob("*/infrastructure/orm_models.py")):
    _ctx = _orm_path.parent.parent.name
    __import__(f"app.{_ctx}.infrastructure.orm_models", fromlist=[""])

import app.shared.outbox  # noqa: E402
from app.shared.base_orm import Base  # noqa: E402

target_metadata = Base.metadata


def get_url() -> str:
    settings = get_settings()
    return settings.database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
