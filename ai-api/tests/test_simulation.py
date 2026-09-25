from __future__ import annotations

from pathlib import Path

import pytest

from app.prototype import PrototypeEdge, PrototypeNode, PrototypePin, PrototypePosition, PrototypeProject
from app.simulation import SimulationError, compile_netlist, simulate_project


def fixture_project() -> PrototypeProject:
    board = PrototypeNode(id="board", kind="controller", label="Board", mode="simulated", position=PrototypePosition(x=0, y=0), pins=[
        PrototypePin(id="3V3", label="3V3", functions=["Power"], direction="power", voltage=3.3),
        PrototypePin(id="GND", label="GND", functions=["Ground"], direction="power", voltage=0),
    ])
    resistor = PrototypeNode(id="r1", kind="passive", label="220 ohm", mode="simulated", component_id="wokwi-resistor", position=PrototypePosition(x=100, y=0), properties={"resistance_ohms": 220}, pins=[
        PrototypePin(id="1", label="1", direction="bidirectional"), PrototypePin(id="2", label="2", direction="bidirectional"),
    ])
    return PrototypeProject(identifier="fixture", name="SPICE fixture", nodes=[board, resistor], edges=[
        PrototypeEdge(id="a", source="board", source_pin="3V3", target="r1", target_pin="1"),
        PrototypeEdge(id="b", source="r1", source_pin="2", target="board", target_pin="GND"),
    ])


def test_compile_netlist_maps_real_graph_nets() -> None:
    netlist, endpoints, warnings = compile_netlist(fixture_project())
    assert "DC 3.3" in netlist
    assert " 220" in netlist
    assert endpoints["board.GND"] == "0"
    assert warnings == []


def test_compile_netlist_requires_power_and_supported_load() -> None:
    empty = PrototypeProject(identifier="fixture", name="Empty", nodes=[], edges=[])
    with pytest.raises(SimulationError, match="power rail"):
        compile_netlist(empty)


def test_installed_ngspice_runs_operating_point() -> None:
    root = Path(__file__).resolve().parents[2]
    if not (root / ".tools" / "ngspice46" / "Spice64" / "bin" / "ngspice_con.exe").is_file():
        pytest.skip("local ngspice resource is not installed")
    report = simulate_project(fixture_project(), root)
    assert report["engine"] == "ngspice"
    assert report["passed"] is True
    assert any(abs(value - 3.3) < 0.001 for value in report["node_voltages"].values())
