from __future__ import annotations

import asyncio
import time
from typing import Any

from bleak import BleakClient, BleakScanner

LUMNI_TEST_SERVICE_UUID = "8f7a0001-6e7d-4a44-9f9d-10a1b2c3d401"
LUMNI_TEST_STATUS_UUID = "8f7a0002-6e7d-4a44-9f9d-10a1b2c3d401"


class BleMonitor:
    def __init__(self, name_prefix: str = "LUMNI-IOT-") -> None:
        self._name_prefix = name_prefix
        self._state: dict[str, Any] = {
            "detected": False,
            "name": None,
            "address": None,
            "rssi_dbm": None,
            "service_uuids": [],
            "last_seen_at": None,
            "connection_verified": False,
            "last_connected_at": None,
            "devices": [],
            "error": None,
        }
        self._lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()

    async def scan(self, timeout: float = 4.0) -> dict[str, Any]:
        async with self._operation_lock:
            return await self._scan(timeout)

    async def _scan(self, timeout: float) -> dict[str, Any]:
        try:
            devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
            nearby = sorted(
                [
                    {
                        "name": device.name or advertisement.local_name or "Unnamed BLE device",
                        "address": device.address,
                        "rssi_dbm": advertisement.rssi,
                        "service_uuids": advertisement.service_uuids,
                        "is_lumni": (device.name or "").startswith(self._name_prefix)
                        or (advertisement.local_name or "").startswith(self._name_prefix)
                        or LUMNI_TEST_SERVICE_UUID
                        in [uuid.lower() for uuid in advertisement.service_uuids],
                    }
                    for device, advertisement in devices.values()
                ],
                key=lambda item: item["rssi_dbm"],
                reverse=True,
            )[:30]
            matches = [
                (device, advertisement)
                for device, advertisement in devices.values()
                if (device.name or "").startswith(self._name_prefix)
                or (advertisement.local_name or "").startswith(self._name_prefix)
                or LUMNI_TEST_SERVICE_UUID in [uuid.lower() for uuid in advertisement.service_uuids]
            ]
            match = max(matches, key=lambda item: item[1].rssi) if matches else None
            async with self._lock:
                if match:
                    device, advertisement = match
                    self._state = {
                        "detected": True,
                        "name": device.name or advertisement.local_name,
                        "address": device.address,
                        "rssi_dbm": advertisement.rssi,
                        "service_uuids": advertisement.service_uuids,
                        "last_seen_at": time.time(),
                        "connection_verified": self._state["connection_verified"],
                        "last_connected_at": self._state["last_connected_at"],
                        "devices": nearby,
                        "error": None,
                    }
                else:
                    self._state["detected"] = False
                    self._state["name"] = None
                    self._state["address"] = None
                    self._state["rssi_dbm"] = None
                    self._state["service_uuids"] = []
                    self._state["devices"] = nearby
                    self._state["error"] = None
                return dict(self._state)
        except Exception as error:  # BLE backends expose platform-specific errors.
            async with self._lock:
                self._state["detected"] = False
                self._state["error"] = str(error)
                return dict(self._state)

    async def verify_connection(self) -> dict[str, Any]:
        async with self._operation_lock:
            async with self._lock:
                address = self._state["address"] if self._state["detected"] else None
            if not address:
                scan_result = await self._scan(6.0)
                address = scan_result["address"] if scan_result["detected"] else None
            if not address:
                return {"verified": False, "error": "LUMNI BLE advertisement was not detected"}
            try:
                async with BleakClient(address, timeout=12.0) as client:
                    payload = await client.read_gatt_char(LUMNI_TEST_STATUS_UUID)
                connected_at = time.time()
                async with self._lock:
                    self._state["connection_verified"] = True
                    self._state["last_connected_at"] = connected_at
                    self._state["error"] = None
                return {
                    "verified": True,
                    "address": address,
                    "status": payload.decode("utf-8", errors="replace"),
                    "connected_at": connected_at,
                }
            except Exception as error:  # BLE backends expose platform-specific errors.
                async with self._lock:
                    self._state["connection_verified"] = False
                    self._state["error"] = str(error)
                return {"verified": False, "address": address, "error": str(error)}
    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self._state)
