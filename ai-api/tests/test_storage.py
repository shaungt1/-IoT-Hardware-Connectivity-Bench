from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import InspectionSnapshot, TestResultRecord as StoredTestResult
from app.storage import StateStore


def test_store_persists_selected_connection_profile(tmp_path) -> None:
    store = StateStore(tmp_path / "iot.db")
    profile = {
        "device": "COM6",
        "description": "USB Serial Device (COM6)",
        "manufacturer": "Espressif",
        "serial_number": "test-device",
        "vid": "303A",
        "pid": "1001",
        "is_esp32": True,
    }

    store.remember_profile(profile, "connected")

    assert store.get_setting("selected_port") == "COM6"
    saved = store.profiles()[0]
    assert saved["port"] == "COM6"
    assert saved["is_esp32"] is True
    assert saved["status"] == "connected"


def test_store_persists_wireless_profile_without_password(tmp_path) -> None:
    store = StateStore(tmp_path / "iot.db")

    store.remember_wireless_profile(
        "wifi",
        "Test Network",
        "Test Network",
        {"ip": "192.168.1.20"},
        "connected",
    )

    saved = store.wireless_profiles()[0]
    assert saved["identifier"] == "Test Network"
    assert saved["metadata"] == {"ip": "192.168.1.20"}
    assert "password" not in saved["metadata"]


def test_store_records_operation_receipts(tmp_path) -> None:
    store = StateStore(tmp_path / "iot.db")
    store.record_operation("plan-1", "serial:COM8", "build:firmware", "read-only", "completed", "Build", "Success")

    event = store.operation_history("serial:COM8")[0]
    assert event["plan_id"] == "plan-1"
    assert event["status"] == "completed"
    assert event["output"] == "Success"


def test_inspection_history_deduplicates_redacts_and_honors_retention(tmp_path) -> None:
    store = StateStore(tmp_path / "iot.db")
    store.set_history_retention(2)
    first = store.record_inspection("serial:COM6", {"model": "board-a", "password": "do-not-store"})
    duplicate = store.record_inspection("serial:COM6", {"model": "board-a", "password": "do-not-store"})
    store.record_inspection("serial:COM6", {"model": "board-b", "nested": {"token": "private", "wifi_station_ssid": "Private Network", "ble_device_address": "AA:BB:CC:DD:EE:FF"}})
    store.record_inspection("serial:COM6", {"model": "board-c"})
    history = store.inspection_history("serial:COM6")
    assert first["recorded"] is True
    assert duplicate["recorded"] is False
    assert [item["inspection"]["model"] for item in history] == ["board-c", "board-b"]
    assert history[-1]["inspection"]["nested"]["token"] == "[redacted]"
    assert history[-1]["inspection"]["nested"]["wifi_station_ssid"] == "[redacted]"
    assert history[-1]["inspection"]["nested"]["ble_device_address"] == "[redacted]"


def test_test_history_exports_and_deletes_by_device(tmp_path) -> None:
    store = StateStore(tmp_path / "iot.db")
    store.record_test_result("serial:COM6", "presence", {"passed": True, "secret": "hidden"})
    store.record_test_result("serial:COM7", "presence", {"passed": False})
    exported = store.export_history("serial:COM6")
    assert exported["tests"][0]["result"]["secret"] == "[redacted]"
    removed = store.delete_history("serial:COM6")
    assert removed == {"inspections": 0, "tests": 1, "operations": 0}
    assert store.test_history("serial:COM6") == []
    assert len(store.test_history("serial:COM7")) == 1


def test_visual_evidence_persists_only_normalized_confirmation(tmp_path) -> None:
    store = StateStore(tmp_path / "iot.db")
    receipt = store.confirm_visual_evidence("serial:COM6", "a" * 64, "CP2102", "usb_uart_bridge", 0.97, "SILABS CP2102")
    duplicate = store.confirm_visual_evidence("serial:COM6", "a" * 64, "CP2102", "usb_uart_bridge", 0.97, "SILABS CP2102")
    assert receipt["recorded"] is True
    assert duplicate["recorded"] is False
    assert store.visual_evidence("serial:COM6") == [{
        "sequence": receipt["sequence"],
        "image_sha256": "a" * 64,
        "marking": "CP2102",
        "role": "usb_uart_bridge",
        "confidence": 0.97,
        "source_text": "SILABS CP2102",
        "confirmed_at": receipt["confirmed_at"],
    }]


def test_store_scrubs_legacy_sensitive_history_before_read_or_export(tmp_path) -> None:
    database_path = tmp_path / "iot.db"
    store = StateStore(database_path)
    with Session(store._engine) as session, session.begin():
        session.add(InspectionSnapshot(
            identifier="serial:COM6",
            fingerprint="legacy-fingerprint",
            inspection_json='{"model":"board-a","wifi_station_ssid":"Private Network","nested":{"ble_device_address":"AA:BB:CC:DD:EE:FF"},"definitions":[{"format":"cmsis-svd","source_sha256":"abc","peripherals":["' + ('register-data-' * 500) + '"]}]}',
            recorded_at="2026-01-01T00:00:00+00:00",
        ))
        session.add(StoredTestResult(
            identifier="serial:COM6",
            test_id="legacy-test",
            passed=1,
            result_json='{"passed":true,"ip_address":"192.168.1.25","token":"private"}',
            recorded_at="2026-01-01T00:00:00+00:00",
        ))

    reopened = StateStore(database_path)
    exported = reopened.export_history("serial:COM6")
    inspection = exported["inspections"][0]["inspection"]
    result = exported["tests"][0]["result"]
    assert inspection["wifi_station_ssid"] == "[redacted]"
    assert inspection["nested"]["ble_device_address"] == "[redacted]"
    assert inspection["definitions"][0]["source_sha256"] == "abc"
    assert inspection["definitions"][0]["peripherals"]["omitted_from_history"] is True
    assert inspection["definitions"][0]["peripherals"]["item_count"] == 1
    assert result["ip_address"] == "[redacted]"
    assert result["token"] == "[redacted]"

    with Session(reopened._engine) as session:
        stored_inspection = session.scalars(select(InspectionSnapshot)).one()
        stored_result = session.scalars(select(StoredTestResult)).one()
        assert "Private Network" not in stored_inspection.inspection_json
        assert "AA:BB:CC:DD:EE:FF" not in stored_inspection.inspection_json
        assert stored_inspection.fingerprint != "legacy-fingerprint"
        assert "192.168.1.25" not in stored_result.result_json
        assert "private" not in stored_result.result_json
