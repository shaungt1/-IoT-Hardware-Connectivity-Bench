from __future__ import annotations

import subprocess
from typing import Any

from .tool_registry import tool_registry


def build_instrument_report(
    registry: dict[str, Any],
    debug_probes: list[dict[str, str]],
    sigrok_devices: list[str],
) -> dict[str, Any]:
    tools = {item["id"]: item for item in registry.get("tools", [])}
    debug_tools = [tools[item] for item in ("pyocd", "openocd", "probe-rs") if item in tools and tools[item]["available"]]
    sigrok = tools.get("sigrok-cli", {"available": False})
    fixtures = [
        {
            "id": "debug-probes",
            "name": "SWD/JTAG debug probes",
            "kind": "debug_probe",
            "status": "connected" if debug_probes else "tool_ready" if debug_tools else "unavailable",
            "tools": [item["id"] for item in debug_tools],
            "devices": debug_probes,
            "fixture_count": len(debug_probes),
            "target_wiring_confirmed": False,
            "next_step": (
                "Bind SWDIO/TMS, SWCLK/TCK, ground, voltage reference, and target reset before attach."
                if debug_probes
                else "Connect a supported CMSIS-DAP, ST-Link, J-Link, or Picoprobe fixture."
                if debug_tools
                else "Install pyOCD, OpenOCD, or probe-rs."
            ),
        },
        {
            "id": "logic-analyzers",
            "name": "Logic analyzers",
            "kind": "logic_analyzer",
            "status": "connected" if sigrok_devices else "tool_ready" if sigrok.get("available") else "unavailable",
            "tools": ["sigrok-cli"] if sigrok.get("available") else [],
            "devices": [{"description": item} for item in sigrok_devices],
            "fixture_count": len(sigrok_devices),
            "target_wiring_confirmed": False,
            "next_step": "Bind signal channels and a common ground, then choose a decoder and sample rate." if sigrok.get("available") else "Install sigrok-cli or PulseView and connect a supported capture device.",
        },
    ]
    return {
        "schema_version": "1.0",
        "fixtures": fixtures,
        "connected_count": sum(item["fixture_count"] for item in fixtures),
        "safety": {
            "target_opened": False,
            "target_wiring_confirmed": False,
            "signals_driven": False,
            "reason": "Discovery inventories host-side fixtures only; it does not prove wiring or access the target.",
        },
    }


def _debug_probes() -> list[dict[str, str]]:
    try:
        from pyocd.core.helpers import ConnectHelper

        probes = ConnectHelper.get_all_connected_probes(blocking=False)
    except Exception:
        return []
    return [
        {
            "unique_id": str(getattr(probe, "unique_id", "")),
            "description": str(getattr(probe, "description", "CMSIS-DAP probe")),
            "vendor": str(getattr(probe, "vendor_name", "")),
            "product": str(getattr(probe, "product_name", "")),
        }
        for probe in probes
    ]


def _sigrok_devices(path: str | None) -> list[str]:
    if not path:
        return []
    try:
        result = subprocess.run([path, "--scan"], capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    lines = [line.strip() for line in (result.stdout or "").splitlines()]
    return [line for line in lines if line and not line.lower().startswith(("the following", "demo -"))][:64]


def scan_instruments() -> dict[str, Any]:
    registry = tool_registry()
    tools = {item["id"]: item for item in registry["tools"]}
    return build_instrument_report(
        registry,
        _debug_probes(),
        _sigrok_devices(tools.get("sigrok-cli", {}).get("path")),
    )
