from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event


ROOT = Path(__file__).resolve().parents[1]


def database_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def migration_config(path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url(path))
    return config


def migrate_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_tables: set[str] = set()
    if path.exists():
        with sqlite3.connect(path) as connection:
            existing_tables = {
                str(row[0])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
    config = migration_config(path)
    if "settings" in existing_tables and "alembic_version" not in existing_tables:
        command.stamp(config, "0001")
    command.upgrade(config, "head")


def create_database_engine(path: Path) -> Engine:
    engine = create_engine(database_url(path), connect_args={"check_same_thread": False, "timeout": 5})

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
