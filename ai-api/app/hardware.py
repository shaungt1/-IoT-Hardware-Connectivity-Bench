from __future__ import annotations

import json
import os
import platform
import re
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from threading import Lock
from typing import Any

import paramiko


LICHEE_USB_ID = ("359F", "2120")
_cache_lock = Lock()
_cached_at = 0.0
_cached_devices: list[dict[str, Any]] = []


POWERSHELL_USB_NETWORK_QUERY = r"""
$items = @(
  Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue |
    Where-Object { $_.Status -eq 'Up' -and $_.PnPDeviceID -like 'USB\VID_*' } |
    ForEach-Object {
      $parent = (Get-PnpDeviceProperty -InstanceId $_.PnPDeviceID -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data
      $ips = @(Get-NetIPAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '169.254.*' } |
        Select-Object -ExpandProperty IPAddress)
      [pscustomobject]@{
        name = $_.Name
        description = $_.InterfaceDescription
        status = [string]$_.Status
        mac_address = $_.MacAddress
        pnp_device_id = $_.PnPDeviceID
        parent_id = $parent
        host_ips = $ips
      }
    }
)
$items | ConvertTo-Json -Compress -Depth 4
"""


def _usb_ids(value: str) -> tuple[str | None, str | None]:
    match = re.search(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", value, re.IGNORECASE)
    return (match.group(1).upper(), match.group(2).upper()) if match else (None, None)


def _device_ip(host_ip: str) -> str | None:
    octets = host_ip.split(".")
    if len(octets) != 4 or any(not part.isdigit() for part in octets):
        return None
    return ".".join([*octets[:3], "1"])


def parse_usb_network_adapters(payload: str) -> list[dict[str, Any]]:
    if not payload.strip():
        return []
    raw = json.loads(payload)
    adapters = raw if isinstance(raw, list) else [raw]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for adapter in adapters:
        parent = str(adapter.get("parent_id") or adapter.get("pnp_device_id") or "")
        grouped.setdefault(parent, []).append(adapter)

    devices: list[dict[str, Any]] = []
    for parent, members in grouped.items():
        vid, pid = _usb_ids(parent)
        preferred = next(
            (item for item in members if "NCM" in str(item.get("description", "")).upper()),
            members[0],
        )
        ordered_members = [preferred, *(item for item in members if item is not preferred)]
        host_ips = [
            str(ip)
            for item in ordered_members
            for ip in (item.get("host_ips") or [])
            if _device_ip(str(ip))
        ]
        if not host_ips:
            continue
        host_ip = host_ips[0]
        target_ip = _device_ip(host_ip)
        serial_number = parent.rsplit("\\", 1)[-1] if "\\" in parent else None
        is_lichee = (vid, pid) == LICHEE_USB_ID
        devices.append(
            {
                "id": f"usb-network:{parent}",
                "kind": "usb_network",
                "device": target_ip,
                "name": "LicheeRV Nano + PicoClaw" if is_lichee else preferred.get("description", "USB network device"),
                "description": preferred.get("description", "USB network adapter"),
                "manufacturer": "Sipeed" if is_lichee else None,
                "serial_number": serial_number,
                "vid": vid,
                "pid": pid,
                "is_esp32": False,
                "is_lichee": is_lichee,
                "transport": "USB network (NCM/RNDIS)",
                "interface": preferred.get("name"),
                "host_ip": host_ip,
                "ip_address": target_ip,
                "mac_address": preferred.get("mac_address"),
                "web_url": f"http://{target_ip}:18800" if is_lichee else None,
            }
        )
    return devices


def discover_usb_network_devices(cache_seconds: float = 5.0) -> list[dict[str, Any]]:
    global _cached_at, _cached_devices
    with _cache_lock:
        now = time.monotonic()
        if now - _cached_at < cache_seconds:
            return [dict(item) for item in _cached_devices]
        if platform.system() != "Windows":
            return []
        try:
            powershell = os.path.join(
                os.environ.get("SystemRoot", r"C:\Windows"),
                "System32",
                "WindowsPowerShell",
                "v1.0",
                "powershell.exe",
            )
            result = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", POWERSHELL_USB_NETWORK_QUERY],
                capture_output=True,
                text=True,
                timeout=8,
                check=True,
            )
            _cached_devices = parse_usb_network_adapters(result.stdout)
            _cached_at = now
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            _cached_devices = []
            _cached_at = now
        return [dict(item) for item in _cached_devices]


def _tcp_open(host: str, port: int, timeout: float = 0.8) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_title(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read(4096).decode("utf-8", "replace")
        match = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else "Web service"
    except (OSError, ValueError):
        return None


def _ssh_command(client: paramiko.SSHClient, command: str) -> str:
    _, stdout, _ = client.exec_command(command, timeout=5)
    return stdout.read().decode("utf-8", "replace").strip().replace("\x00", "")


SAFE_TARGET_COMMANDS = {
    "system_summary": ("System summary", "uname -a; printf '\n'; cat /etc/os-release 2>/dev/null"),
    "network_interfaces": ("Network interfaces", "ip -brief address 2>/dev/null || ifconfig 2>/dev/null"),
    "usb_devices": ("USB devices", "lsusb 2>/dev/null || echo 'lsusb is not installed'"),
    "i2c_adapters": ("I2C adapters", "i2cdetect -l 2>/dev/null || echo 'i2c-tools is not installed'"),
    "media_devices": ("Media devices", "ls -l /dev/video* /dev/media* 2>/dev/null || echo 'No media device nodes'"),
}


def run_usb_network_diagnostic(identifier: str, command_id: str) -> dict[str, Any]:
    device = next((item for item in discover_usb_network_devices(0) if item["id"] == identifier), None)
    if device is None:
        raise ValueError("USB network device is no longer available")
    if command_id not in SAFE_TARGET_COMMANDS:
        raise ValueError("Diagnostic command is not in the read-only allowlist")
    if not device.get("is_lichee"):
        raise ValueError("This target has no compatible authenticated diagnostic adapter")
    label, command = SAFE_TARGET_COMMANDS[command_id]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            str(device["ip_address"]),
            username="root",
            password="root",
            timeout=3,
            banner_timeout=3,
            auth_timeout=3,
        )
        output = _ssh_command(client, command)
        return {
            "command_id": command_id,
            "label": label,
            "target": device["ip_address"],
            "output": output or "Command completed with no output.",
            "risk": "read-only",
        }
    except (OSError, paramiko.SSHException) as error:
        raise ValueError(f"Target diagnostic failed: {error}") from error
    finally:
        client.close()


def _lichee_telemetry(host: str) -> dict[str, Any]:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            host,
            username="root",
            password="root",
            timeout=3,
            banner_timeout=3,
            auth_timeout=3,
        )
        hostname = _ssh_command(client, "hostname")
        kernel = _ssh_command(client, "uname -r")
        os_name = _ssh_command(client, ". /etc/os-release 2>/dev/null; echo ${PRETTY_NAME:-Linux}")
        model = _ssh_command(client, "cat /proc/device-tree/model 2>/dev/null")
        uptime = _ssh_command(client, "cut -d. -f1 /proc/uptime")
        memory = _ssh_command(client, "awk '/MemAvailable:/ {print $2 * 1024}' /proc/meminfo")
        wifi = _ssh_command(client, "ip -brief address show wlan0 2>/dev/null | tr -s ' '")
        i2c_adapters = _ssh_command(client, "i2cdetect -l 2>/dev/null")
        media_devices = _ssh_command(client, "for path in /dev/video* /dev/media*; do [ -e \"$path\" ] && echo \"$path\"; done")
        camera_detected = bool(media_devices)
        return {
            "ssh_authenticated": True,
            "device": "LicheeRV Nano + PicoClaw",
            "hostname": hostname,
            "model": model or "LicheeRV Nano",
            "firmware": os_name,
            "kernel": kernel,
            "uptime_ms": int(uptime or 0) * 1000,
            "free_heap_bytes": int(memory or 0),
            "camera_ready": camera_detected,
            "camera_status": "GC4653 detected" if camera_detected else "GC4653 configured; sensor not detected",
            "wifi_interface": wifi or "wlan0 unavailable",
            "i2c_adapters": i2c_adapters,
            "media_devices": media_devices,
        }
    except (OSError, paramiko.SSHException, ValueError):
        return {"ssh_authenticated": False}
    finally:
        client.close()


def inspect_usb_network_device(identifier: str) -> dict[str, Any]:
    device = next((item for item in discover_usb_network_devices(0) if item["id"] == identifier), None)
    if device is None:
        raise ValueError("USB network device is no longer available")
    host = str(device["ip_address"])
    ssh_open = _tcp_open(host, 22)
    web_title = _http_title(str(device["web_url"])) if device.get("web_url") else None
    telemetry = _lichee_telemetry(host) if device.get("is_lichee") and ssh_open else {}
    return {
        **device,
        "online": ssh_open or bool(web_title),
        "services": {
            "ssh": ssh_open,
            "web": bool(web_title),
            "web_title": web_title,
        },
        "telemetry": telemetry,
    }
