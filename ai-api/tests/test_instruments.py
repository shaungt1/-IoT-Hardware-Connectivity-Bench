from app.instruments import build_instrument_report


def test_instrument_report_separates_tools_fixtures_and_target_wiring() -> None:
    report = build_instrument_report(
        {"tools": [
            {"id": "pyocd", "available": True},
            {"id": "openocd", "available": True},
            {"id": "sigrok-cli", "available": True},
        ]},
        [{"unique_id": "ABC", "description": "CMSIS-DAP", "vendor": "Arm", "product": "DAPLink"}],
        ["fx2lafw:conn=1.2 - Saleae clone"],
    )
    assert report["connected_count"] == 2
    assert all(item["status"] == "connected" for item in report["fixtures"])
    assert all(item["target_wiring_confirmed"] is False for item in report["fixtures"])
    assert report["safety"]["signals_driven"] is False


def test_instrument_report_does_not_invent_connected_hardware() -> None:
    report = build_instrument_report(
        {"tools": [{"id": "pyocd", "available": True}, {"id": "sigrok-cli", "available": False}]},
        [],
        [],
    )
    by_id = {item["id"]: item for item in report["fixtures"]}
    assert by_id["debug-probes"]["status"] == "tool_ready"
    assert by_id["logic-analyzers"]["status"] == "unavailable"
    assert report["connected_count"] == 0
