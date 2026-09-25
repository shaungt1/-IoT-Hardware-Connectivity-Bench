from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.pin_knowledge import annotate_pins
from app.prototype import PrototypeEdge, PrototypeNode, PrototypePin, PrototypePosition, PrototypeProject, reconcile_project, seed_project, validate_project
from app.storage import StateStore


def test_seed_project_uses_inspected_device_and_pins() -> None:
    project = seed_project(
        "serial:COM8",
        {
            "model": "Example controller",
            "family": "Example family",
            "classification": "microcontroller_board",
            "mcu": "EX123",
            "pins": [{"name": "A0", "functions": ["ADC", "GPIO"]}],
        },
    )

    assert project.identifier == "serial:COM8"
    assert project.nodes[0].mode == "physical"
    assert project.nodes[0].pins[0].id == "A0"
    assert project.nodes[0].properties["mcu"] == "EX123"


def test_graph_rejects_dangling_pin_reference() -> None:
    node = PrototypeNode(
        id="board",
        kind="controller",
        label="Board",
        mode="physical",
        position=PrototypePosition(x=0, y=0),
        pins=[PrototypePin(id="A0", label="A0", functions=["ADC"])],
    )

    with pytest.raises(ValidationError, match="unknown pin"):
        PrototypeProject(
            identifier="board-1",
            name="Bad graph",
            nodes=[node],
            edges=[PrototypeEdge(id="wire-1", source="board", source_pin="missing", target="board", target_pin="A0")],
        )


def test_graph_rejects_duplicate_pin_identifiers() -> None:
    with pytest.raises(ValidationError, match="duplicate pin"):
        PrototypeProject(
            identifier="board-1",
            name="Duplicate pins",
            nodes=[PrototypeNode(
                id="board",
                kind="controller",
                label="Board",
                mode="physical",
                position=PrototypePosition(x=0, y=0),
                pins=[
                    PrototypePin(id="A0", label="A0", functions=["ADC"]),
                    PrototypePin(id="A0", label="A0 duplicate", functions=["GPIO"]),
                ],
            )],
        )


def test_project_round_trips_through_store(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")
    project = seed_project("device-1", {"model": "Board", "pins": []})

    saved = store.save_prototype_project(project.identifier, project.model_dump(mode="json"))
    loaded = store.get_prototype_project(project.identifier)

    assert loaded == saved
    assert loaded is not None
    assert loaded["updated_at"]
    assert loaded["revision"] == 1


def test_project_store_rejects_stale_revision(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")
    project = seed_project("device-1", {"model": "Board", "pins": []})
    first = store.save_prototype_project(project.identifier, project.model_dump(mode="json"))

    store.save_prototype_project(project.identifier, first)
    with pytest.raises(ValueError, match="changed in another session"):
        store.save_prototype_project(project.identifier, first)


def test_pin_knowledge_normalizes_common_aliases() -> None:
    pins = annotate_pins(
        [{"name": "SCLK", "aliases": ["D5"], "functions": ["SPI clock"], "group": "right"}]
    )

    assert pins[0]["knowledge"][0]["canonical"] == "SPI SCK / SCLK"
    assert "Clock frequency" in pins[0]["knowledge"][0]["caution"]


def test_saved_representative_board_is_reconciled_to_exact_inspected_target() -> None:
    old = seed_project("serial:COM6", {"model": "Generic ESP32", "pins": [{"name": "GPIO22", "functions": ["GPIO"]}]})
    old.nodes.append(PrototypeNode(
        id="led",
        kind="output",
        label="LED",
        mode="simulated",
        position=PrototypePosition(x=700, y=200),
        pins=[PrototypePin(id="A", label="Anode", functions=["GPIO"], direction="input", voltage=3.3)],
    ))
    old.nodes.append(PrototypeNode(
        id="legacy-placeholder",
        kind="sensor",
        label="Virtual analog sensor",
        mode="simulated",
        component_id="generic-analog-sensor",
        position=PrototypePosition(x=30, y=200),
        pins=[],
    ))
    inspection = {
        "model": "Seeed Studio XIAO ESP32-S3 Sense",
        "family": "Seeed XIAO ESP32-S3",
        "pins": [
            {"name": "D0", "aliases": ["A0", "GPIO1"], "functions": ["GPIO", "ADC1_CH0"]},
            {"name": "GND", "aliases": ["Ground"], "functions": ["Ground"]},
        ],
        "telemetry": {"board_id": "seeed_xiao_esp32s3_sense", "pin_map_version": "v1"},
    }

    reconciled = reconcile_project(old.model_dump(mode="json"), "serial:COM6", inspection)

    assert reconciled.name == "Seeed Studio XIAO ESP32-S3 Sense prototype"
    assert reconciled.nodes[0].component_id == "seeed_xiao_esp32s3_sense"
    assert [pin.id for pin in reconciled.nodes[0].pins] == ["D0", "GND"]
    assert reconciled.nodes[0].pins[1].direction == "power"
    assert reconciled.nodes[1].id == "led"
    assert all(node.id != "legacy-placeholder" for node in reconciled.nodes)


def test_backend_validator_rejects_net_wide_output_contention() -> None:
    nodes = [
        PrototypeNode(id=name, kind="output", label=name, mode="simulated", position=PrototypePosition(x=index * 100, y=0), pins=[PrototypePin(id="OUT", label="OUT", direction="output", voltage=3.3)])
        for index, name in enumerate(("one", "two", "three"))
    ]
    project = PrototypeProject(
        identifier="fixture",
        name="Contention fixture",
        nodes=nodes,
        edges=[
            PrototypeEdge(id="a", source="one", source_pin="OUT", target="three", target_pin="OUT"),
            PrototypeEdge(id="b", source="two", source_pin="OUT", target="three", target_pin="OUT"),
        ],
    )
    validated, issues = validate_project(project)
    assert all(edge.validation == "invalid" for edge in validated.edges)
    assert any("contention" in item["message"] for item in issues)


def test_backend_validator_marks_physical_to_simulated_edge_hybrid() -> None:
    source = PrototypeNode(id="board", kind="controller", label="Board", mode="physical", position=PrototypePosition(x=0, y=0), pins=[PrototypePin(id="D1", label="D1", functions=["GPIO"], direction="output", voltage=3.3)])
    target = PrototypeNode(id="led", kind="output", label="LED", mode="simulated", position=PrototypePosition(x=100, y=0), pins=[PrototypePin(id="A", label="A", functions=["GPIO"], direction="input", voltage=3.3)])
    project = PrototypeProject(identifier="fixture", name="Hybrid", nodes=[source, target], edges=[PrototypeEdge(id="wire", source="board", source_pin="D1", target="led", target_pin="A")])
    validated, _ = validate_project(project)
    assert validated.edges[0].state_source == "hybrid"
    assert validated.edges[0].validation == "valid"
