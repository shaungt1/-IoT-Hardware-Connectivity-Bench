from __future__ import annotations

import json
import subprocess
from typing import Any

from .base import AdapterManifest
from ..tool_paths import tool_executable


DEBUG_USB_IDS = {
    ("0D28", "0204"): "Arm DAPLink / CMSIS-DAP",
    ("0483", "3748"): "STMicroelectronics ST-LINK/V2",
    ("0483", "374B"): "STMicroelectronics ST-LINK/V2.1",
    ("0483", "374F"): "STMicroelectronics ST-LINK/V3",
    ("1366", "0101"): "SEGGER J-Link",
    ("1366", "0105"): "SEGGER J-Link",
    ("2E8A", "000C"): "Raspberry Pi Debug Probe / Picoprobe",
}
NAME_HINTS = ("cmsis-dap", "daplink", "st-link", "stlink", "j-link", "picoprobe", "debug probe")


def _pyocd_path() -> str | None:
    return tool_executable("pyocd")


def _probe_inventory() -> dict[str, Any]:
    executable = _pyocd_path()
    if not executable:
        raise ValueError("pyOCD is not installed in the bench environment")
    try:
        result = subprocess.run(
            [executable, "json", "--probes", "--no-config"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"pyOCD probe inventory could not complete: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise ValueError(f"pyOCD probe inventory failed: {detail[-1] if detail else 'unknown error'}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("pyOCD returned malformed probe inventory JSON") from error
    return {"ready": True, "pyocd_version": payload.get("pyocd_version"), "probes": payload.get("boards", [])}


class DebugProbeAdapter:
    adapter_id = "arm_debug_probe"
    name = "CMSIS-DAP, ST-LINK, J-Link and Picoprobe adapter"
    manifest = AdapterManifest(
        id=adapter_id,
        name=name,
        version="1.0",
        transports=("CMSIS-DAP", "SWD", "JTAG"),
        families=("Arm Cortex-M", "DAPLink", "ST-LINK", "J-Link", "Picoprobe"),
        inspection_modes=("passive", "read-only", "disruptive"),
        timeout_seconds=10,
        safety="Probe enumeration is passive. Target attach, halt, memory access, reset, and flash are separate protected operations and are never performed by inventory.",
    )

    def supports(self, profile: dict[str, Any]) -> bool:
        identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
        name = f"{profile.get('name', '')} {profile.get('description', '')}".lower()
        return identity in DEBUG_USB_IDS or any(hint in name for hint in NAME_HINTS)

    def inspect_passive(self, profile: dict[str, Any]) -> dict[str, Any]:
        identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
        probe_name = DEBUG_USB_IDS.get(identity) or profile.get("name") or "Hardware debug probe"
        usb_identity = f"{identity[0] or '----'}:{identity[1] or '----'}"
        return {
            "adapter": {"id": self.adapter_id, "name": self.name, "mode": "passive probe inventory"},
            "identity": {
                "model": probe_name,
                "family": "Arm hardware debug probe",
                "classification": "debug_probe",
                "manufacturer": profile.get("manufacturer"),
                "mcu": None,
                "architecture": None,
                "runtime": "Probe firmware; target not attached",
                "confidence": 0.98 if identity in DEBUG_USB_IDS else 0.85,
                "candidates": [],
                "capabilities": [
                    {"id": "swd", "name": "Serial Wire Debug", "status": "expected", "source": "Debug probe identity"},
                    {"id": "jtag", "name": "JTAG debug", "status": "expected", "source": "Debug probe identity; exact probe capability varies"},
                ],
                "components": [{"id": "debug_probe", "name": probe_name, "type": "debug adapter", "status": "verified", "source": f"USB identity {usb_identity}"}],
                "resources": [{"title": "pyOCD probe support", "url": "https://pyocd.io/docs/debug_probes.html", "provider": "pyOCD", "kind": "tool documentation"}],
            },
            "identity_layers": [
                {"id": "debug_interface", "layer": "Host interface", "name": probe_name, "status": "verified", "source": f"USB {usb_identity}"},
                {"id": "target", "layer": "Target processor", "name": "Not attached or not identified", "status": "unavailable", "source": "A protected target session is required"},
            ],
            "telemetry": {"pyocd_available": bool(_pyocd_path())},
            "evidence": [{"source": "USB descriptor", "claim": f"Debug probe interface {usb_identity}", "status": "verified"}],
            "tests": [{"id": "debug_probe_inventory", "name": "Enumerate attached debug probes", "risk": "passive", "available": bool(_pyocd_path()), "description": "Uses pyOCD to enumerate probe identities without attaching to, halting, resetting, or reading a target."}],
            "pins": [],
            "attached_peripherals": [],
        }

    def run_test(self, profile: dict[str, Any], test_id: str) -> dict[str, Any] | None:
        if test_id != "debug_probe_inventory":
            return None
        result = _probe_inventory()
        return {"passed": True, "summary": f"pyOCD enumerated {len(result['probes'])} attached debug probe(s) without opening a target session.", "evidence": result}
