import sys
import threading
import time

from app.operations import OperationManager, OperationPlan
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


def test_disconnect_invalidates_plan_and_cancels_active_process(tmp_path, monkeypatch) -> None:
    manager = OperationManager(tmp_path, StateStore(tmp_path / "state.db"), DeviceWorkspace(tmp_path))
    profile = {"id": "serial:COM8", "kind": "serial", "device": "COM8"}
    plan = OperationPlan(
        id="long-operation",
        identifier=profile["id"],
        operation_id="test:long",
        label="Long operation",
        risk="read-only",
        description="Test operation",
        preview="Wait for cancellation",
        created_at=time.time(),
        parameters={},
        fingerprint=manager.fingerprint(profile, {}),
    )
    manager._plans[plan.id] = plan
    monkeypatch.setattr(manager, "_command", lambda *_: [sys.executable, "-u", "-c", "import time; print('build started', flush=True); time.sleep(30)"])
    result = {}

    def execute():
        result.update(manager.execute(plan.id, profile["id"], None, profile, {}))

    thread = threading.Thread(target=execute)
    thread.start()
    deadline = time.time() + 3
    while not manager.snapshot()["active_identifiers"] and time.time() < deadline:
        time.sleep(0.01)

    cancelled = manager.cancel_identifier(profile["id"])
    thread.join(timeout=3)

    assert cancelled["process_terminated"] is True
    assert thread.is_alive() is False
    assert result["status"] == "cancelled"
    assert result["passed"] is False
    assert profile["id"] in manager.snapshot()["disconnected_identifiers"]
    manager.mark_present(profile["id"])
    assert profile["id"] not in manager.snapshot()["disconnected_identifiers"]


def test_operator_cancel_terminates_process_without_marking_target_disconnected(tmp_path, monkeypatch) -> None:
    manager = OperationManager(tmp_path, StateStore(tmp_path / "state.db"), DeviceWorkspace(tmp_path))
    profile = {"id": "serial:COM8", "kind": "serial", "device": "COM8"}
    plan = OperationPlan(
        id="operator-cancel",
        identifier=profile["id"],
        operation_id="test:long",
        label="Long operation",
        risk="read-only",
        description="Test operation",
        preview="Wait for operator cancellation",
        created_at=time.time(),
        parameters={},
        fingerprint=manager.fingerprint(profile, {}),
    )
    manager._plans[plan.id] = plan
    monkeypatch.setattr(manager, "_command", lambda *_: [sys.executable, "-c", "import time; time.sleep(30)"])
    result = {}

    thread = threading.Thread(target=lambda: result.update(manager.execute(plan.id, profile["id"], None, profile, {})))
    thread.start()
    deadline = time.time() + 3
    while not manager.snapshot()["active_identifiers"] and time.time() < deadline:
        time.sleep(0.01)

    while "build started" not in manager.snapshot()["active"][0]["output"] and time.time() < deadline:
        time.sleep(0.01)

    cancelled = manager.cancel_active(profile["id"])
    thread.join(timeout=3)

    assert cancelled == {"identifier": profile["id"], "plans_cancelled": 1, "process_terminated": True}
    assert thread.is_alive() is False
    assert result["status"] == "cancelled"
    assert profile["id"] not in manager.snapshot()["disconnected_identifiers"]
    assert manager.snapshot()["active"] == []
