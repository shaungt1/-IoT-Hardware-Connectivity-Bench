from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS connection_profiles (
                    port TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    manufacturer TEXT,
                    serial_number TEXT,
                    vid TEXT,
                    pid TEXT,
                    is_esp32 INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    last_connected_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS wireless_profiles (
                    kind TEXT NOT NULL,
                    identifier TEXT NOT NULL,
                    name TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_connected_at TEXT NOT NULL,
                    PRIMARY KEY(kind, identifier)
                );
                CREATE TABLE IF NOT EXISTS operation_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL,
                    identifier TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    status TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    output TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def get_setting(self, key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def remember_profile(self, profile: dict[str, Any], status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO connection_profiles(
                    port, description, manufacturer, serial_number, vid, pid,
                    is_esp32, status, last_connected_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(port) DO UPDATE SET
                    description = excluded.description,
                    manufacturer = excluded.manufacturer,
                    serial_number = excluded.serial_number,
                    vid = excluded.vid,
                    pid = excluded.pid,
                    is_esp32 = excluded.is_esp32,
                    status = excluded.status,
                    last_connected_at = excluded.last_connected_at
                """,
                (
                    profile["device"],
                    profile["description"],
                    profile.get("manufacturer"),
                    profile.get("serial_number"),
                    profile.get("vid"),
                    profile.get("pid"),
                    int(bool(profile["is_esp32"])),
                    status,
                    now,
                ),
            )
        self.set_setting("selected_port", str(profile["device"]))

    def profiles(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM connection_profiles ORDER BY last_connected_at DESC"
            ).fetchall()
        return [
            {
                **dict(row),
                "is_esp32": bool(row["is_esp32"]),
            }
            for row in rows
        ]

    def remember_wireless_profile(
        self,
        kind: str,
        identifier: str,
        name: str,
        metadata: dict[str, Any],
        status: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO wireless_profiles(kind, identifier, name, metadata, status, last_connected_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(kind, identifier) DO UPDATE SET
                    name = excluded.name,
                    metadata = excluded.metadata,
                    status = excluded.status,
                    last_connected_at = excluded.last_connected_at
                """,
                (kind, identifier, name, json.dumps(metadata), status, now),
            )

    def wireless_profiles(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM wireless_profiles ORDER BY last_connected_at DESC"
            ).fetchall()
        return [
            {
                **dict(row),
                "metadata": json.loads(row["metadata"]),
            }
            for row in rows
        ]

    def record_operation(
        self,
        plan_id: str,
        identifier: str,
        operation_id: str,
        risk: str,
        status: str,
        preview: str,
        output: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO operation_audit(plan_id, identifier, operation_id, risk, status, preview, output, recorded_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (plan_id, identifier, operation_id, risk, status, preview, output[-64_000:], now),
            )

    def operation_history(self, identifier: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM operation_audit"
        parameters: tuple[Any, ...] = ()
        if identifier:
            query += " WHERE identifier = ?"
            parameters = (identifier,)
        query += " ORDER BY sequence DESC LIMIT ?"
        parameters = (*parameters, max(1, min(limit, 500)))
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]
