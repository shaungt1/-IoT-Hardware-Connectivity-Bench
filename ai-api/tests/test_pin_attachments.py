from app.evidence_graph import build_evidence_graph
from app.pin_attachments import apply_pin_attachments, find_pin


def fixture_inspection() -> dict:
    return {
        "identifier": "serial:fixture",
        "model": "Fixture board",
        "classification": "microcontroller_board",
        "confidence": 0.8,
        "identity_layers": [],
        "components": [],
        "attached_peripherals": [],
        "connection_interfaces": [],
        "services": [],
        "definitions": [],
        "evidence": [],
        "pins": [{
            "name": "D1",
            "aliases": ["GPIO1"],
            "group": "Header",
            "functions": ["GPIO"],
            "status": "detected",
            "source": "fixture",
        }],
    }


def test_user_attachment_is_declared_and_connected_to_exact_pin() -> None:
    inspection = fixture_inspection()

    apply_pin_attachments(inspection, [{
        "pin": "GPIO1",
        "component_name": "Water temperature sensor",
        "component_type": "sensor",
        "interface": "one_wire",
        "notes": "Observed on the workbench",
    }])
    graph = build_evidence_graph(inspection)

    assert find_pin(inspection, "D1")["attachment"]["status"] == "declared"
    assert inspection["attached_peripherals"][0]["address"] == "D1"
    assert inspection["components"][0]["status"] == "declared"
    assert any(
        edge["source"] == "pin:d1"
        and edge["relation"] == "connected_to"
        and edge["status"] == "declared"
        for edge in graph["edges"]
    )


def test_attachment_for_unknown_pin_is_not_promoted() -> None:
    inspection = fixture_inspection()

    apply_pin_attachments(inspection, [{"pin": "D99", "component_name": "Unknown"}])

    assert inspection["user_pin_attachments"] == []
    assert inspection["components"] == []
    assert inspection["evidence"] == []
