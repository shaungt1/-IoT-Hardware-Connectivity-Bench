from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class PrototypePosition(BaseModel):
    x: float = Field(ge=-100_000, le=100_000)
    y: float = Field(ge=-100_000, le=100_000)


class PrototypePin(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=128)
    functions: list[str] = Field(default_factory=list, max_length=32)
    voltage: float | None = Field(default=None, ge=-1000, le=1000)
    direction: Literal["input", "output", "bidirectional", "power", "unknown"] = "unknown"


class PrototypeNode(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    kind: Literal["controller", "sensor", "output", "passive", "instrument", "custom"]
    label: str = Field(min_length=1, max_length=128)
    mode: Literal["physical", "simulated", "hybrid", "disconnected", "user_defined"]
    position: PrototypePosition
    component_id: str | None = Field(default=None, max_length=128)
    target_identifier: str | None = Field(default=None, max_length=512)
    pins: list[PrototypePin] = Field(default_factory=list, max_length=256)
    properties: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)


class PrototypeEdge(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=128)
    source_pin: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=128)
    target_pin: str = Field(min_length=1, max_length=128)
    signal: str = Field(default="unknown", max_length=64)
    state_source: Literal["physical", "simulated", "hybrid", "user_defined"] = "user_defined"
    validation: Literal["valid", "warning", "invalid", "unknown"] = "unknown"
    message: str = Field(default="Connection has not been electrically validated.", max_length=512)


class PrototypeProject(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    revision: int = Field(default=0, ge=0)
    identifier: str = Field(min_length=1, max_length=512)
    name: str = Field(min_length=1, max_length=128)
    nodes: list[PrototypeNode] = Field(default_factory=list, max_length=500)
    edges: list[PrototypeEdge] = Field(default_factory=list, max_length=1500)
    updated_at: str | None = None

    @model_validator(mode="after")
    def validate_graph(self) -> "PrototypeProject":
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Prototype node identifiers must be unique")
        edge_ids = [edge.id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("Prototype edge identifiers must be unique")
        nodes = {node.id: node for node in self.nodes}
        for node in self.nodes:
            pin_ids = [pin.id for pin in node.pins]
            if len(pin_ids) != len(set(pin_ids)):
                raise ValueError(f"Prototype node {node.id} has duplicate pin identifiers")
            if len(json.dumps({"properties": node.properties, "state": node.state}, default=str)) > 131_072:
                raise ValueError(f"Prototype node {node.id} metadata exceeds the 128 KiB limit")
        for edge in self.edges:
            if edge.source not in nodes or edge.target not in nodes:
                raise ValueError(f"Prototype edge {edge.id} references an unknown node")
            source_pins = {pin.id for pin in nodes[edge.source].pins}
            target_pins = {pin.id for pin in nodes[edge.target].pins}
            if edge.source_pin not in source_pins or edge.target_pin not in target_pins:
                raise ValueError(f"Prototype edge {edge.id} references an unknown pin")
        return self


def _inspected_pins(inspection: dict[str, Any]) -> list[PrototypePin]:
    pins: list[PrototypePin] = []
    for index, pin in enumerate(inspection.get("pins", [])):
        name = str(pin.get("name") or f"pin-{index}")
        functions = [str(item) for item in pin.get("functions", [])]
        normalized = " ".join([name, *functions]).lower()
        direction: Literal["input", "output", "bidirectional", "power", "unknown"] = "bidirectional"
        voltage = 3.3
        if "ground" in normalized or name.upper() == "GND":
            direction, voltage = "power", 0.0
        elif name.upper() == "5V" or "5 v " in f"{normalized} ":
            direction, voltage = "power", 5.0
        elif name.upper() == "3V3" or "3.3 v" in normalized:
            direction, voltage = "power", 3.3
        elif "uart tx" in normalized:
            direction = "output"
        elif "uart rx" in normalized:
            direction = "input"
        pins.append(
            PrototypePin(
                id=name,
                label=" / ".join([name, *[str(alias) for alias in pin.get("aliases", [])]]),
                functions=functions,
                direction=direction,
                voltage=voltage,
            )
        )
    return pins


def _controller_properties(inspection: dict[str, Any]) -> dict[str, Any]:
    telemetry = inspection.get("telemetry") or {}
    return {
        "classification": inspection.get("classification"),
        "mcu": inspection.get("mcu"),
        "architecture": inspection.get("architecture"),
        "runtime": inspection.get("runtime"),
        "confidence": inspection.get("confidence"),
        "board_id": telemetry.get("board_id"),
        "pin_map_version": telemetry.get("pin_map_version"),
        "pin_constraints": {pin.get("name"): pin.get("electrical") for pin in inspection.get("pins", []) if pin.get("name") and pin.get("electrical")},
        "source": "Authenticated inspection and vendor board definition",
    }


def reconcile_project(project_data: dict[str, Any], identifier: str, inspection: dict[str, Any]) -> PrototypeProject:
    """Refresh the physical target while preserving user-created parts and valid nets."""

    project = PrototypeProject.model_validate(project_data)
    exact_pins = _inspected_pins(inspection)
    model = str(inspection.get("model") or "Selected device")
    telemetry = inspection.get("telemetry") or {}
    component_id = str(telemetry.get("board_id") or inspection.get("family") or model)
    physical = next((node for node in project.nodes if node.target_identifier == identifier), None)
    legacy_placeholder_ids = {"generic-analog-sensor", "generic-led"}
    retained_nodes = [node for node in project.nodes if node.component_id not in legacy_placeholder_ids]
    if physical is None:
        physical = PrototypeNode(
            id="selected-controller",
            kind="controller",
            label=model,
            mode="physical",
            position=PrototypePosition(x=360, y=180),
            target_identifier=identifier,
        )
        nodes = [physical, *retained_nodes]
    else:
        nodes = retained_nodes
    updated = physical.model_copy(update={
        "label": model,
        "mode": "physical",
        "component_id": component_id,
        "pins": exact_pins,
        "properties": {**physical.properties, **_controller_properties(inspection), "pin_map": "Exact inspected board map"},
    })
    nodes = [updated if node.id == physical.id else node for node in nodes]
    pin_ids = {node.id: {pin.id for pin in node.pins} for node in nodes}
    edges = [
        edge for edge in project.edges
        if edge.source_pin in pin_ids.get(edge.source, set()) and edge.target_pin in pin_ids.get(edge.target, set())
    ]
    return PrototypeProject(
        revision=project.revision,
        identifier=identifier,
        name=f"{model} prototype",
        nodes=nodes,
        edges=edges,
        updated_at=project.updated_at,
    )


def seed_project(identifier: str, inspection: dict[str, Any]) -> PrototypeProject:
    pins = _inspected_pins(inspection)
    telemetry = inspection.get("telemetry") or {}
    component_id = str(telemetry.get("board_id") or inspection.get("family") or inspection.get("model") or "selected-device")
    controller = PrototypeNode(
        id="selected-controller",
        kind="controller",
        label=str(inspection.get("model") or "Selected device"),
        mode="physical",
        position=PrototypePosition(x=360, y=180),
        component_id=component_id,
        target_identifier=identifier,
        pins=pins,
        properties={**_controller_properties(inspection), "pin_map": "Exact inspected board map"},
    )
    return PrototypeProject(
        identifier=identifier,
        name=f"{controller.label} prototype",
        nodes=[controller],
        edges=[],
    )


def _is_ground(pin: PrototypePin) -> bool:
    return pin.voltage == 0 or any(item.lower() == "ground" for item in pin.functions) or pin.id.upper().startswith("GND")


def _edge_validation(source: PrototypePin, target: PrototypePin) -> tuple[str, str, str]:
    common = next((item for item in source.functions if item in target.functions), None)
    signal = common or (source.functions + target.functions + ["signal"])[0]
    source_ground, target_ground = _is_ground(source), _is_ground(target)
    if source_ground != target_ground:
        non_ground = target if source_ground else source
        if non_ground.direction == "output" or (non_ground.direction == "power" and non_ground.voltage not in (None, 0)):
            return signal, "invalid", "Ground cannot be wired directly to a positive rail or driven output."
    if source_ground and target_ground:
        return "GND", "valid", "Ground reference connection."
    if source.direction == target.direction == "output":
        return signal, "invalid", "Two driven outputs can contend and must not be connected directly."
    if source.direction == target.direction == "power" and source.voltage is not None and target.voltage is not None and abs(source.voltage - target.voltage) > 0.25:
        return "power", "invalid", f"{source.voltage} V and {target.voltage} V rails are incompatible."
    supply = source if source.direction == "power" else target if target.direction == "power" else None
    load = target if supply is source else source
    if supply and supply.voltage is not None and load.voltage is not None and supply.voltage > load.voltage + 0.25:
        return signal, "invalid", f"{supply.voltage} V exceeds the {load.voltage} V target rating."
    if source.direction == target.direction == "input":
        return signal, "warning", "Both endpoints are inputs; this net has no identified driver."
    if not common and source.direction != "power" and target.direction != "power":
        return signal, "warning", "Pin functions do not share a known bus or signal role."
    return signal, "valid", f"Compatible {common} connection." if common else "Direction and voltage checks passed."


def validate_project(project: PrototypeProject) -> tuple[PrototypeProject, list[dict[str, Any]]]:
    nodes = {node.id: node for node in project.nodes}
    pins = {(node.id, pin.id): pin for node in project.nodes for pin in node.pins}
    issues: list[dict[str, Any]] = []
    updated: list[PrototypeEdge] = []
    endpoint_edges: dict[tuple[str, str], list[int]] = {}
    adjacency: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for index, edge in enumerate(project.edges):
        source_key, target_key = (edge.source, edge.source_pin), (edge.target, edge.target_pin)
        source, target = pins[source_key], pins[target_key]
        signal, validation, message = _edge_validation(source, target)
        modes = {nodes[edge.source].mode, nodes[edge.target].mode}
        state_source: Literal["physical", "simulated", "hybrid", "user_defined"]
        if modes <= {"physical"}:
            state_source = "physical"
        elif modes <= {"simulated"}:
            state_source = "simulated"
        elif "physical" in modes and "simulated" in modes:
            state_source = "hybrid"
        else:
            state_source = "user_defined"
        updated.append(edge.model_copy(update={"signal": signal, "validation": validation, "message": message, "state_source": state_source}))
        endpoint_edges.setdefault(source_key, []).append(index)
        endpoint_edges.setdefault(target_key, []).append(index)
        adjacency.setdefault(source_key, set()).add(target_key)
        adjacency.setdefault(target_key, set()).add(source_key)
        if validation != "valid":
            issues.append({"edge_id": edge.id, "severity": validation, "message": message})

    visited: set[tuple[str, str]] = set()
    for start in adjacency:
        if start in visited:
            continue
        stack, endpoints, edge_indexes = [start], set(), set()
        while stack:
            item = stack.pop()
            if item in visited:
                continue
            visited.add(item); endpoints.add(item)
            edge_indexes.update(endpoint_edges.get(item, []))
            stack.extend(adjacency.get(item, set()) - visited)
        drivers = [item for item in endpoints if pins[item].direction == "output"]
        rails = sorted({pins[item].voltage for item in endpoints if pins[item].direction == "power" and pins[item].voltage is not None})
        net_error = None
        if len(drivers) > 1:
            net_error = f"Net has {len(drivers)} driven outputs and may cause contention."
        elif rails and rails[-1] - rails[0] > 0.25:
            net_error = f"Net joins incompatible power rails: {', '.join(f'{value:g} V' for value in rails)}."
        if net_error:
            for edge_index in edge_indexes:
                edge = updated[edge_index]
                updated[edge_index] = edge.model_copy(update={"validation": "invalid", "message": net_error})
                issues.append({"edge_id": edge.id, "severity": "invalid", "message": net_error})

    return project.model_copy(update={"edges": updated}), issues
