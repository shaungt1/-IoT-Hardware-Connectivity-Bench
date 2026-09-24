from app.serial_diagnostics import _payload, supports_sensor_diagnostics


def test_manifest_parser_accepts_only_protocol_lines() -> None:
    assert _payload('BENCH_READY {"protocol":"iot-bench-sensors/1"}', ("BENCH_READY",)) == {
        "protocol": "iot-bench-sensors/1"
    }
    assert _payload("unrelated boot log", ("BENCH_READY",)) is None


def test_sensor_diagnostics_are_restricted_to_known_nano_usb_identity() -> None:
    assert supports_sensor_diagnostics({"vid": "2341", "pid": "805A"}) is True
    assert supports_sensor_diagnostics({"vid": "10C4", "pid": "EA60"}) is False
