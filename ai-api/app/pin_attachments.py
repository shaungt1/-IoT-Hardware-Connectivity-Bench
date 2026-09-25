from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any


def find_pin(inspection: dict[str, Any], pin_name: str) -> dict[str, Any] | None:
    expected = pin_name.strip().casefold()
    for pin in inspection.get("pins") or []:
        names = [pin.get("name"), *(pin.get("aliases") or [])]
        if any(str(name or "").casefold() == expected for name in names):
            return pin
    return None


def apply_pin_attachments(inspection: dict[str, Any], attachments: list[dict[str, Any]]) -> None:
    """Merge user-confirmed observations without promoting detection status."""
    normalized: list[dict[str, Any]] = []
    components = inspection.setdefault("components", [])
    peripherals = inspection.setdefault("attached_peripherals", [])
    evidence = inspection.setdefault("evidence", [])

    for value in attachments:
        pin = find_pin(inspection, str(value.get("pin") or ""))
        if pin is None:
            continue
        attachment = {
            "pin": str(pin.get("name")),
            "component_name": str(value.get("component_name") or "Unidentified attachment"),
            "component_type": str(value.get("component_type") or "user_defined"),
            "interface": str(value.get("interface") or "direct_pin"),
            "notes": str(value.get("notes") or ""),
            "status": "declared",
            "source": "User-confirmed pin attachment",
        }
        normalized.append(attachment)
        pin["attachment"] = deepcopy(attachment)
        suffix = hashlib.sha256(
            f"{attachment['pin']}|{attachment['component_name']}".encode("utf-8")
        ).hexdigest()[:12]
        component_id = f"user-attachment:{suffix}"
        if not any(item.get("id") == component_id for item in components):
            components.append({
                "id": component_id,
                "name": attachment["component_name"],
                "type": attachment["component_type"],
                "bus": attachment["interface"],
                "variant": None,
                "status": "declared",
                "source": attachment["source"],
            })
        peripherals.append({
            "id": component_id,
            "name": attachment["component_name"],
            "bus": attachment["interface"],
            "status": "declared",
            "address": attachment["pin"],
            "candidates": [attachment["component_name"]],
            "source": attachment["source"],
        })
        evidence.append({
            "claim": f"{attachment['component_name']} is connected to {attachment['pin']}",
            "status": "declared",
            "source": attachment["source"],
        })

    inspection["user_pin_attachments"] = normalized
