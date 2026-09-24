from __future__ import annotations

import re
import subprocess
from typing import Any


def _band(channel: int, explicit_band: str = "") -> str:
    normalized = explicit_band.lower().replace(" ", "")
    if "6ghz" in normalized:
        return "6 GHz"
    if "5ghz" in normalized:
        return "5 GHz"
    if "2.4ghz" in normalized:
        return "2.4 GHz"
    return "2.4 GHz" if 1 <= channel <= 14 else "5 GHz"


def parse_netsh_networks(output: str) -> list[dict[str, Any]]:
    networks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    authentication = "Unknown"
    for raw_line in output.splitlines():
        line = raw_line.strip()
        ssid_match = re.match(r"SSID\s+\d+\s*:\s*(.*)", line)
        if ssid_match:
            if current:
                networks.append(current)
            current = {
                "ssid": ssid_match.group(1).strip() or "Hidden network",
                "signal_percent": 0,
                "channel": 0,
                "band": "Unknown",
                "security": "Unknown",
                "source": "Windows host",
            }
            authentication = "Unknown"
            continue
        if current is None:
            continue
        if line.startswith("Authentication"):
            authentication = line.partition(":")[2].strip() or "Unknown"
            current["security"] = authentication
        elif line.startswith("Signal"):
            match = re.search(r"(\d+)%", line)
            if match:
                current["signal_percent"] = max(current["signal_percent"], int(match.group(1)))
        elif line.startswith("Channel"):
            value = line.partition(":")[2].strip()
            if value.isdigit():
                current["channel"] = int(value)
                current["band"] = _band(current["channel"])
        elif line.startswith("Band"):
            value = line.partition(":")[2].strip()
            current["band"] = _band(current["channel"], value)
    if current:
        networks.append(current)

    strongest: dict[tuple[str, str], dict[str, Any]] = {}
    for network in networks:
        key = (network["ssid"], network["band"])
        if key not in strongest or network["signal_percent"] > strongest[key]["signal_percent"]:
            strongest[key] = network
    return sorted(strongest.values(), key=lambda item: item["signal_percent"], reverse=True)


def scan_host_wifi() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {"available": False, "networks": [], "error": str(error)}

    output = f"{completed.stdout}\n{completed.stderr}".strip()
    if completed.returncode != 0 or "no wireless interface" in output.lower():
        return {
            "available": False,
            "networks": [],
            "error": "No Windows Wi-Fi adapter is available for 2.4/5 GHz host scanning",
        }
    return {"available": True, "networks": parse_netsh_networks(output), "error": None}
