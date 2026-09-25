from app.device_state import DeviceStateManager


def device(identifier: str, name: str = "Device") -> dict:
    return {"id": identifier, "kind": "serial", "name": name, "device": identifier.split(":")[-1]}


def test_state_manager_emits_connect_disconnect_and_keeps_present_inventory() -> None:
    manager = DeviceStateManager()

    assert manager.update([device("serial:COM6")]) is True
    first = manager.snapshot()
    assert first["revision"] == 1
    assert first["events"][-1]["action"] == "connected"

    assert manager.update([device("serial:COM6")]) is False
    assert manager.snapshot()["revision"] == 1
    assert manager.last_delta() == {"added": [], "removed": [], "changed": []}

    assert manager.update([device("serial:COM12", "Feather")]) is True
    final = manager.snapshot()
    assert [item["id"] for item in final["hardware"]] == ["serial:COM12"]
    assert [(event["action"], event["identifier"]) for event in final["events"][-2:]] == [
        ("connected", "serial:COM12"),
        ("disconnected", "serial:COM6"),
    ]
    assert manager.last_delta() == {
        "added": ["serial:COM12"],
        "removed": ["serial:COM6"],
        "changed": [],
    }
