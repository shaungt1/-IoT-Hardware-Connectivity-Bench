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
