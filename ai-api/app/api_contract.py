from __future__ import annotations


API_VERSION = "1.0"
EVIDENCE_SCHEMA_VERSION = "1.0"
PROTOTYPE_SCHEMA_VERSION = "1.0"
TEST_PACK_SCHEMA_VERSION = "1.0"


def api_contract() -> dict[str, object]:
    """Describe stable local contracts and their trust boundaries."""

    return {
        "api_version": API_VERSION,
        "transport": {
            "http_prefix": "/api",
            "device_state_websocket": "/ws",
            "camera_websocket": "/ws/camera",
            "mcp": "stdio",
        },
        "schemas": {
            "evidence_graph": EVIDENCE_SCHEMA_VERSION,
            "prototype": PROTOTYPE_SCHEMA_VERSION,
            "test_pack": TEST_PACK_SCHEMA_VERSION,
        },
        "surfaces": {
            "public_read": {
                "description": "Versioned, redacted inspection and capability contracts for local clients.",
                "authentication": "loopback boundary",
            },
            "local_control": {
                "description": "Target-bound operations available only to the local hardware service.",
                "authentication": "loopback boundary plus target fingerprint",
            },
            "protected_mutation": {
                "description": "Disruptive or destructive operations require a fresh plan, explicit approval, and an expiring token.",
                "authentication": "loopback boundary, target fingerprint, and approval token",
            },
            "mcp": {
                "description": "Read, inspect, simulate, test, and plan; approval and physical execution are denied.",
                "transport": "local stdio",
            },
        },
        "compatibility": {
            "policy": "Additive fields are backward compatible within API version 1. Breaking changes require a new major version.",
            "response_header": "X-IoT-Bench-API-Version",
        },
        "hosted_release": {
            "supported": False,
            "reason": "Hosted access requires authenticated TLS, tenant isolation, and a separately authenticated local hardware agent.",
        },
    }
