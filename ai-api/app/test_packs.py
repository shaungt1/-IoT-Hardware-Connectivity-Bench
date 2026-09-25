from __future__ import annotations

import hashlib
import json
from typing import Any


TEST_PACK_SCHEMA_VERSION = "1.0"


def build_test_pack(inspection: dict[str, Any]) -> dict[str, Any]:
    tests = [
        {
            "id": str(item.get("id")),
            "name": str(item.get("name") or item.get("id")),
            "risk": str(item.get("risk") or "unknown"),
            "available": bool(item.get("available")),
            "description": str(item.get("description") or ""),
            "action": item.get("action"),
        }
        for item in inspection.get("tests") or []
        if item.get("id")
    ]
    fingerprint_payload = {
        "schema_version": TEST_PACK_SCHEMA_VERSION,
        "identifier": inspection.get("identifier"),
        "model": inspection.get("model"),
        "adapter": (inspection.get("adapter") or {}).get("id"),
        "tests": tests,
    }
    pack_hash = hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        **fingerprint_payload,
        "pack_id": f"bench-tests:{pack_hash[:16]}",
        "pack_hash": pack_hash,
        "count": len(tests),
        "available_count": sum(1 for item in tests if item["available"]),
    }
