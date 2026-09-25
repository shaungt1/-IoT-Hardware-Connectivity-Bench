from __future__ import annotations

import ast
import ctypes
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import psutil
import serial

from .base import AdapterManifest


SUPPORTED_USB_IDS = {("239A", "8023")}
_PROBE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_SERIAL_LOCKS: dict[str, threading.Lock] = {}
_LOCK_GUARD = threading.Lock()
_VOLUME_LOCK = threading.Lock()

I2C_ADDRESS_HINTS: dict[int, list[str]] = {
    0x18: ["LIS3DH/LIS2DH accelerometer", "MCP9808 temperature sensor"],
    0x19: ["LIS3DH/LIS2DH accelerometer", "MCP9808 temperature sensor"],
    0x1C: ["MMA8451 or compatible accelerometer"],
    0x1D: ["MMA8451, ADXL345, or compatible accelerometer"],
    0x28: ["BNO055 absolute orientation sensor"],
    0x29: ["VL53L0X distance or TSL2591 light sensor"],
    0x39: ["APDS9960 gesture/proximity or VEML light sensor"],
    0x3C: ["SSD1306/SH110x display candidate"],
    0x3D: ["SSD1306/SH110x display candidate"],
    0x40: ["HTU21D/SHT2x sensor or PCA9685 controller"],
    0x44: ["SHT3x temperature/humidity sensor"],
    0x45: ["SHT3x temperature/humidity sensor"],
    0x48: ["ADS1x15 ADC or TMP102 temperature sensor"],
    0x53: ["ADXL345 accelerometer"],
    0x68: ["MPU/ICM motion sensor or DS3231 RTC"],
    0x69: ["MPU/ICM motion sensor"],
    0x76: ["BMP/BME pressure or environmental sensor"],
    0x77: ["BMP/BME pressure or environmental sensor"],
}

FEATHER_M0_PINS = [
    {"name": "D0", "aliases": ["RX"], "group": "UART / GPIO", "functions": ["GPIO", "UART RX", "analog input"]},
    {"name": "D1", "aliases": ["TX"], "group": "UART / GPIO", "functions": ["GPIO", "UART TX", "analog input"]},
    {"name": "SDA", "aliases": [], "group": "I2C", "functions": ["I2C data", "GPIO"]},
    {"name": "SCL", "aliases": [], "group": "I2C", "functions": ["I2C clock", "GPIO"]},
    {"name": "SCK", "aliases": [], "group": "SPI", "functions": ["SPI clock", "GPIO"]},
    {"name": "MOSI", "aliases": [], "group": "SPI", "functions": ["SPI controller out", "GPIO"]},
    {"name": "MISO", "aliases": [], "group": "SPI", "functions": ["SPI controller in", "GPIO"]},
    {"name": "D5", "aliases": [], "group": "Digital", "functions": ["GPIO", "PWM", "interrupt"]},
    {"name": "D6", "aliases": [], "group": "Digital", "functions": ["GPIO", "PWM", "interrupt"]},
    {"name": "D9", "aliases": ["A7"], "group": "Digital / analog", "functions": ["GPIO", "PWM", "battery-divider analog input"]},
    {"name": "D10", "aliases": [], "group": "Digital", "functions": ["GPIO", "PWM", "interrupt"]},
    {"name": "D11", "aliases": [], "group": "Digital", "functions": ["GPIO", "PWM", "interrupt"]},
    {"name": "D12", "aliases": [], "group": "Digital", "functions": ["GPIO", "PWM", "interrupt"]},
    {"name": "D13", "aliases": ["LED"], "group": "Digital", "functions": ["GPIO", "PWM", "red status LED"]},
    {"name": "A0", "aliases": ["DAC0"], "group": "Analog", "functions": ["analog input", "true analog output", "GPIO"]},
    {"name": "A1", "aliases": [], "group": "Analog", "functions": ["analog input", "GPIO"]},
    {"name": "A2", "aliases": [], "group": "Analog", "functions": ["analog input", "GPIO"]},
    {"name": "A3", "aliases": [], "group": "Analog", "functions": ["analog input", "GPIO"]},
    {"name": "A4", "aliases": [], "group": "Analog", "functions": ["analog input", "GPIO"]},
    {"name": "A5", "aliases": [], "group": "Analog", "functions": ["analog input", "GPIO"]},
    {"name": "NEOPIXEL", "aliases": ["D8"], "group": "Onboard", "functions": ["single RGB NeoPixel"]},
    {"name": "SWDIO", "aliases": [], "group": "Debug", "functions": ["SWD data"]},
    {"name": "SWCLK", "aliases": [], "group": "Debug", "functions": ["SWD clock"]},
    {"name": "RST", "aliases": [], "group": "Control", "functions": ["hardware reset"]},
    {"name": "USB", "aliases": [], "group": "Power", "functions": ["USB supply"]},
    {"name": "BAT", "aliases": [], "group": "Power", "functions": ["LiPo battery"]},
    {"name": "3V", "aliases": [], "group": "Power", "functions": ["3.3 V regulated output"]},
    {"name": "EN", "aliases": [], "group": "Power", "functions": ["3.3 V regulator enable"]},
    {"name": "GND", "aliases": [], "group": "Power", "functions": ["ground"]},
]


def _port_lock(port: str) -> threading.Lock:
    with _LOCK_GUARD:
        return _SERIAL_LOCKS.setdefault(port.upper(), threading.Lock())


def _volume_label(root: str) -> str:
    if os.name != "nt":
        return ""
    label = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root), label, len(label), None, None, None, None, 0
    )
    return label.value if ok else ""


def _source_imports(path: Path) -> list[str]:
    try:
        # CircuitPython rewrites and remounts code.py during reloads. Parse a
        # bounded snapshot so a transient or malformed file never breaks host
        # inventory for the whole bench.
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            source = handle.read(256 * 1024)
        tree = ast.parse(source)
    except (OSError, SyntaxError, ValueError, SystemError, RecursionError):
        return []
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return sorted(imports)


def _find_volume(profile: dict[str, Any], attempts: int = 1) -> dict[str, Any] | None:
    with _VOLUME_LOCK:
        for attempt in range(max(1, attempts)):
            for partition in psutil.disk_partitions(all=True):
                root = partition.mountpoint
                try:
                    label = _volume_label(root)
                    if label.upper() != "CIRCUITPY":
                        continue
                    volume = Path(root)
                    boot_path = volume / "boot_out.txt"
                    try:
                        boot = boot_path.read_text(encoding="utf-8", errors="replace")[:8192].strip()
                    except OSError:
                        boot = ""
                    board_name = str(profile.get("name") or "").lower()
                    if board_name and "feather" in board_name and "feather" not in boot.lower():
                        continue
                    usage = psutil.disk_usage(root)
                    files = []
                    try:
                        files = sorted(item.name for item in volume.iterdir() if item.name not in {"System Volume Information", ".Trashes", ".fseventsd"})
                    except OSError:
                        pass
                    code_files = [name for name in ("code.py", "main.py") if (volume / name).is_file()]
                    imports = sorted({module for name in code_files for module in _source_imports(volume / name)})
                    libraries = []
                    lib = volume / "lib"
                    if lib.is_dir():
                        try:
                            libraries = sorted(item.name for item in lib.iterdir())
                        except OSError:
                            pass
                    match = re.search(r"Adafruit CircuitPython\s+([^;]+).*?;\s*(.+?)(?:\s+with\s+(.+))?$", boot)
                    return {
                        "path": root,
                        "label": label,
                        "filesystem": partition.fstype,
                        "boot": boot,
                        "version": match.group(1).strip() if match else None,
                        "board": match.group(2).strip() if match else None,
                        "mcu": match.group(3).strip() if match and match.group(3) else None,
                        "size_bytes": usage.total,
                        "free_bytes": usage.free,
                        "files": files,
                        "code_files": code_files,
                        "imports": imports,
                        "libraries": libraries,
                    }
                except OSError:
                    # CircuitPython briefly unmounts and remounts after a soft
                    # reload. Treat that as a transient device state.
                    continue
            if attempt + 1 < attempts:
                time.sleep(0.5)
    return None


def _read_until(stream: serial.Serial, marker: bytes, timeout: float) -> bytes:
    deadline = time.monotonic() + timeout
    data = bytearray()
    while time.monotonic() < deadline:
        waiting = stream.in_waiting
        if waiting:
            data.extend(stream.read(waiting))
            if marker in data:
                return bytes(data)
        else:
            time.sleep(0.02)
    raise ValueError(f"CircuitPython did not return {marker.decode('ascii', 'replace')}")


def _parse_probe(output: str) -> dict[str, Any]:
    values: dict[str, str] = {}
    for line in output.replace("\r", "").split("\n"):
        if line.startswith("__BENCH_") and "=" in line:
            key, value = line.removeprefix("__BENCH_").split("=", 1)
            values[key] = value.strip()
    addresses = [int(value, 16) for value in values.get("I2C", "").split(",") if re.fullmatch(r"[0-9A-Fa-f]{2}", value)]
    pins = [value for value in values.get("PINS", "").split(",") if value]
    return {
        "ready": values.get("DONE") == "1",
        "runtime": values.get("RUNTIME"),
        "board_id": values.get("BOARD"),
        "cpu_frequency_hz": int(values["FREQUENCY"]) if values.get("FREQUENCY", "").isdigit() else None,
        "free_heap_bytes": int(values["HEAP"]) if values.get("HEAP", "").isdigit() else None,
        "pins": pins,
        "i2c_addresses": addresses,
        "i2c_seen_addresses": [int(value, 16) for value in values.get("I2C_SEEN", "").split(",") if re.fullmatch(r"[0-9A-Fa-f]{2}", value)],
        "i2c_error": values.get("I2C_ERROR"),
    }


def _deep_probe(port: str) -> dict[str, Any]:
    script = """import board, gc, sys, time
print('__BENCH_RUNTIME=' + str(sys.implementation))
print('__BENCH_BOARD=' + str(getattr(board, 'board_id', 'unknown')))
print('__BENCH_PINS=' + ','.join([name for name in dir(board) if not name.startswith('_')]))
print('__BENCH_HEAP=' + str(gc.mem_free()))
try:
 import microcontroller
 print('__BENCH_FREQUENCY=' + str(getattr(microcontroller.cpu, 'frequency', '')))
except Exception as error:
 print('__BENCH_CPU_ERROR=' + repr(error))
try:
 import busio
 i2c = busio.I2C(board.SCL, board.SDA)
 while not i2c.try_lock():
  pass
 scans = []
 for scan_index in range(3):
  scans.append(i2c.scan())
  time.sleep(0.05)
 addresses = [address for address in scans[0] if all(address in sample for sample in scans[1:])]
 seen = sorted(set([address for sample in scans for address in sample]))
 i2c.unlock()
 i2c.deinit()
 print('__BENCH_I2C=' + ','.join(['%02X' % address for address in addresses]))
 print('__BENCH_I2C_SEEN=' + ','.join(['%02X' % address for address in seen]))
except Exception as error:
 print('__BENCH_I2C_ERROR=' + repr(error))
print('__BENCH_DONE=1')
"""
    try:
        with _port_lock(port):
            with serial.Serial(port, 115200, timeout=0.1, write_timeout=2) as stream:
                time.sleep(0.3)
                stream.reset_input_buffer()
                # Stop the user program, leave any friendly prompt, then enter
                # CircuitPython's raw REPL so stdout has unambiguous framing.
                stream.write(b"\x03\x03\x02")
                stream.flush()
                _read_until(stream, b">>> ", 6.0)
                stream.write(b"\x01")
                stream.flush()
                _read_until(stream, b"raw REPL; CTRL-B to exit\r\n>", 6.0)
                stream.write(script.encode("utf-8") + b"\x04")
                stream.flush()
                output = _read_until(stream, b"\x04>", 12.0)
                # Return to the friendly REPL and soft-reload the existing
                # program. No file on CIRCUITPY is created or modified.
                stream.write(b"\x02\x04")
                stream.flush()
    except (OSError, serial.SerialException) as error:
        raise ValueError(f"Could not open CircuitPython serial port: {error}") from error
    decoded = output.decode("utf-8", "replace")
    if decoded.startswith("OK"):
        decoded = decoded[2:]
    parsed = _parse_probe(decoded)
    if not parsed.get("ready"):
        raise ValueError("CircuitPython probe did not complete")
    _PROBE_CACHE[port.upper()] = (time.time(), parsed)
    return parsed


def _peripherals(addresses: list[int]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"i2c-{address:02x}",
            "name": f"I2C device at 0x{address:02X}",
            "bus": "I2C",
            "status": "detected",
            "address": f"0x{address:02X}",
            "candidates": I2C_ADDRESS_HINTS.get(address, ["Unknown I2C peripheral; signature probe required"]),
            "source": "CircuitPython controlled bus scan",
        }
        for address in addresses
    ]


class CircuitPythonAdapter:
    adapter_id = "circuitpython"
    name = "CircuitPython USB runtime"
    manifest = AdapterManifest(
        id=adapter_id,
        name=name,
        version="1.0",
        transports=("USB serial", "mounted storage"),
        families=("CircuitPython", "SAMD", "RP2040", "nRF52", "ESP32"),
        inspection_modes=("passive", "disruptive"),
        timeout_seconds=20,
        safety="Reads mounted metadata passively; REPL probes are opt-in and reload the existing program without writing files.",
    )

    def supports(self, profile: dict[str, Any]) -> bool:
        identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
        return profile.get("kind") == "serial" and identity in SUPPORTED_USB_IDS

    def inspect_passive(self, profile: dict[str, Any]) -> dict[str, Any]:
        volume = _find_volume(profile)
        cached = _PROBE_CACHE.get(str(profile.get("device", "")).upper())
        probe = cached[1] if cached and time.time() - cached[0] < 600 else None
        pins = []
        live_names = set(probe.get("pins", [])) if probe else set()
        for item in FEATHER_M0_PINS:
            pin = dict(item)
            pin["status"] = "verified" if pin["name"] in live_names or any(alias in live_names for alias in pin["aliases"]) else "expected"
            pin["source"] = "CircuitPython runtime" if pin["status"] == "verified" else "Adafruit board pinout"
            pins.append(pin)
        evidence = []
        if volume:
            evidence.extend([
                {"source": f"{volume['label']} volume {volume['path']}", "claim": f"CircuitPython {volume.get('version') or 'runtime'} storage mounted", "status": "verified"},
                {"source": "boot_out.txt", "claim": volume.get("boot") or "CircuitPython boot metadata present", "status": "verified"},
            ])
        if probe:
            stable_count = len(probe.get("i2c_addresses", []))
            seen_count = len(probe.get("i2c_seen_addresses", []))
            evidence.append({"source": "controlled CircuitPython REPL probe", "claim": f"Runtime reported {len(probe.get('pins', []))} board names and {stable_count} stable I2C address(es) across three samples", "status": "verified"})
            if seen_count > stable_count:
                evidence.append({"source": "three-sample I2C stability check", "claim": f"Ignored {seen_count - stable_count} transient address response(s) as unverified bus noise", "status": "detected"})
        tests = [
            {"id": "circuitpython_storage", "name": "Verify CIRCUITPY storage and boot metadata", "risk": "read-only", "available": bool(volume), "description": "Reads mounted volume metadata, code filenames, imports, and library names without changing files."},
            {"id": "circuitpython_runtime_probe", "action": "deep_probe", "name": "Deep probe CircuitPython runtime and pins", "risk": "disruptive", "available": True, "description": "Temporarily interrupts the running script, inventories runtime pin names and memory, then reloads the existing program."},
            {"id": "circuitpython_i2c_scan", "action": "bus_scan", "name": "Scan external I2C peripherals", "risk": "disruptive", "available": True, "description": "Temporarily enters the REPL and scans the exposed SDA/SCL bus. Address matches are candidates until a signature is verified."},
        ]
        telemetry = {
            "firmware": f"CircuitPython {volume.get('version')}" if volume and volume.get("version") else "CircuitPython",
            "runtime_adapter": self.name,
            "storage_mount": volume.get("path") if volume else None,
            "storage_total_bytes": volume.get("size_bytes") if volume else None,
            "storage_free_bytes": volume.get("free_bytes") if volume else None,
            "code_files": volume.get("code_files", []) if volume else [],
            "imports": volume.get("imports", []) if volume else [],
            "libraries": volume.get("libraries", []) if volume else [],
            "free_heap_bytes": probe.get("free_heap_bytes") if probe else None,
            "cpu_frequency_hz": probe.get("cpu_frequency_hz") if probe else None,
        }
        return {
            "adapter": {"id": self.adapter_id, "name": self.name, "mode": "passive storage plus opt-in serial probe"},
            "telemetry": telemetry,
            "evidence": evidence,
            "tests": tests,
            "pins": pins,
            "attached_peripherals": _peripherals(probe.get("i2c_addresses", [])) if probe else [],
            "probe": probe,
            "volume": volume,
        }

    def run_test(self, profile: dict[str, Any], test_id: str) -> dict[str, Any] | None:
        if test_id == "circuitpython_storage":
            volume = _find_volume(profile, attempts=8)
            return {
                "passed": bool(volume),
                "summary": f"CIRCUITPY storage verified at {volume['path']}." if volume else "No matching CIRCUITPY volume is mounted.",
                "evidence": volume,
            }
        if test_id in {"circuitpython_runtime_probe", "circuitpython_i2c_scan"}:
            result = _deep_probe(str(profile["device"]))
            count = len(result.get("i2c_addresses", []))
            transient = max(0, len(result.get("i2c_seen_addresses", [])) - count)
            summary = f"CircuitPython runtime returned {len(result.get('pins', []))} board names and {count} stable I2C address(es) across three samples."
            if transient:
                summary += f" {transient} transient response(s) were ignored."
            if test_id == "circuitpython_i2c_scan":
                summary = f"External I2C scan completed with {count} stable responding address(es) across three samples."
                if transient:
                    summary += f" {transient} transient response(s) were ignored."
            return {"passed": True, "summary": summary, "evidence": result}
        return None
