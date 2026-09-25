from __future__ import annotations

from typing import Any, Iterable


_STATUS_RANK = {
    "verified": 5,
    "detected": 4,
    "declared": 3,
    "expected": 2,
    "unknown": 1,
    "unavailable": 0,
}


def _best_status(items: Iterable[dict[str, Any]], default: str = "unknown") -> str:
    statuses = [str(item.get("status") or default) for item in items]
    return max(statuses, key=lambda value: _STATUS_RANK.get(value, 1), default=default)


def _sources(items: Iterable[dict[str, Any]], fallback: str) -> str:
    values = []
    for item in items:
        source = str(item.get("source") or "").strip()
        if source and source not in values:
            values.append(source)
    return "; ".join(values[:3]) or fallback


def build_discovery_report(
    profile: dict[str, Any],
    inspection: dict[str, Any],
    live: dict[str, Any] | None,
    probe_matrix: dict[str, Any],
) -> dict[str, Any]:
    """Summarize progressive discovery without promoting absent physical evidence."""
    components = list(inspection.get("components") or [])
    capabilities = list(inspection.get("capabilities") or [])
    pins = list(inspection.get("pins") or [])
    buses = list(inspection.get("connection_interfaces") or [])
    attachments = list(inspection.get("attached_peripherals") or [])
    definitions = list(inspection.get("definitions") or [])
    identity_layers = list(inspection.get("identity_layers") or [])
    services = list(inspection.get("services") or [])
    telemetry = dict(inspection.get("telemetry") or {})
    adapter_attempts = list((live or {}).get("adapter_attempts") or [])

    def component_matches(*tokens: str) -> list[dict[str, Any]]:
        wanted = {token.lower() for token in tokens}
        return [
            item
            for item in components
            if str(item.get("type") or "").lower() in wanted
            or any(token in str(item.get("type") or "").lower() for token in wanted)
        ]

    processors = component_matches("processor", "mcu", "soc", "cpu", "microcontroller")
    sensors = component_matches("sensor", "camera", "microphone", "imu")
    memory = component_matches("memory", "storage", "flash", "ram", "psram", "sd")
    radios = component_matches("radio", "wireless", "wifi", "wi-fi", "ble", "bluetooth")
    radio_capabilities = [
        item for item in capabilities
        if str(item.get("id") or "").lower() in {"wifi", "ble", "bluetooth", "radio", "wireless"}
        or any(token in str(item.get("name") or "").lower() for token in ("wi-fi", "wifi", "bluetooth", "radio"))
    ]
    bridge_layers = [item for item in identity_layers if "bridge" in str(item.get("layer") or "").lower()]
    board_layers = [
        item for item in identity_layers
        if any(token in str(item.get("layer") or "").lower() for token in ("board", "target", "module"))
    ]

    def coverage(
        identifier: str,
        label: str,
        items: list[dict[str, Any]],
        *,
        fallback_count: int = 0,
        fallback_status: str = "unknown",
        fallback_source: str = "No compatible evidence source answered",
        detail: str,
    ) -> dict[str, Any]:
        return {
            "id": identifier,
            "label": label,
            "status": _best_status(items, fallback_status) if items else fallback_status,
            "count": len(items) if items else fallback_count,
            "source": _sources(items, fallback_source),
            "detail": detail,
        }

    processor_fallback = 1 if inspection.get("mcu") else 0
    processor_status = "detected" if processor_fallback else "unknown"
    runtime_present = bool(inspection.get("runtime") and str(inspection.get("runtime")).lower() != "unknown")
    coverage_rows = [
        coverage(
            "host_interface", "Host interface", [{"status": "verified", "source": "Host USB/PnP, serial, network, or SSH enumeration"}],
            detail="The transport visible to this computer; it is not automatically the complete board.",
        ),
        coverage(
            "bridge", "USB or serial bridge", bridge_layers,
            fallback_status="detected" if profile.get("kind") == "serial" and profile.get("vid") else "unknown",
            fallback_count=1 if profile.get("kind") == "serial" and profile.get("vid") else 0,
            fallback_source="Host USB identity" if profile.get("kind") == "serial" else "No separate bridge identified",
            detail="A bridge claim remains separate from the processor and board behind it.",
        ),
        coverage(
            "board", "Board or module", board_layers,
            fallback_status="detected" if inspection.get("model") and "unidentified" not in str(inspection.get("model")).lower() else "unknown",
            fallback_count=1 if inspection.get("model") and "unidentified" not in str(inspection.get("model")).lower() else 0,
            fallback_source="Consolidated inspection",
            detail="Exact board identity requires a runtime, ROM/debug response, definition, or user-confirmed evidence.",
        ),
        coverage(
            "processor", "Processor / MCU / SoC", processors,
            fallback_status=processor_status,
            fallback_count=processor_fallback,
            fallback_source="Consolidated target identity" if processor_fallback else "No processor evidence",
            detail=str(inspection.get("mcu") or "No processor has been identified."),
        ),
        coverage("components", "Major onboard components", components, detail="Processors, memories, radios, interfaces, sensors, and other reported board parts."),
        coverage("sensors", "Sensors and cameras", sensors, detail="Only runtime, bus, definition, or confirmed visual evidence can establish these parts."),
        coverage("memory", "Memory and storage", memory, detail="Flash, RAM, PSRAM, removable storage, and storage controllers when exposed."),
        coverage("radios", "Wireless and radio", [*radios, *radio_capabilities], detail="Wi-Fi, BLE, SDR, and other communication hardware or capabilities."),
        coverage("pins", "Exposed pins", pins, detail="Documented or runtime-reported terminals with functions and electrical constraints."),
        coverage("buses", "Buses and connection interfaces", buses, detail="I2C, SPI, UART, GPIO, SDIO, debug, and other exposed routes."),
        coverage("attachments", "Attached peripherals", attachments, detail="Bus responders or operating-system devices observed beyond the main board."),
        coverage(
            "runtime", "Runtime / firmware / OS",
            [{"status": "verified" if telemetry.get("firmware") else "detected", "source": "Live target inspection"}] if runtime_present else [],
            fallback_count=1 if runtime_present else 0,
            fallback_status="detected" if runtime_present else "unknown",
            fallback_source="Consolidated inspection" if runtime_present else "No runtime handshake",
            detail=str(inspection.get("runtime") or "No compatible runtime or operating system answered."),
        ),
        coverage("services", "Target services", services, detail="Authenticated or observed network and local services exposed by the target."),
    ]

    adapter = inspection.get("adapter") or {}
    adapter_failed = bool(adapter_attempts and not adapter and any(item.get("status") == "failed" for item in adapter_attempts))
    phases = [
        {"id": "host", "label": "Discover", "status": "verified", "summary": f"Host enumerated {profile.get('transport') or profile.get('kind') or 'an interface'} without opening unknown circuitry."},
        {"id": "adapter", "label": "Identify", "status": "verified" if adapter else "unavailable" if adapter_failed else "unknown", "summary": f"{adapter.get('name')} matched this target." if adapter else "No compatible passive/runtime adapter produced target identity."},
        {"id": "decompose", "label": "Decompose", "status": "detected" if components or pins else "unknown", "summary": f"Collected {len(components)} component and {len(pins)} pin claims."},
        {"id": "trace", "label": "Trace", "status": "detected" if buses or attachments else "unknown", "summary": f"Mapped {len(buses)} bus/interface and {len(attachments)} attachment claims."},
        {"id": "definitions", "label": "Enrich", "status": "declared" if definitions else "unknown", "summary": f"{len(definitions)} structured definition source(s) are bound." if definitions else "No SVD, DeviceTree, KiCad, or Fritzing definition is bound."},
        {"id": "verify", "label": "Verify", "status": "verified" if probe_matrix.get("available_count") else "expected" if probe_matrix.get("instrument_required_count") else "unknown", "summary": f"{probe_matrix.get('available_count', 0)} probe route(s) are runnable; {probe_matrix.get('instrument_required_count', 0)} require fixtures."},
    ]

    requirements = {
        "processor": ("Use a supported ROM/runtime handshake, SWD/JTAG probe, DeviceTree, or exact board definition.", ["runtime", "rom_protocol", "debug_probe", "definition"]),
        "components": ("Import a schematic/BOM/DeviceTree, use cooperative firmware, or confirm board markings from photographs.", ["definition", "runtime", "visual_confirmation"]),
        "sensors": ("Run a supported I2C/runtime scan or supply a board definition; SPI and passive sensors are not self-enumerating.", ["bus_probe", "runtime", "definition"]),
        "pins": ("Identify the exact board/processor or use a debug/runtime adapter that reports the exposed pin map.", ["board_identity", "runtime", "debug_probe"]),
        "buses": ("Provide a pin map/runtime/DeviceTree or connect a supported logic analyzer without driving unknown pins.", ["pin_map", "runtime", "logic_analyzer"]),
        "attachments": ("Use an enumerable bus, operating-system inventory, or external logic/analog instrumentation.", ["bus_probe", "operating_system", "instrument"]),
        "runtime": ("Use a known serial protocol, ROM loader, debug probe, SSH agent, or cooperative diagnostic firmware.", ["protocol", "debug_probe", "ssh", "approved_firmware"]),
    }
    unresolved = []
    for item in coverage_rows:
        if item["id"] not in requirements or item["count"]:
            continue
        next_step, required = requirements[item["id"]]
        unresolved.append({
            "id": item["id"],
            "label": item["label"],
            "reason": item["detail"],
            "next_step": next_step,
            "required_evidence": required,
        })

    return {
        "schema_version": "1.0",
        "identifier": inspection.get("identifier"),
        "phases": phases,
        "coverage": coverage_rows,
        "unresolved": unresolved,
        "adapter_attempts": adapter_attempts,
        "graph": {
            "nodes": len((inspection.get("evidence_graph") or {}).get("nodes") or []),
            "edges": len((inspection.get("evidence_graph") or {}).get("edges") or []),
        },
        "safety": {
            "unknown_pins_driven": False,
            "blind_serial_bytes_sent": False,
            "automatic_brute_force": False,
            "physical_limit": "USB alone cannot reveal unexposed passives, traces, SPI topology, or arbitrary GPIO attachments.",
        },
    }
