from __future__ import annotations

import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db_models import Base


config = context.config
target_metadata = Base.metadata

if not config.get_main_option("sqlalchemy.url"):
    api_root = Path(config.config_file_name or __file__).resolve().parent
    if api_root.name == "alembic":
        api_root = api_root.parent
    database_path = Path(os.getenv("IOT_BENCH_DB", api_root / "data" / "iot.db"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.resolve().as_posix()}")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
