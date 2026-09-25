from __future__ import annotations

import time
from copy import deepcopy
from typing import Any


class DeviceStateManager:
    """Tracks one authoritative, present-now hardware inventory and its deltas."""

    def __init__(self) -> None:
        self._inventory: list[dict[str, Any]] = []
        self._revision = 0
        self._events: list[dict[str, Any]] = []
        self._last_delta: dict[str, list[str]] = {"added": [], "removed": [], "changed": []}

    def update(self, inventory: list[dict[str, Any]]) -> bool:
        next_by_id = {str(item["id"]): deepcopy(item) for item in inventory}
        current_by_id = {str(item["id"]): item for item in self._inventory}
        added = sorted(next_by_id.keys() - current_by_id.keys())
        removed = sorted(current_by_id.keys() - next_by_id.keys())
        changed = sorted(
            identifier
            for identifier in next_by_id.keys() & current_by_id.keys()
            if next_by_id[identifier] != current_by_id[identifier]
        )
        self._last_delta = {"added": added, "removed": removed, "changed": changed}
        if not (added or removed or changed):
            return False

        self._revision += 1
        observed_at = time.time()
        for action, identifiers, source in (
            ("connected", added, next_by_id),
            ("disconnected", removed, current_by_id),
            ("changed", changed, next_by_id),
        ):
            for identifier in identifiers:
                item = source[identifier]
                self._events.append(
                    {
                        "revision": self._revision,
                        "action": action,
                        "identifier": identifier,
                        "name": item.get("name") or item.get("description") or identifier,
                        "interface": item.get("device") or item.get("interface") or item.get("ip_address"),
                        "observed_at": observed_at,
                    }
                )
        self._events = self._events[-100:]
        self._inventory = [next_by_id[identifier] for identifier in sorted(next_by_id)]
        return True

    def last_delta(self) -> dict[str, list[str]]:
        return deepcopy(self._last_delta)

    def snapshot(self) -> dict[str, Any]:
        return {
            "revision": self._revision,
            "hardware": deepcopy(self._inventory),
            "events": deepcopy(self._events[-20:]),
        }
