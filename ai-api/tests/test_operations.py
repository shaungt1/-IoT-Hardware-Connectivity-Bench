from app.operations import OperationManager
from app.storage import StateStore
from app.workspace import DeviceWorkspace


def test_workspace_write_requires_target_bound_approval(tmp_path) -> None:
    firmware = tmp_path / "firmware"
    firmware.mkdir()
    target = firmware / "main.py"
    target.write_bytes(b"old\n")
    store = StateStore(tmp_path / "state.db")
    workspace = DeviceWorkspace(tmp_path)
    manager = OperationManager(tmp_path, store, workspace)
    opened = workspace.read_text("bench-firmware", "main.py")

    profile = {"id": "serial:COM8"}
    fingerprint = manager.fingerprint(profile, {})
    plan = manager.create_write_plan("serial:COM8", "bench-firmware", "main.py", "new\n", opened["sha256"], fingerprint)
    rejected = False
    try:
        manager.execute(plan["plan_id"], "serial:COM8", None, profile, {})
    except ValueError:
        rejected = True
    assert rejected is True

    approval = manager.approve(plan["plan_id"], "serial:COM8")
    result = manager.execute(plan["plan_id"], "serial:COM8", approval["approval_token"], profile, {})
    assert result["passed"] is True
    assert target.read_text(encoding="utf-8") == "new\n"
    assert {item["status"] for item in store.operation_history("serial:COM8")} >= {"planned", "approved", "completed"}


def test_capabilities_never_offer_flash_without_serial_target(tmp_path, monkeypatch) -> None:
    project = tmp_path / "firmware" / "demo"
    project.mkdir(parents=True)
    (project / "platformio.ini").write_text("[platformio]\n", encoding="utf-8")
    store = StateStore(tmp_path / "state.db")
    manager = OperationManager(tmp_path, store, DeviceWorkspace(tmp_path))
    monkeypatch.setattr(manager, "_platformio_available", lambda: True)

    operations = manager.capabilities({"id": "usb:1", "kind": "usb_identity"}, {})
    build = next(item for item in operations if item["id"].startswith("build:"))
    flash = next(item for item in operations if item["id"].startswith("flash:"))

    assert build["available"] is True
    assert flash["available"] is False


def test_flash_requires_project_board_match(tmp_path, monkeypatch) -> None:
    project = tmp_path / "firmware" / "nano"
    project.mkdir(parents=True)
    (project / "platformio.ini").write_text("[env:nano]\nboard = nano33ble\n", encoding="utf-8")
    manager = OperationManager(tmp_path, StateStore(tmp_path / "state.db"), DeviceWorkspace(tmp_path))
    monkeypatch.setattr(manager, "_platformio_available", lambda: True)
    profile = {"id": "serial:COM8", "kind": "serial", "device": "COM8"}

    feather = manager.capabilities(profile, {"model": "Adafruit Feather M0 Express", "mcu": "ATSAMD21G18"})
    nano = manager.capabilities(profile, {"model": "Arduino Nano 33 BLE Sense", "mcu": "Nordic nRF52840"})

    assert next(item for item in feather if item["id"].startswith("flash:"))["available"] is False
    assert next(item for item in nano if item["id"].startswith("flash:"))["available"] is True
