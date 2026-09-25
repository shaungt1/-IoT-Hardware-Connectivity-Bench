from app.evidence_graph import build_evidence_graph


def test_evidence_graph_preserves_status_and_provenance() -> None:
    graph = build_evidence_graph({
        "identifier": "serial:COM9",
        "model": "Fixture board",
        "classification": "microcontroller_board",
        "confidence": 0.8,
        "identity_layers": [
            {"id": "bridge", "layer": "USB bridge", "name": "CP2102", "status": "verified", "source": "USB descriptor"},
            {"id": "target", "layer": "Target", "name": "Unresolved", "status": "unavailable", "source": "No handshake"},
        ],
        "components": [{"id": "sensor", "name": "Sensor candidate", "type": "sensor", "status": "expected", "source": "board definition"}],
        "pins": [{"name": "D1", "aliases": ["GPIO5"], "functions": ["GPIO"], "group": "digital", "status": "expected", "source": "board definition"}],
        "attached_peripherals": [],
        "definitions": [{"source_name": "board.kicad_sch", "source_sha256": "abc", "format": "kicad-schematic", "scope": "design_evidence", "counts": {"components": 1}, "provenance": {"kind": "uploaded_design"}}],
    })
    nodes = {node["id"]: node for node in graph["nodes"]}
    assert graph["schema_version"] == "1.0"
    assert nodes["identity:target"]["status"] == "unavailable"
    assert nodes["component:sensor"]["status"] == "expected"
    assert nodes["pin:d1"]["provenance"]["source"] == "board definition"
    assert nodes["pin:d1"]["confidence"]["may_promote_live_claim"] is False
    assert nodes["identity:bridge"]["confidence"]["live_verified"] is True
    assert graph["calibration"]["definition_promotion"] == "prohibited_without_matching_live_evidence"
    assert any(edge["relation"] == "describes" and edge["status"] == "declared" for edge in graph["edges"])


def test_evidence_graph_deduplicates_duplicate_component_claims() -> None:
    component = {"id": "imu", "name": "IMU", "type": "sensor", "status": "verified", "source": "runtime"}
    graph = build_evidence_graph({"identifier": "x", "model": "Board", "components": [component, component]})
    assert graph["counts"]["component"] == 1
    assert len([edge for edge in graph["edges"] if edge["relation"] == "contains"]) == 1


def test_imported_definition_never_promotes_exact_board_without_live_evidence() -> None:
    graph = build_evidence_graph({
        "identifier": "serial:COM9",
        "model": "User selected board",
        "confidence": 0.99,
        "evidence": [{"source": "saved bench profile", "claim": "Exact model selected", "status": "declared"}],
        "definitions": [{
            "source_name": "board.kicad_sch",
            "source_sha256": "abc",
            "format": "kicad-schematic",
            "scope": "design_evidence",
            "provenance": {"kind": "uploaded_design"},
        }],
    })

    assert graph["calibration"]["exact_board_live_verified"] is False
    assert graph["calibration"]["live_verified_claims"] == 0
    assert next(node for node in graph["nodes"] if node["kind"] == "definition")["confidence"]["live_verified"] is False


def test_evidence_graph_promotes_processor_runtime_bus_and_service_to_first_class_nodes() -> None:
    graph = build_evidence_graph({
        "identifier": "fixture",
        "model": "Fixture board",
        "mcu": "ACM32",
        "architecture": "Arm Cortex-M4",
        "runtime": "fixture-1.0",
        "telemetry": {"firmware": "fixture-1.0"},
        "connection_interfaces": [{"id": "i2c", "name": "I2C", "status": "verified", "adapter": "I2C0"}],
        "components": [{"id": "imu", "name": "IMU", "type": "sensor", "bus": "I2C0", "status": "verified", "source": "runtime"}],
        "pins": [{"name": "SDA", "functions": ["I2C SDA"], "status": "verified", "source": "runtime"}],
        "attached_peripherals": [{"id": "68", "name": "IMU responder", "bus": "I2C0", "address": "0x68", "status": "detected", "source": "scan"}],
        "services": [{"name": "SSH", "address": "192.0.2.10", "port": 22, "status": "verified"}],
    })

    assert graph["counts"]["processor"] == 1
    assert graph["counts"]["runtime"] == 1
    assert graph["counts"]["bus"] == 1
    assert graph["counts"]["service"] == 1
    relations = {edge["relation"] for edge in graph["edges"]}
    assert {"exposes_bus", "connects", "uses_pin", "enumerates", "offers"}.issubset(relations)
