from __future__ import annotations

import time
from typing import Any

import serial

from .base import AdapterManifest


FIRMATA_USB_VIDS = {"2341", "2A03"}
START_SYSEX = 0xF0
END_SYSEX = 0xF7
REPORT_FIRMWARE = 0x79


def _query_firmata(port: str, timeout: float = 3.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    try:
        with serial.Serial(port, 57600, timeout=0.1, write_timeout=1) as stream:
            time.sleep(0.15)
            stream.reset_input_buffer()
            stream.write(bytes((START_SYSEX, REPORT_FIRMWARE, END_SYSEX)))
            stream.flush()
            buffer = bytearray()
            while time.monotonic() < deadline:
                chunk = stream.read(256)
                if chunk:
                    buffer.extend(chunk)
                start = buffer.find(bytes((START_SYSEX, REPORT_FIRMWARE)))
                end = buffer.find(bytes((END_SYSEX,)), start + 2) if start >= 0 else -1
                if start < 0 or end < 0:
                    continue
                payload = buffer[start + 2:end]
                if len(payload) < 2:
                    break
                major, minor = payload[0], payload[1]
                name_bytes = payload[2:]
                name = "".join(chr(name_bytes[index] | (name_bytes[index + 1] << 7)) for index in range(0, len(name_bytes) - 1, 2))
                return {"ready": True, "protocol": "firmata", "version": f"{major}.{minor}", "firmware": name.strip() or "Unspecified Firmata firmware"}
    except (OSError, serial.SerialException) as error:
        return {"ready": False, "error": str(error)}
    return {"ready": False, "error": "No Firmata REPORT_FIRMWARE response was received"}


class FirmataAdapter:
    adapter_id = "firmata"
    name = "Firmata runtime"
    manifest = AdapterManifest(
        id=adapter_id,
        name=name,
        version="1.0",
        transports=("USB serial",),
        families=("Arduino-compatible Firmata targets",),
        inspection_modes=("passive", "disruptive"),
        timeout_seconds=4.0,
        safety="USB identity only marks a Firmata candidate. The opt-in handshake opens the serial port, which may reset the board, and sends only the Firmata REPORT_FIRMWARE query.",
    )

    def supports(self, profile: dict[str, Any]) -> bool:
        return profile.get("kind") == "serial" and str(profile.get("vid") or "").upper() in FIRMATA_USB_VIDS

    def inspect_passive(self, profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter": {"id": self.adapter_id, "name": self.name, "mode": "candidate; opt-in handshake required"},
            "evidence": [{"source": "USB vendor identity", "claim": "Arduino-compatible serial target; Firmata runtime is not yet verified", "status": "detected"}],
            "tests": [{
                "id": "firmata_handshake",
                "action": "deep_probe",
                "name": "Identify Firmata runtime",
                "risk": "disruptive",
                "available": True,
                "description": "Opens the serial interface, which may reset the board, and sends the standard REPORT_FIRMWARE query. No pin is driven.",
            }],
        }

    def run_test(self, profile: dict[str, Any], test_id: str) -> dict[str, Any] | None:
        if test_id != "firmata_handshake":
            return None
        result = _query_firmata(str(profile.get("device") or ""))
        return {
            "passed": bool(result.get("ready")),
            "summary": f"Firmata {result.get('version')} runtime identified: {result.get('firmware')}." if result.get("ready") else str(result.get("error")),
            "evidence": result,
        }
