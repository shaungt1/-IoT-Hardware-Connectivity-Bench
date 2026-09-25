from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .database import create_database_engine, migrate_database
from .db_models import (
    ConnectionProfile,
    InspectionSnapshot,
    OperationAudit,
    PrototypeProjectRecord,
    Setting,
    TestResultRecord,
    VisualEvidenceRecord,
    WirelessProfile,
)


SENSITIVE_KEYS = {
    "password", "passphrase", "secret", "token", "api_key", "private_key", "credential",
    "ssid", "bssid", "wifi_station_ssid", "wifi_ap_ssid", "station_ssid",
    "mac_address", "ble_device_address", "serial_number", "ip_address",
    "wifi_station_ip", "wifi_ap_ip", "wifi_gateway_ip", "wifi_dns_ip",
}


def _sanitized(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if str(key).lower() in SENSITIVE_KEYS else _sanitized(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitized(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitized(item) for item in value]
    return value


def _sanitized_json(payload: str) -> tuple[str, bool]:
    """Return canonical redacted JSON and whether redaction changed the data."""
    try:
        decoded = json.loads(payload)
    except (TypeError, ValueError):
        return payload, False
    sanitized = json.dumps(_sanitized(decoded), sort_keys=True, separators=(",", ":"))
    original = json.dumps(decoded, sort_keys=True, separators=(",", ":"))
    return sanitized, sanitized != original


def _inspection_history_payload(inspection: Any) -> Any:
    """Keep inspection evidence useful without copying imported definition trees."""
    payload = _sanitized(inspection)
    if not isinstance(payload, dict) or not isinstance(payload.get("definitions"), list):
        return payload
    summaries: list[Any] = []
    for definition in payload["definitions"][:64]:
        if not isinstance(definition, dict):
            summaries.append(definition)
            continue
        summary: dict[str, Any] = {}
        for key, value in definition.items():
            encoded_size = len(json.dumps(value, sort_keys=True, separators=(",", ":")))
            if encoded_size <= 4096:
                summary[key] = value
            else:
                summary[key] = {
                    "omitted_from_history": True,
                    "item_count": len(value) if isinstance(value, (dict, list)) else None,
                    "encoded_bytes": encoded_size,
                }
        summaries.append(summary)
    payload["definitions"] = summaries
    return payload


def _inspection_history_json(payload: str) -> tuple[str, bool]:
    try:
        decoded = json.loads(payload)
    except (TypeError, ValueError):
        return payload, False
    compacted = json.dumps(_inspection_history_payload(decoded), sort_keys=True, separators=(",", ":"))
    original = json.dumps(decoded, sort_keys=True, separators=(",", ":"))
    return compacted, compacted != original


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        migrate_database(path)
        self._engine = create_database_engine(path)
        history_changed = self._scrub_sensitive_history()
        if history_changed:
            with self._engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
                connection.exec_driver_sql("VACUUM")

    def _scrub_sensitive_history(self) -> bool:
        """Redact rows created before the current privacy policy was installed."""
        changed_any = False
        with Session(self._engine) as session, session.begin():
            for row in session.scalars(select(InspectionSnapshot)).all():
                payload, changed = _inspection_history_json(row.inspection_json)
                if changed:
                    changed_any = True
                    row.inspection_json = payload
                    row.fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            for row in session.scalars(select(TestResultRecord)).all():
                payload, changed = _sanitized_json(row.result_json)
                if changed:
                    changed_any = True
                    row.result_json = payload
        return changed_any

    def get_setting(self, key: str) -> str | None:
        with Session(self._engine) as session:
            row = session.get(Setting, key)
            return row.value if row else None

    def set_setting(self, key: str, value: str) -> None:
        with Session(self._engine) as session, session.begin():
            row = session.get(Setting, key)
            if row:
                row.value = value
            else:
                session.add(Setting(key=key, value=value))

    def remember_profile(self, profile: dict[str, Any], status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        port = str(profile["device"])
        with Session(self._engine) as session, session.begin():
            row = session.get(ConnectionProfile, port)
            values = {
                "description": str(profile["description"]),
                "manufacturer": profile.get("manufacturer"),
                "serial_number": profile.get("serial_number"),
                "vid": profile.get("vid"),
                "pid": profile.get("pid"),
                "is_esp32": int(bool(profile["is_esp32"])),
                "status": status,
                "last_connected_at": now,
            }
            if row:
                for key, value in values.items():
                    setattr(row, key, value)
            else:
                session.add(ConnectionProfile(port=port, **values))
        self.set_setting("selected_port", port)

    def profiles(self) -> list[dict[str, Any]]:
        with Session(self._engine) as session:
            rows = session.scalars(select(ConnectionProfile).order_by(ConnectionProfile.last_connected_at.desc())).all()
            return [
                {
                    "port": row.port,
                    "description": row.description,
                    "manufacturer": row.manufacturer,
                    "serial_number": row.serial_number,
                    "vid": row.vid,
                    "pid": row.pid,
                    "is_esp32": bool(row.is_esp32),
                    "status": row.status,
                    "last_connected_at": row.last_connected_at,
                }
                for row in rows
            ]

    def remember_wireless_profile(self, kind: str, identifier: str, name: str, metadata: dict[str, Any], status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(metadata)
        with Session(self._engine) as session, session.begin():
            row = session.get(WirelessProfile, (kind, identifier))
            if row:
                row.name = name
                row.metadata_json = serialized
                row.status = status
                row.last_connected_at = now
            else:
                session.add(WirelessProfile(kind=kind, identifier=identifier, name=name, metadata_json=serialized, status=status, last_connected_at=now))

    def wireless_profiles(self) -> list[dict[str, Any]]:
        with Session(self._engine) as session:
            rows = session.scalars(select(WirelessProfile).order_by(WirelessProfile.last_connected_at.desc())).all()
            return [
                {
                    "kind": row.kind,
                    "identifier": row.identifier,
                    "name": row.name,
                    "metadata": json.loads(row.metadata_json),
                    "status": row.status,
                    "last_connected_at": row.last_connected_at,
                }
                for row in rows
            ]

    def record_operation(self, plan_id: str, identifier: str, operation_id: str, risk: str, status: str, preview: str, output: str) -> None:
        with Session(self._engine) as session, session.begin():
            session.add(OperationAudit(plan_id=plan_id, identifier=identifier, operation_id=operation_id, risk=risk, status=status, preview=preview, output=output[-64_000:], recorded_at=datetime.now(timezone.utc).isoformat()))

    def operation_history(self, identifier: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        statement = select(OperationAudit)
        if identifier:
            statement = statement.where(OperationAudit.identifier == identifier)
        statement = statement.order_by(OperationAudit.sequence.desc()).limit(max(1, min(limit, 500)))
        with Session(self._engine) as session:
            rows = session.scalars(statement).all()
            return [
                {"sequence": row.sequence, "plan_id": row.plan_id, "identifier": row.identifier, "operation_id": row.operation_id, "risk": row.risk, "status": row.status, "preview": row.preview, "output": row.output, "recorded_at": row.recorded_at}
                for row in rows
            ]

    def get_prototype_project(self, identifier: str) -> dict[str, Any] | None:
        with Session(self._engine) as session:
            row = session.get(PrototypeProjectRecord, identifier)
            if not row:
                return None
            project = json.loads(row.project_json)
            project["updated_at"] = row.updated_at
            return project

    def save_prototype_project(self, identifier: str, project: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(project)
        payload["identifier"] = identifier
        payload["updated_at"] = now
        with Session(self._engine) as session, session.begin():
            row = session.get(PrototypeProjectRecord, identifier)
            expected_revision = int(payload.get("revision", 0))
            if row:
                current = json.loads(row.project_json)
                current_revision = int(current.get("revision", 0))
                if expected_revision != current_revision:
                    raise ValueError(
                        f"Prototype changed in another session (expected revision {expected_revision}, current {current_revision})"
                    )
                payload["revision"] = current_revision + 1
            else:
                if expected_revision != 0:
                    raise ValueError("A new prototype must start at revision 0")
                payload["revision"] = 1
            serialized = json.dumps(payload)
            schema_version = str(payload.get("schema_version", "1.0"))
            if row:
                row.schema_version = schema_version
                row.project_json = serialized
                row.updated_at = now
            else:
                session.add(PrototypeProjectRecord(identifier=identifier, schema_version=schema_version, project_json=serialized, updated_at=now))
        return payload

    def _history_limit(self) -> int:
        configured = self.get_setting("history_retention_per_device")
        try:
            return max(1, min(int(configured or "100"), 1000))
        except ValueError:
            return 100

    def history_retention(self) -> int:
        return self._history_limit()

    def set_history_retention(self, limit: int) -> int:
        bounded = max(1, min(int(limit), 1000))
        self.set_setting("history_retention_per_device", str(bounded))
        return bounded

    def record_inspection(self, identifier: str, inspection: dict[str, Any]) -> dict[str, Any]:
        payload = _inspection_history_payload(inspection)
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        limit = self._history_limit()
        with Session(self._engine) as session, session.begin():
            latest = session.scalars(
                select(InspectionSnapshot)
                .where(InspectionSnapshot.identifier == identifier)
                .order_by(InspectionSnapshot.sequence.desc())
                .limit(1)
            ).first()
            if latest and latest.fingerprint == fingerprint:
                return {"recorded": False, "sequence": latest.sequence, "fingerprint": fingerprint, "recorded_at": latest.recorded_at}
            row = InspectionSnapshot(identifier=identifier, fingerprint=fingerprint, inspection_json=serialized, recorded_at=now)
            session.add(row)
            session.flush()
            stale = session.scalars(
                select(InspectionSnapshot.sequence)
                .where(InspectionSnapshot.identifier == identifier)
                .order_by(InspectionSnapshot.sequence.desc())
                .offset(limit)
            ).all()
            if stale:
                session.execute(delete(InspectionSnapshot).where(InspectionSnapshot.sequence.in_(stale)))
            return {"recorded": True, "sequence": row.sequence, "fingerprint": fingerprint, "recorded_at": now}

    def inspection_history(self, identifier: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        statement = select(InspectionSnapshot)
        if identifier:
            statement = statement.where(InspectionSnapshot.identifier == identifier)
        statement = statement.order_by(InspectionSnapshot.sequence.desc()).limit(max(1, min(limit, 1000)))
        with Session(self._engine) as session:
            return [
                {
                    "sequence": row.sequence,
                    "identifier": row.identifier,
                    "fingerprint": row.fingerprint,
                    "inspection": _inspection_history_payload(json.loads(row.inspection_json)),
                    "recorded_at": row.recorded_at,
                }
                for row in session.scalars(statement).all()
            ]

    def record_test_result(self, identifier: str, test_id: str, result: dict[str, Any]) -> dict[str, Any]:
        payload = _sanitized(result)
        now = datetime.now(timezone.utc).isoformat()
        limit = self._history_limit()
        with Session(self._engine) as session, session.begin():
            row = TestResultRecord(
                identifier=identifier,
                test_id=test_id,
                passed=int(bool(payload.get("passed"))),
                result_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
                recorded_at=now,
            )
            session.add(row)
            session.flush()
            stale = session.scalars(
                select(TestResultRecord.sequence)
                .where(TestResultRecord.identifier == identifier)
                .order_by(TestResultRecord.sequence.desc())
                .offset(limit)
            ).all()
            if stale:
                session.execute(delete(TestResultRecord).where(TestResultRecord.sequence.in_(stale)))
            return {"recorded": True, "sequence": row.sequence, "recorded_at": now}

    def test_history(self, identifier: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        statement = select(TestResultRecord)
        if identifier:
            statement = statement.where(TestResultRecord.identifier == identifier)
        statement = statement.order_by(TestResultRecord.sequence.desc()).limit(max(1, min(limit, 1000)))
        with Session(self._engine) as session:
            return [
                {
                    "sequence": row.sequence,
                    "identifier": row.identifier,
                    "test_id": row.test_id,
                    "passed": bool(row.passed),
                    "result": _sanitized(json.loads(row.result_json)),
                    "recorded_at": row.recorded_at,
                }
                for row in session.scalars(statement).all()
            ]

    def confirm_visual_evidence(self, identifier: str, image_sha256: str, marking: str, role: str, confidence: float, source_text: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with Session(self._engine) as session, session.begin():
            existing = session.scalars(select(VisualEvidenceRecord).where(
                VisualEvidenceRecord.identifier == identifier,
                VisualEvidenceRecord.image_sha256 == image_sha256,
                VisualEvidenceRecord.marking == marking,
                VisualEvidenceRecord.role == role,
            )).first()
            if existing:
                return {"recorded": False, "sequence": existing.sequence, "confirmed_at": existing.confirmed_at}
            row = VisualEvidenceRecord(
                identifier=identifier,
                image_sha256=image_sha256,
                marking=marking,
                role=role,
                confidence_ppm=max(0, min(round(confidence * 1_000_000), 1_000_000)),
                source_text=source_text[:512],
                confirmed_at=now,
            )
            session.add(row)
            session.flush()
            return {"recorded": True, "sequence": row.sequence, "confirmed_at": now}

    def visual_evidence(self, identifier: str) -> list[dict[str, Any]]:
        with Session(self._engine) as session:
            rows = session.scalars(select(VisualEvidenceRecord).where(VisualEvidenceRecord.identifier == identifier).order_by(VisualEvidenceRecord.sequence)).all()
            return [{
                "sequence": row.sequence,
                "image_sha256": row.image_sha256,
                "marking": row.marking,
                "role": row.role,
                "confidence": row.confidence_ppm / 1_000_000,
                "source_text": row.source_text,
                "confirmed_at": row.confirmed_at,
            } for row in rows]

    def export_history(self, identifier: str | None = None) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "identifier": identifier,
            "inspections": self.inspection_history(identifier, 1000),
            "tests": self.test_history(identifier, 1000),
            "operations": self.operation_history(identifier, 500),
        }

    def delete_history(self, identifier: str | None = None) -> dict[str, int]:
        with Session(self._engine) as session, session.begin():
            inspection_statement = delete(InspectionSnapshot)
            test_statement = delete(TestResultRecord)
            operation_statement = delete(OperationAudit)
            if identifier:
                inspection_statement = inspection_statement.where(InspectionSnapshot.identifier == identifier)
                test_statement = test_statement.where(TestResultRecord.identifier == identifier)
                operation_statement = operation_statement.where(OperationAudit.identifier == identifier)
            inspections = session.execute(inspection_statement).rowcount or 0
            tests = session.execute(test_statement).rowcount or 0
            operations = session.execute(operation_statement).rowcount or 0
        return {"inspections": inspections, "tests": tests, "operations": operations}
