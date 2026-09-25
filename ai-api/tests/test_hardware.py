import json

import pytest

from app.hardware import _device_ip, inspect_usb_network_device, parse_usb_network_adapters, run_usb_network_diagnostic


def test_device_ip_uses_board_address_on_usb_subnet() -> None:
    assert _device_ip("10.6.156.100") == "10.6.156.1"
    assert _device_ip("invalid") is None


def test_usb_network_discovery_identifies_lichee_and_prefers_ncm() -> None:
    parent = r"USB\VID_359F&PID_2120\DD9E1EA31519C768"
    payload = json.dumps(
        [
            {
                "name": "Ethernet 7",
                "description": "Remote NDIS based Internet Sharing Device",
                "status": "Up",
                "mac_address": "00-11-22-33-44-55",
                "pnp_device_id": parent + "&MI_00",
                "parent_id": parent,
                "host_ips": ["10.6.157.100"],
            },
            {
                "name": "Ethernet 8",
                "description": "UsbNcm Host Device",
                "status": "Up",
                "mac_address": "00-11-22-33-44-66",
                "pnp_device_id": parent + "&MI_02",
                "parent_id": parent,
                "host_ips": ["10.6.156.100"],
            },
        ]
    )

    devices = parse_usb_network_adapters(payload)

    assert len(devices) == 1
    assert devices[0]["name"] == "LicheeRV Nano + PicoClaw"
    assert devices[0]["interface"] == "Ethernet 8"
    assert devices[0]["ip_address"] == "10.6.156.1"
    assert devices[0]["web_url"] == "http://10.6.156.1:18800"


def test_usb_network_inspection_never_assumes_ssh_credentials(monkeypatch) -> None:
    profile = {
        "id": "usb-network:test",
        "kind": "usb_network",
        "ip_address": "10.6.156.1",
        "web_url": None,
        "is_lichee": True,
    }
    monkeypatch.setattr("app.hardware.discover_usb_network_devices", lambda cache_seconds=0: [profile])
    monkeypatch.setattr("app.hardware._tcp_open", lambda host, port: True)

    result = inspect_usb_network_device(profile["id"])

    assert result["telemetry"]["ssh_authenticated"] is False
    assert result["telemetry"]["enrollment_required"] is True
    with pytest.raises(ValueError, match="verified SSH host-key"):
        run_usb_network_diagnostic(profile["id"], "system_summary")
