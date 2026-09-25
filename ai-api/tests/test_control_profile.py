from app.control_profile import build_control_profile


def test_pin_map_does_not_imply_physical_control() -> None:
    profile = build_control_profile({
        "identifier": "serial:COM6",
        "pins": [{"name": "D0"}],
        "telemetry": {"board_id": "seeed_xiao_esp32s3_sense"},
    }, connected=True)

    assert profile["mapped"] is True
    assert profile["control_ready"] is False
    assert all(item["available"] is False for item in profile["capabilities"])
    assert profile["safety"]["prototype_wire_implies_physical_control"] is False


def test_only_runtime_advertised_control_actions_are_enabled() -> None:
    profile = build_control_profile({
        "identifier": "serial:COM6",
        "pins": [{"name": "D0"}],
        "telemetry": {
            "control_protocol": "iot-bench-control/1",
            "control_capabilities": ["gpio_read", "gpio_write"],
        },
    }, connected=True)

    assert profile["control_ready"] is True
    assert {item["id"] for item in profile["capabilities"] if item["available"]} == {"gpio_read", "gpio_write"}
