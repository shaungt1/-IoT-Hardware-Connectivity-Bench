import pytest

from app.control_operations import ControlError, ControlOperationManager
from app.storage import StateStore


def inspection() -> dict:
    return {
        "identifier": "serial:COM6",
        "pins": [
            {"name": "D0", "functions": ["GPIO", "ADC1_CH0"]},
            {"name": "GND", "functions": ["Ground"]},
        ],
        "telemetry": {
            "board_id": "seeed_xiao_esp32s3_sense",
            "pin_map_version": "v1",
            "control_protocol": "iot-bench-control/1",
            "control_capabilities": ["gpio_read", "gpio_write", "adc_read"],
        },
    }


def test_control_write_requires_bound_approval_and_records_receipt(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")
    manager = ControlOperationManager(store)
    plan = manager.create_plan("serial:COM6", "gpio_write", "D0", 1, inspection(), True)

    with pytest.raises(ControlError, match="approval token"):
        manager.prepare(plan["plan_id"], "serial:COM6", None, inspection())
    approval = manager.approve(plan["plan_id"], "serial:COM6")
    prepared = manager.prepare(plan["plan_id"], "serial:COM6", approval["approval_token"], inspection())
    result = manager.finish(prepared, True, "GPIO WRITE D0 returned 1")

    assert prepared.command == "GPIO WRITE\tD0\t1"
    assert result["passed"] is True
    assert {item["status"] for item in store.operation_history("serial:COM6")} >= {"planned", "approved", "completed"}


def test_control_rejects_power_unknown_and_unnegotiated_pins(tmp_path) -> None:
    manager = ControlOperationManager(StateStore(tmp_path / "state.db"))
    with pytest.raises(ControlError, match="Power and ground"):
        manager.create_plan("serial:COM6", "gpio_write", "GND", 1, inspection(), True)
    with pytest.raises(ControlError, match="not in the verified"):
        manager.create_plan("serial:COM6", "gpio_write", "D7", 1, inspection(), True)
    unavailable = inspection()
    unavailable["telemetry"].pop("control_protocol")
    with pytest.raises(ControlError, match="not negotiated"):
        manager.create_plan("serial:COM6", "gpio_write", "D0", 1, unavailable, True)


def test_target_change_invalidates_control_approval(tmp_path) -> None:
    manager = ControlOperationManager(StateStore(tmp_path / "state.db"))
    plan = manager.create_plan("serial:COM6", "gpio_read", "D0", None, inspection(), True)
    approval = manager.approve(plan["plan_id"], "serial:COM6")
    changed = inspection()
    changed["telemetry"]["pin_map_version"] = "v2"

    with pytest.raises(ControlError, match="changed"):
        manager.prepare(plan["plan_id"], "serial:COM6", approval["approval_token"], changed)
