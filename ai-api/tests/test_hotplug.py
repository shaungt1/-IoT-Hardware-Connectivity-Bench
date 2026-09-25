import asyncio
import threading

from app.hotplug import HostDeviceEvents, filter_present_local_devices


def test_portable_poll_notifies_when_snapshot_changes() -> None:
    snapshots = iter([("serial:A",), ("serial:A",), ("serial:B",)])
    current = [("serial:A",)]

    def snapshot():
        try:
            current[0] = next(snapshots)
        except StopIteration:
            pass
        return current[0]

    source = HostDeviceEvents(snapshot_provider=snapshot, poll_seconds=0.01, platform_name="posix")

    async def scenario():
        source.start()
        await source.wait(reconciliation_seconds=0.5)
        await source.wait(reconciliation_seconds=0.5)
        assert source.snapshot()["event_count"] == 1
        assert source.snapshot()["mode"] == "polling_snapshot"
        source.stop()

    asyncio.run(scenario())
    assert not any(thread.name == "iot-bench-hotplug-poll" and thread.is_alive() for thread in threading.enumerate())


def test_fast_presence_removes_only_reliably_absent_local_interfaces() -> None:
    inventory = [
        {"id": "serial:COM6", "kind": "serial"},
        {"id": "serial:COM12", "kind": "serial"},
        {"id": "usb:303A:1001:1:2", "kind": "usb_identity"},
        {"id": "ssh:lab", "kind": "ssh_target"},
    ]

    filtered = filter_present_local_devices(
        inventory,
        {"serial": {"serial:COM12"}, "usb_identity": None},
    )

    assert [item["id"] for item in filtered] == ["serial:COM12", "usb:303A:1001:1:2", "ssh:lab"]
