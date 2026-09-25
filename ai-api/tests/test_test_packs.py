from app.test_packs import build_test_pack


def test_test_pack_is_versioned_deterministic_and_preserves_risk() -> None:
    inspection = {
        "identifier": "serial:COM9",
        "model": "Fixture",
        "adapter": {"id": "fixture"},
        "tests": [
            {"id": "presence", "name": "Presence", "risk": "passive", "available": True, "description": "Check"},
            {"id": "probe", "name": "Probe", "risk": "disruptive", "available": False, "description": "Probe"},
        ],
    }
    first = build_test_pack(inspection)
    second = build_test_pack(inspection)
    assert first == second
    assert first["schema_version"] == "1.0"
    assert first["available_count"] == 1
    assert first["tests"][1]["risk"] == "disruptive"


def test_test_pack_hash_changes_when_availability_changes() -> None:
    base = {"identifier": "x", "model": "Board", "tests": [{"id": "probe", "available": False}]}
    changed = {**base, "tests": [{"id": "probe", "available": True}]}
    assert build_test_pack(base)["pack_hash"] != build_test_pack(changed)["pack_hash"]
