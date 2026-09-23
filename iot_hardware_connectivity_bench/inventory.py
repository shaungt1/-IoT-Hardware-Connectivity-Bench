from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import platform
import socket
from typing import Any

from serial.tools import list_ports

from . import __version__


@dataclass(slots=True)
class DeviceRecord:
    kind: str
    identifier: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "identifier": self.identifier,
            "summary": self.summary,
            "details": self.details,
        }


def _none_if_empty(value: Any) -> Any:
    return value if value not in ("", None, "n/a", "N/A") else None


def host_metadata() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "python_version": platform.python_version(),
    }


def list_serial_devices() -> list[DeviceRecord]:
    devices: list[DeviceRecord] = []
    for port in list_ports.comports():
        description = _none_if_empty(getattr(port, "description", None)) or getattr(port, "name", None) or port.device
        devices.append(
            DeviceRecord(
                kind="serial",
                identifier=port.device,
                summary=description,
                details={
                    "device": port.device,
                    "name": _none_if_empty(getattr(port, "name", None)),
                    "description": _none_if_empty(getattr(port, "description", None)),
                    "hwid": _none_if_empty(getattr(port, "hwid", None)),
                    "vid": getattr(port, "vid", None),
                    "pid": getattr(port, "pid", None),
                    "serial_number": _none_if_empty(getattr(port, "serial_number", None)),
                    "manufacturer": _none_if_empty(getattr(port, "manufacturer", None)),
                    "product": _none_if_empty(getattr(port, "product", None)),
                    "interface": _none_if_empty(getattr(port, "interface", None)),
                    "location": _none_if_empty(getattr(port, "location", None)),
                },
            )
        )
    return devices


def list_video_devices(video_root: Path = Path("/dev")) -> list[DeviceRecord]:
    if not video_root.exists():
        return []

    devices: list[DeviceRecord] = []
    for entry in sorted(video_root.glob("video*")):
        devices.append(
            DeviceRecord(
                kind="camera",
                identifier=str(entry),
                summary=f"Video capture device {entry.name}",
                details={"path": str(entry)},
            )
        )
    return devices


def list_storage_devices(storage_root: Path = Path("/sys/block")) -> list[DeviceRecord]:
    if not storage_root.exists():
        return []

    devices: list[DeviceRecord] = []
    for entry in sorted(storage_root.iterdir()):
        if not entry.is_dir():
            continue
        removable_path = entry / "removable"
        size_path = entry / "size"
        model_path = entry / "device" / "model"
        vendor_path = entry / "device" / "vendor"
        devices.append(
            DeviceRecord(
                kind="storage",
                identifier=entry.name,
                summary=f"Block device {entry.name}",
                details={
                    "name": entry.name,
                    "path": str(entry),
                    "removable": removable_path.read_text().strip() == "1" if removable_path.exists() else None,
                    "size_sectors": size_path.read_text().strip() if size_path.exists() else None,
                    "model": model_path.read_text().strip() if model_path.exists() else None,
                    "vendor": vendor_path.read_text().strip() if vendor_path.exists() else None,
                },
            )
        )
    return devices


def list_network_interfaces(interface_root: Path = Path("/sys/class/net")) -> list[DeviceRecord]:
    if not interface_root.exists():
        return []

    devices: list[DeviceRecord] = []
    for entry in sorted(interface_root.iterdir()):
        if not entry.is_dir():
            continue
        devices.append(
            DeviceRecord(
                kind="network",
                identifier=entry.name,
                summary=f"Network interface {entry.name}",
                details={"name": entry.name, "path": str(entry)},
            )
        )
    return devices


def collect_inventory() -> dict[str, Any]:
    devices = [
        *list_serial_devices(),
        *list_video_devices(),
        *list_storage_devices(),
        *list_network_interfaces(),
    ]
    return {
        "version": __version__,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "host": host_metadata(),
        "device_count": len(devices),
        "devices": [device.to_dict() for device in devices],
    }


def filter_devices(
    inventory: dict[str, Any],
    *,
    kind: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    devices = inventory["devices"]
    if kind:
        devices = [device for device in devices if device["kind"] == kind]
    if query:
        needle = query.lower()
        devices = [
            device
            for device in devices
            if needle in device["identifier"].lower() or needle in device["summary"].lower()
        ]
    return devices
