from types import SimpleNamespace

from app.tool_registry import diagnose_tool, tool_registry
from app.usb_inventory import normalize_usb_device


def test_normalizes_known_lichee_usb_identity() -> None:
    device = SimpleNamespace(
        idVendor=0x359F,
        idProduct=0x2120,
        bus=1,
        address=26,
        bDeviceClass=0xEF,
        manufacturer="Sipeed",
        product="USB download gadget",
        serial_number=None,
    )

    result = normalize_usb_device(device)

    assert result["usb_identity"] == "359F:2120"
    assert result["name"] == "Sipeed LicheeRV Nano"
    assert result["kind"] == "linux-board"
    assert result["development_candidate"] is True
    assert result["inspection"] == "passive"


def test_tool_registry_has_explicit_risk_for_every_tool() -> None:
    result = tool_registry()

    assert result["available_count"] >= 7
    assert all("diagnostic_supported" in item and "documentation_url" in item for item in result["tools"])
    assert {tool["risk"] for tool in result["tools"]} <= set(result["risk_levels"])
    assert all(tool["capability"] in {"active", "planned"} for tool in result["tools"])


def test_ngspice_diagnostic_is_bounded_and_non_mutating() -> None:
    report = diagnose_tool("ngspice")
    if report["available"]:
        assert report["diagnostic_ran"] is True
        assert "ngspice" in report["output"].lower()
    assert report["physical_hardware_changed"] is False
