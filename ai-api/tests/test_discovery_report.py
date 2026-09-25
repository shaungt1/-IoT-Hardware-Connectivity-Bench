from app.discovery_report import build_discovery_report


def test_discovery_report_traces_layers_and_keeps_unknowns_visible() -> None:
    inspection = {
        "identifier": "serial:COM9",
        "model": "Fixture board",
        "mcu": "ACM32",
        "runtime": "fixture-1.0",
        "adapter": {"id": "fixture", "name": "Fixture adapter"},
        "identity_layers": [
            {"layer": "USB bridge", "name": "CP2102", "status": "verified", "source": "USB descriptor"},
            {"layer": "Board", "name": "Fixture board", "status": "verified", "source": "runtime handshake"},
        ],
        "components": [
            {"id": "mcu", "name": "ACM32", "type": "processor", "status": "verified", "source": "runtime handshake"},
            {"id": "imu", "name": "IMU", "type": "sensor", "status": "detected", "source": "I2C scan"},
        ],
        "capabilities": [{"id": "i2c", "name": "I2C", "status": "verified", "source": "runtime handshake"}],
        "pins": [{"name": "SDA", "status": "verified", "source": "runtime handshake"}],
        "connection_interfaces": [{"id": "i2c", "name": "I2C", "status": "verified", "adapter": "I2C0"}],
        "attached_peripherals": [],
        "definitions": [],
        "services": [],
        "telemetry": {"firmware": "fixture-1.0"},
        "evidence_graph": {"nodes": [{}, {}], "edges": [{}]},
    }
    report = build_discovery_report(
        {"kind": "serial", "transport": "USB serial", "vid": "10C4"},
        inspection,
        {"adapter_attempts": [{"adapter_id": "fixture", "name": "Fixture", "status": "completed"}]},
        {"available_count": 2, "instrument_required_count": 2},
    )

    coverage = {item["id"]: item for item in report["coverage"]}
    assert coverage["bridge"]["status"] == "verified"
    assert coverage["processor"]["count"] == 1
    assert coverage["sensors"]["count"] == 1
    assert coverage["pins"]["count"] == 1
    assert coverage["attachments"]["status"] == "unknown"
    assert any(item["id"] == "attachments" for item in report["unresolved"])
    assert report["graph"] == {"nodes": 2, "edges": 1}
    assert report["safety"]["automatic_brute_force"] is False


def test_discovery_report_records_adapter_failure_without_losing_host_identity() -> None:
    report = build_discovery_report(
        {"kind": "serial", "transport": "USB serial", "vid": "10C4"},
        {
            "identifier": "serial:COM9",
            "model": "Silicon Labs CP210x USB-to-UART bridge",
            "components": [],
            "capabilities": [],
            "pins": [],
            "connection_interfaces": [],
            "attached_peripherals": [],
            "definitions": [],
            "identity_layers": [],
            "services": [],
            "telemetry": {},
            "evidence_graph": {"nodes": [{}], "edges": []},
        },
        {"adapter_attempts": [{"adapter_id": "rom", "name": "ROM", "status": "failed"}]},
        {"available_count": 0, "instrument_required_count": 3},
    )

    phases = {item["id"]: item for item in report["phases"]}
    assert phases["host"]["status"] == "verified"
    assert phases["adapter"]["status"] == "unavailable"
    assert report["coverage"][0]["status"] == "verified"
