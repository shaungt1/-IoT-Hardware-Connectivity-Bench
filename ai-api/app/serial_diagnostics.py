from __future__ import annotations

import json
import threading
import time
from typing import Any

import serial


SUPPORTED_SENSOR_USB_IDS = {("2341", "805A"), ("2341", "005A")}
DIAGNOSTIC_IDS = {"lsm9ds1", "apds9960", "hts221", "lps22hb", "mp34dt05", "i2c"}
_SERIAL_LOCKS: dict[str, threading.Lock] = {}
_SERIAL_LOCKS_GUARD = threading.Lock()


def _port_lock(port: str) -> threading.Lock:
    with _SERIAL_LOCKS_GUARD:
        return _SERIAL_LOCKS.setdefault(port.upper(), threading.Lock())


def supports_sensor_diagnostics(profile: dict[str, Any]) -> bool:
    return (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper()) in SUPPORTED_SENSOR_USB_IDS


def _payload(line: str, prefixes: tuple[str, ...]) -> dict[str, Any] | None:
    for prefix in prefixes:
        if not line.startswith(prefix):
            continue
        try:
            value = json.loads(line[len(prefix):].strip())
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None
    return None


def _wait_for(stream: serial.Serial, prefixes: tuple[str, ...], timeout: float) -> dict[str, Any] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = stream.readline().decode("utf-8", "replace").strip()
        if not line:
            continue
        parsed = _payload(line, prefixes)
        if parsed is not None:
            return parsed
    return None


def probe_sensor_diagnostics(port: str, timeout: float = 3.2) -> dict[str, Any]:
    try:
        with _port_lock(port):
            with serial.Serial(port, 115200, timeout=0.25, write_timeout=1) as stream:
                manifest = _wait_for(stream, ("BENCH_READY", "BENCH_MANIFEST"), timeout)
    except (OSError, serial.SerialException) as error:
        return {"ready": False, "error": str(error)}
    if not manifest or manifest.get("protocol") != "iot-bench-sensors/1":
        return {"ready": False, "error": "Compatible sensor diagnostic firmware did not identify itself"}
    return {"ready": True, **manifest}


def run_sensor_diagnostic(port: str, sensor_id: str, timeout: float = 4.0) -> dict[str, Any]:
    if sensor_id not in DIAGNOSTIC_IDS:
        raise ValueError("Test is not in the diagnostic allowlist")
    try:
        with _port_lock(port):
            with serial.Serial(port, 115200, timeout=0.25, write_timeout=1) as stream:
                manifest = _wait_for(stream, ("BENCH_READY", "BENCH_MANIFEST"), 3.2)
                if not manifest or manifest.get("protocol") != "iot-bench-sensors/1":
                    raise ValueError("Compatible sensor diagnostic firmware is not active")
                stream.write(f"TEST {sensor_id}\n".encode("ascii"))
                stream.flush()
                result = _wait_for(stream, ("BENCH_RESULT", "BENCH_ERROR"), timeout)
    except (OSError, serial.SerialException) as error:
        raise ValueError(f"Could not open diagnostic serial port: {error}") from error
    if result is None:
        raise ValueError("Diagnostic firmware did not return a sensor result")
    return result
