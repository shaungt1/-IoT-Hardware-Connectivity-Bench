from __future__ import annotations

import re
from typing import Any

from .evidence_policy import calibrate_claim, inspection_calibration


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return text or "unknown"


def build_evidence_graph(inspection: dict[str, Any]) -> dict[str, Any]:
    """Create a compact, normalized graph without promoting expected evidence."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[str] = set()

    def add_node(node_id: str, kind: str, name: str, status: str, source: str, **attributes: Any) -> str:
        if node_id not in seen_nodes:
            seen_nodes.add(node_id)
            nodes.append({
                "id": node_id,
                "kind": kind,
                "name": name,
                "status": status,
                "provenance": {"source": source},
                "confidence": calibrate_claim(status, source),
                "attributes": attributes,
            })
        return node_id

    def add_edge(source: str, target: str, relation: str, status: str, evidence_source: str) -> None:
        edge_id = f"{source}|{relation}|{target}"
        if source in seen_nodes and target in seen_nodes and edge_id not in seen_edges:
            seen_edges.add(edge_id)
            edges.append({
                "id": edge_id,
                "source": source,
                "target": target,
                "relation": relation,
                "status": status,
                "provenance": {"source": evidence_source},
                "confidence": calibrate_claim(status, evidence_source),
            })

    device_id = add_node(
        "device:selected",
        "device",
        inspection.get("model") or "Unidentified hardware",
        "detected",
        "consolidated inspection",
        classification=inspection.get("classification"),
        reported_confidence=inspection.get("confidence"),
        identifier=inspection.get("identifier"),
    )

    previous_layer = device_id
    for index, layer in enumerate(inspection.get("identity_layers") or []):
        layer_id = add_node(
            f"identity:{_slug(layer.get('id') or index)}",
            "identity_layer",
            layer.get("name") or "Unresolved",
            layer.get("status") or "unknown",
            layer.get("source") or "unspecified",
            layer=layer.get("layer"),
        )
        add_edge(previous_layer, layer_id, "resolves_to", layer.get("status") or "unknown", layer.get("source") or "unspecified")
        previous_layer = layer_id

    mcu = inspection.get("mcu")
    if mcu:
        processor_id = add_node(
            f"processor:{_slug(mcu)}",
            "processor",
            str(mcu),
            "detected",
            "consolidated target identity",
            architecture=inspection.get("architecture"),
            manufacturer=inspection.get("manufacturer"),
        )
        add_edge(device_id, processor_id, "contains", "detected", "consolidated target identity")

    runtime = inspection.get("runtime")
    if runtime and str(runtime).lower() != "unknown":
        runtime_source = "authenticated device inspection" if (inspection.get("telemetry") or {}).get("firmware") else "consolidated inspection"
        runtime_status = "verified" if runtime_source.startswith("authenticated") else "detected"
        runtime_id = add_node(
            f"runtime:{_slug(runtime)}",
            "runtime",
            str(runtime),
            runtime_status,
            runtime_source,
            telemetry=inspection.get("telemetry") or {},
        )
        add_edge(device_id, runtime_id, "runs", runtime_status, runtime_source)

    buses: dict[str, str] = {}
    for interface in inspection.get("connection_interfaces") or []:
        bus_key = str(interface.get("id") or interface.get("name") or "unknown").lower()
        bus_id = add_node(
            f"bus:{_slug(bus_key)}",
            "bus",
            interface.get("name") or bus_key.upper(),
            interface.get("status") or "unknown",
            interface.get("adapter") or "consolidated inspection",
            adapter=interface.get("adapter"),
            limitation=interface.get("limitation"),
        )
        buses[bus_key] = bus_id
        buses[str(interface.get("name") or "").lower()] = bus_id
        add_edge(device_id, bus_id, "exposes_bus", interface.get("status") or "unknown", interface.get("adapter") or "consolidated inspection")

    for component in inspection.get("components") or []:
        node_id = add_node(
            f"component:{_slug(component.get('id') or component.get('name'))}",
            "component",
            component.get("name") or "Unknown component",
            component.get("status") or "unknown",
            component.get("source") or "unspecified",
            component_type=component.get("type"),
            bus=component.get("bus"),
            variant=component.get("variant"),
        )
        add_edge(device_id, node_id, "contains", component.get("status") or "unknown", component.get("source") or "unspecified")
        component_bus = str(component.get("bus") or "").lower()
        matching_bus = next((bus_id for key, bus_id in buses.items() if key and (key in component_bus or component_bus in key)), None)
        if matching_bus:
            add_edge(matching_bus, node_id, "connects", component.get("status") or "unknown", component.get("source") or "unspecified")

    pin_nodes: dict[str, str] = {}
    for pin in inspection.get("pins") or []:
        node_id = add_node(
            f"pin:{_slug(pin.get('name'))}",
            "pin",
            pin.get("name") or "Unknown pin",
            pin.get("status") or "unknown",
            pin.get("source") or "unspecified",
            aliases=pin.get("aliases") or [],
            functions=pin.get("functions") or [],
            group=pin.get("group"),
        )
        for pin_name in [pin.get("name"), *(pin.get("aliases") or [])]:
            if pin_name:
                pin_nodes[str(pin_name).casefold()] = node_id
        add_edge(device_id, node_id, "exposes", pin.get("status") or "unknown", pin.get("source") or "unspecified")
        functions = " ".join(str(item).lower() for item in pin.get("functions") or [])
        matching_bus = next((bus_id for key, bus_id in buses.items() if key and key in functions), None)
        if matching_bus:
            add_edge(matching_bus, node_id, "uses_pin", pin.get("status") or "unknown", pin.get("source") or "unspecified")

    for peripheral in inspection.get("attached_peripherals") or []:
        node_id = add_node(
            f"peripheral:{_slug(peripheral.get('id') or peripheral.get('address') or peripheral.get('name'))}",
            "attached_peripheral",
            peripheral.get("name") or "Unresolved peripheral",
            peripheral.get("status") or "unknown",
            peripheral.get("source") or "unspecified",
            bus=peripheral.get("bus"),
            address=peripheral.get("address"),
            candidates=peripheral.get("candidates") or [],
        )
        add_edge(device_id, node_id, "attached_to", peripheral.get("status") or "unknown", peripheral.get("source") or "unspecified")
        peripheral_bus = str(peripheral.get("bus") or "").lower()
        matching_bus = next((bus_id for key, bus_id in buses.items() if key and (key in peripheral_bus or peripheral_bus in key)), None)
        if matching_bus:
            add_edge(matching_bus, node_id, "enumerates", peripheral.get("status") or "unknown", peripheral.get("source") or "unspecified")
        attached_pin = pin_nodes.get(str(peripheral.get("address") or "").casefold())
        if attached_pin:
            add_edge(attached_pin, node_id, "connected_to", peripheral.get("status") or "unknown", peripheral.get("source") or "unspecified")

    for service in inspection.get("services") or []:
        service_id = add_node(
            f"service:{_slug(service.get('name'))}-{_slug(service.get('port'))}",
            "service",
            service.get("name") or "Target service",
            service.get("status") or "unknown",
            "live target inspection",
            address=service.get("address"),
            port=service.get("port"),
            url=service.get("url"),
        )
        add_edge(device_id, service_id, "offers", service.get("status") or "unknown", "live target inspection")

    for definition in inspection.get("definitions") or []:
        definition_id = add_node(
            f"definition:{_slug(definition.get('source_sha256'))}",
            "definition",
            definition.get("source_name") or "Imported definition",
            "declared",
            definition.get("provenance", {}).get("kind") or "uploaded definition",
            format=definition.get("format"),
            scope=definition.get("scope"),
            counts=definition.get("counts") or {},
            sha256=definition.get("source_sha256"),
        )
        add_edge(definition_id, device_id, "describes", "declared", definition.get("source_name") or "uploaded definition")

    counts: dict[str, int] = {}
    for node in nodes:
        counts[node["kind"]] = counts.get(node["kind"], 0) + 1
    return {
        "schema_version": "1.0",
        "root": device_id,
        "nodes": nodes,
        "edges": edges,
        "counts": counts,
        "calibration": inspection_calibration(inspection),
    }
