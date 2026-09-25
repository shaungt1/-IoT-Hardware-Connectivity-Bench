from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .prototype import PrototypeProject, validate_project


class SimulationError(ValueError):
    pass


def ngspice_path(root: Path) -> Path | None:
    configured = os.getenv("IOT_BENCH_NGSPICE")
    candidates = [
        Path(configured) if configured else None,
        root / ".tools" / "ngspice46" / "Spice64" / "bin" / "ngspice_con.exe",
        root / ".tools" / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe",
    ]
    return next((item for item in candidates if item and item.is_file()), None)


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(self, item: tuple[str, str]) -> tuple[str, str]:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: tuple[str, str], right: tuple[str, str]) -> None:
        self.parent[self.find(right)] = self.find(left)


def _is_ground(pin: Any) -> bool:
    return pin.voltage == 0 or pin.id.upper().startswith(("GND", "VSS")) or any(value.lower() == "ground" for value in pin.functions)


def compile_netlist(project: PrototypeProject) -> tuple[str, dict[str, str], list[str]]:
    validated, issues = validate_project(project)
    invalid = [item for item in issues if item["severity"] == "invalid"]
    if invalid:
        raise SimulationError(f"Electrical simulation is blocked by {len(invalid)} invalid net(s)")

    union = _UnionFind()
    pin_lookup = {(node.id, pin.id): pin for node in validated.nodes for pin in node.pins}
    for endpoint in pin_lookup:
        union.find(endpoint)
    for edge in validated.edges:
        union.union((edge.source, edge.source_pin), (edge.target, edge.target_pin))

    groups: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for endpoint in pin_lookup:
        groups.setdefault(union.find(endpoint), []).append(endpoint)
    ground_groups = {root for root, endpoints in groups.items() if any(_is_ground(pin_lookup[item]) for item in endpoints)}
    names: dict[tuple[str, str], str] = {}
    next_net = 1
    for root, endpoints in groups.items():
        name = "0" if root in ground_groups else f"n{next_net}"
        if root not in ground_groups:
            next_net += 1
        for endpoint in endpoints:
            names[endpoint] = name

    lines = ["IoT Hardware Connectivity Bench prototype", ".options noacct"]
    warnings: list[str] = []
    source_index = resistor_index = diode_index = 1
    source_nets: dict[str, float] = {}
    modeled_nodes: set[str] = set()

    for node in validated.nodes:
        for pin in node.pins:
            net = names[(node.id, pin.id)]
            if net != "0" and pin.direction == "power" and pin.voltage and pin.voltage > 0:
                previous = source_nets.get(net)
                if previous is not None and abs(previous - pin.voltage) > 0.01:
                    raise SimulationError(f"Net {net} contains conflicting {previous:g} V and {pin.voltage:g} V sources")
                if previous is None:
                    lines.append(f"V{source_index} {net} 0 DC {pin.voltage:g}")
                    source_nets[net] = pin.voltage
                    source_index += 1

        component = (node.component_id or "").lower()
        if component == "wokwi-resistor" and len(node.pins) >= 2:
            resistance = float(node.properties.get("resistance_ohms", 220))
            if not 0.001 <= resistance <= 1e12:
                raise SimulationError(f"{node.label} resistance must be between 0.001 ohm and 1 Tohm")
            lines.append(f"R{resistor_index} {names[(node.id, node.pins[0].id)]} {names[(node.id, node.pins[1].id)]} {resistance:g}")
            resistor_index += 1
            modeled_nodes.add(node.id)
        elif component in {"wokwi-led", "wokwi-rgb-led"} and len(node.pins) >= 2:
            common = next((pin for pin in node.pins if _is_ground(pin)), node.pins[1])
            channels = [pin for pin in node.pins if pin.id != common.id]
            for channel in channels:
                lines.append(f"D{diode_index} {names[(node.id, channel.id)]} {names[(node.id, common.id)]} D_LED")
                diode_index += 1
            modeled_nodes.add(node.id)
        elif component == "wokwi-potentiometer" and len(node.pins) >= 3:
            value = max(0.1, min(99.9, float(node.state.get("value", 50))))
            total = float(node.properties.get("resistance_ohms", 10_000))
            pin_by_id = {pin.id: pin for pin in node.pins}
            if {"VCC", "SIG", "GND"} <= pin_by_id.keys():
                lines.extend([
                    f"R{resistor_index} {names[(node.id, 'VCC')]} {names[(node.id, 'SIG')]} {total * (100 - value) / 100:g}",
                    f"R{resistor_index + 1} {names[(node.id, 'SIG')]} {names[(node.id, 'GND')]} {total * value / 100:g}",
                ])
                resistor_index += 2
                modeled_nodes.add(node.id)
        elif component == "wokwi-pushbutton" and len(node.pins) >= 2:
            resistance = 0.01 if node.state.get("pressed") else 1e9
            lines.append(f"R{resistor_index} {names[(node.id, node.pins[0].id)]} {names[(node.id, node.pins[1].id)]} {resistance:g}")
            resistor_index += 1
            modeled_nodes.add(node.id)

    if diode_index > 1:
        lines.append(".model D_LED D(Is=1e-20 N=2 Rs=10)")
    if not source_nets:
        raise SimulationError("No connected positive power rail is available for a DC operating-point simulation")
    if resistor_index == 1 and diode_index == 1:
        raise SimulationError("No supported electrical load is connected; add a resistor, LED, potentiometer, or switch")
    for node in validated.nodes:
        if node.id not in modeled_nodes and node.kind != "controller":
            warnings.append(f"{node.label} has no SPICE behavioral model and was omitted")
    observed = sorted({name for name in names.values() if name != "0"})
    lines.extend([".op", f".print op {' '.join(f'v({name})' for name in observed)}", ".end"])
    endpoint_names = {f"{node}.{pin}": name for (node, pin), name in names.items()}
    return "\n".join(lines) + "\n", endpoint_names, warnings


def _parse_operating_point(log: str, nets: list[str]) -> dict[str, float]:
    for line in reversed(log.splitlines()):
        fields = line.strip().split()
        if fields and fields[0] == "0" and len(fields) >= len(nets) + 1:
            try:
                return {net: float(fields[index + 1]) for index, net in enumerate(nets)}
            except ValueError:
                continue
    values: dict[str, float] = {}
    for net in nets:
        match = re.search(rf"^\s*{re.escape(net)}\s+([-+0-9.eE]+)\s*$", log, re.MULTILINE)
        if match:
            values[net] = float(match.group(1))
    return values


def simulate_project(project: PrototypeProject, root: Path) -> dict[str, Any]:
    executable = ngspice_path(root)
    if executable is None:
        raise SimulationError("ngspice is not installed; run the local resource installer")
    netlist, endpoints, warnings = compile_netlist(project)
    nets = sorted({value for value in endpoints.values() if value != "0"})
    with tempfile.TemporaryDirectory(prefix="iot-bench-spice-") as directory:
        work = Path(directory)
        circuit = work / "prototype.cir"
        log_path = work / "ngspice.log"
        circuit.write_text(netlist, encoding="ascii")
        try:
            result = subprocess.run(
                [str(executable), "-b", "-o", str(log_path), str(circuit)],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
                cwd=executable.parents[1],
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SimulationError(f"ngspice execution failed: {error}") from error
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else result.stdout + result.stderr
        if result.returncode != 0 or "fatal error" in log.lower():
            raise SimulationError("ngspice rejected the generated circuit")
    voltages = _parse_operating_point(log, nets)
    return {
        "schema_version": "1.0",
        "engine": "ngspice",
        "analysis": "dc_operating_point",
        "passed": bool(voltages),
        "node_voltages": voltages,
        "endpoint_nets": endpoints,
        "warnings": warnings,
        "netlist": netlist,
        "safety": {"physical_hardware_changed": False, "subprocess_timeout_seconds": 8},
    }
