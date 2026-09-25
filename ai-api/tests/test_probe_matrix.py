from app.probe_matrix import build_probe_matrix


def test_probe_matrix_exposes_every_interface_without_driving_unknown_pins() -> None:
    report = build_probe_matrix({
        "identifier": "serial:COM6", "adapter": {"id": "sensor-diagnostic", "name": "Bench firmware"}, "pins": [{"name": "D4"}],
        "tests": [{"id": "probe", "action": "deep_probe", "available": True, "risk": "disruptive", "description": "Probe runtime"}, {"id": "i2c", "action": "bus_scan", "available": True, "risk": "disruptive", "description": "Scan bus"}],
        "telemetry": {"control_protocol": "iot-bench-control/1", "control_capabilities": ["gpio_read", "adc_read"]},
    }, connected=True)
    by_id = {item["id"]: item for item in report["probes"]}
    assert by_id["bus_scan"]["can_run"] is True
    assert by_id["gpio_read"]["status"] == "available"
    assert by_id["spi_transfer"]["status"] == "locked"
    assert by_id["logic_capture"]["status"] == "instrument_required"
    assert report["safety"]["unknown_pins_driven"] is False
    assert report["safety"]["automatic_brute_force"] is False


def test_probe_matrix_locks_live_paths_when_disconnected() -> None:
    report = build_probe_matrix({"identifier": "serial:COM6", "tests": [], "telemetry": {}}, connected=False)
    assert report["available_count"] == 0
    assert all(item["status"] != "available" for item in report["probes"])
