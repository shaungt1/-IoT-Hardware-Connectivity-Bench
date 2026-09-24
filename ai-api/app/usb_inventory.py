from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from typing import Any

import libusb_package
import usb.core


USB_CLASS_NAMES = {
    0x00: "Per-interface",
    0x02: "Communications",
    0x03: "Human interface",
    0x08: "Mass storage",
    0x09: "Hub",
    0x0A: "CDC data",
    0x0E: "Video",
    0xE0: "Wireless controller",
    0xEF: "Composite device",
    0xFE: "Application specific",
    0xFF: "Vendor specific",
}

KNOWN_USB_DEVICES = {
    (0x303A, 0x1001): ("Espressif USB JTAG/serial", "microcontroller"),
    (0x359F, 0x2120): ("Sipeed LicheeRV Nano", "linux-board"),
    (0x10C4, 0xEA60): ("Silicon Labs CP210x USB-to-UART bridge", "usb-uart-bridge"),
    (0x1D50, 0x6018): ("Great Scott Gadgets HackRF One", "software-defined-radio"),
    (0x239A, 0x8023): ("Adafruit Feather M0 Express", "microcontroller"),
    (0x046D, 0x0944): ("Logitech MX Brio", "camera"),
    (0x09E8, 0x0049): ("Akai MPK mini 3", "midi-controller"),
    (0x17E9, 0x4320): ("Insignia USB-to-HDMI adapter", "display-adapter"),
}

PNP_CLASS_PRIORITY = {"Ports": 8, "Camera": 7, "MEDIA": 6, "Display": 5, "USB": 4, "HIDClass": 2}

POWERSHELL_PNP_QUERY = r"""
@(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
  Where-Object { $_.InstanceId -match 'VID_[0-9A-F]{4}&PID_[0-9A-F]{4}' } |
  ForEach-Object {
    if ($_.InstanceId -match 'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})') {
      [pscustomobject]@{
        vendor_id = $Matches[1]
        product_id = $Matches[2]
        class_name = $_.Class
        friendly_name = $_.FriendlyName
        status = [string]$_.Status
        instance_id = $_.InstanceId
      }
    }
  }) | ConvertTo-Json -Compress -Depth 3
"""


def _windows_pnp_inventory() -> dict[tuple[str, str], dict[str, Any]]:
    if platform.system() != "Windows":
        return {}
    powershell = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    try:
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", POWERSHELL_PNP_QUERY],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        )
        payload = json.loads(result.stdout or "[]")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {}
    rows = payload if isinstance(payload, list) else [payload]
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("vendor_id", "")).upper(), str(row.get("product_id", "")).upper())
        current = grouped.get(key)
        if current is None or PNP_CLASS_PRIORITY.get(str(row.get("class_name")), 0) > PNP_CLASS_PRIORITY.get(str(current.get("class_name")), 0):
            grouped[key] = row
    return grouped


def _classification(kind: str, device_class: int, pnp_class: str | None) -> str:
    known = {
        "microcontroller": "microcontroller_board",
        "linux-board": "linux_single_board_computer",
        "usb-uart-bridge": "usb_uart_bridge",
        "software-defined-radio": "software_defined_radio",
        "camera": "camera_peripheral",
        "midi-controller": "midi_controller",
        "display-adapter": "display_adapter",
    }
    if kind in known:
        return known[kind]
    class_name = (pnp_class or "").lower()
    if class_name == "camera" or device_class == 0x0E:
        return "camera_peripheral"
    if class_name == "media":
        return "audio_video_peripheral"
    if class_name in {"keyboard", "mouse", "hidclass"} or device_class == 0x03:
        return "human_interface_device"
    if class_name == "diskdrive" or device_class == 0x08:
        return "storage_device"
    if class_name == "display":
        return "display_adapter"
    if device_class == 0x09:
        return "usb_hub"
    return "usb_peripheral"


def _safe_text(device: Any, attribute: str) -> str | None:
    try:
        value = getattr(device, attribute, None)
        return str(value).strip() if value else None
    except (usb.core.USBError, ValueError, NotImplementedError):
        return None


def normalize_usb_device(device: Any, pnp: dict[tuple[str, str], dict[str, Any]] | None = None) -> dict:
    vendor_id = int(device.idVendor)
    product_id = int(device.idProduct)
    device_class = int(getattr(device, "bDeviceClass", 0))
    known_name, kind = KNOWN_USB_DEVICES.get(
        (vendor_id, product_id),
        (None, "host-interface" if device_class == 0x09 else "usb-device"),
    )
    manufacturer = _safe_text(device, "manufacturer")
    product = _safe_text(device, "product")
    pnp_record = (pnp or {}).get((f"{vendor_id:04X}", f"{product_id:04X}"), {})
    pnp_name = str(pnp_record.get("friendly_name") or "").strip() or None
    pnp_class = str(pnp_record.get("class_name") or "").strip() or None
    display_name = known_name or product or pnp_name or manufacturer or "USB device"
    classification = _classification(kind, device_class, pnp_class)
    development_candidate = classification in {"microcontroller_board", "linux_single_board_computer", "usb_uart_bridge", "software_defined_radio"} or device_class in {0x02, 0x0A, 0xFE, 0xFF}
    return {
        "id": f"usb:{vendor_id:04X}:{product_id:04X}:{getattr(device, 'bus', 0)}:{getattr(device, 'address', 0)}",
        "name": display_name,
        "kind": kind,
        "vendor_id": f"{vendor_id:04X}",
        "product_id": f"{product_id:04X}",
        "usb_identity": f"{vendor_id:04X}:{product_id:04X}",
        "bus": int(getattr(device, "bus", 0) or 0),
        "address": int(getattr(device, "address", 0) or 0),
        "device_class": device_class,
        "class_name": USB_CLASS_NAMES.get(device_class, f"Class 0x{device_class:02X}"),
        "pnp_class": pnp_class,
        "classification": classification,
        "manufacturer": manufacturer,
        "product": product,
        "serial_number": _safe_text(device, "serial_number"),
        "development_candidate": development_candidate,
        "inspection": "passive",
        "status": pnp_record.get("status") or "present",
    }


def scan_usb_devices() -> dict:
    errors: list[str] = []
    devices: list[dict] = []
    try:
        pnp = _windows_pnp_inventory()
        found = libusb_package.find(find_all=True)
        devices = [normalize_usb_device(device, pnp) for device in found]
    except (usb.core.USBError, OSError, RuntimeError) as error:
        errors.append(str(error))
    devices.sort(key=lambda item: (not item["development_candidate"], item["name"], item["usb_identity"]))
    return {
        "provider": "PyUSB with libusb-package",
        "inspection": "passive",
        "count": len(devices),
        "candidate_count": sum(1 for item in devices if item["development_candidate"]),
        "devices": devices,
        "errors": errors,
    }
