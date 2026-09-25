from __future__ import annotations

import re
import subprocess
import threading
import time
from typing import Any

from .base import AdapterManifest
from ..tool_paths import tool_executable


SERIAL_BRIDGE_USB_IDS = {
    ("10C4", "EA60"),  # Silicon Labs CP210x
    ("1A86", "7523"),  # WCH CH340/CH341
    ("1A86", "5523"),
    ("0403", "6001"),  # FTDI FT232
    ("303A", "1001"),  # Espressif native USB serial/JTAG
}

_PROBE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_SERIAL_LOCKS: dict[str, threading.Lock] = {}
_LOCK_GUARD = threading.Lock()


NODEMCU_ESP8266_PINS = [
    {"name": "A0", "aliases": ["ADC0"], "group": "Analog", "functions": ["10-bit analog input"]},
    {"name": "D0", "aliases": ["GPIO16", "WAKE"], "group": "Digital", "functions": ["GPIO", "deep-sleep wake"]},
    {"name": "D1", "aliases": ["GPIO5", "SCL"], "group": "I2C / GPIO", "functions": ["GPIO", "I2C clock", "PWM"]},
    {"name": "D2", "aliases": ["GPIO4", "SDA"], "group": "I2C / GPIO", "functions": ["GPIO", "I2C data", "PWM"]},
    {"name": "D3", "aliases": ["GPIO0", "FLASH"], "group": "Boot / GPIO", "functions": ["GPIO", "boot strap", "flash button"]},
    {"name": "D4", "aliases": ["GPIO2", "LED_BUILTIN"], "group": "Boot / GPIO", "functions": ["GPIO", "boot strap", "onboard LED"]},
    {"name": "D5", "aliases": ["GPIO14", "SCLK"], "group": "SPI / GPIO", "functions": ["GPIO", "SPI clock", "PWM"]},
    {"name": "D6", "aliases": ["GPIO12", "MISO"], "group": "SPI / GPIO", "functions": ["GPIO", "SPI controller input", "PWM"]},
    {"name": "D7", "aliases": ["GPIO13", "MOSI"], "group": "SPI / GPIO", "functions": ["GPIO", "SPI controller output", "PWM"]},
    {"name": "D8", "aliases": ["GPIO15", "CS"], "group": "Boot / SPI", "functions": ["GPIO", "SPI chip select", "boot strap"]},
    {"name": "RX", "aliases": ["GPIO3", "RXD0"], "group": "UART / GPIO", "functions": ["UART receive", "GPIO"]},
    {"name": "TX", "aliases": ["GPIO1", "TXD0"], "group": "UART / GPIO", "functions": ["UART transmit", "GPIO"]},
    {"name": "SD3", "aliases": ["GPIO10"], "group": "Internal flash", "functions": ["SPI flash data; normally unavailable"]},
    {"name": "SD2", "aliases": ["GPIO9"], "group": "Internal flash", "functions": ["SPI flash data; normally unavailable"]},
    {"name": "SD1", "aliases": ["GPIO8"], "group": "Internal flash", "functions": ["SPI flash data; reserved"]},
    {"name": "CMD", "aliases": ["GPIO11"], "group": "Internal flash", "functions": ["SPI flash command; reserved"]},
    {"name": "SD0", "aliases": ["GPIO7"], "group": "Internal flash", "functions": ["SPI flash data; reserved"]},
    {"name": "CLK", "aliases": ["GPIO6"], "group": "Internal flash", "functions": ["SPI flash clock; reserved"]},
    {"name": "EN", "aliases": ["CH_PD"], "group": "Control", "functions": ["chip enable"]},
    {"name": "RST", "aliases": [], "group": "Control", "functions": ["hardware reset"]},
    {"name": "VIN", "aliases": [], "group": "Power", "functions": ["external supply input"]},
    {"name": "3V3", "aliases": [], "group": "Power", "functions": ["3.3 V regulated rail"]},
    {"name": "GND", "aliases": [], "group": "Power", "functions": ["ground"]},
]


def _port_lock(port: str) -> threading.Lock:
    with _LOCK_GUARD:
        return _SERIAL_LOCKS.setdefault(port.upper(), threading.Lock())


def _esptool_available() -> bool:
    return tool_executable("esptool") is not None


def _field(output: str, label: str) -> str | None:
    match = re.search(rf"^{re.escape(label)}:\s*(.+?)\s*$", output, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None


def _parse_probe(output: str) -> dict[str, Any]:
    chip = _field(output, "Chip type")
    flash_size = _field(output, "Detected flash size")
    if not chip:
        raise ValueError("The serial target did not return an Espressif ROM identity")
    return {
        "ready": True,
        "chip": chip,
        "features": [item.strip() for item in (_field(output, "Features") or "").split(",") if item.strip()],
        "crystal_frequency": _field(output, "Crystal frequency"),
        "mac_address": _field(output, "MAC"),
        "flash_manufacturer": _field(output, "Manufacturer"),
        "flash_device": _field(output, "Device"),
        "flash_size": flash_size,
        "raw_summary": output,
    }


def _probe_target(port: str) -> dict[str, Any]:
    if not _esptool_available():
        raise ValueError("esptool is not installed in the bench environment")
    executable = tool_executable("esptool")
    if not executable:
        raise ValueError("esptool is not installed in the bench tool environment")
    command = [
        executable,
        "--chip",
        "auto",
        "--port",
        port,
        "--baud",
        "115200",
        "--before",
        "default-reset",
        "--after",
        "hard-reset",
        "--no-stub",
        "flash-id",
    ]
    try:
        with _port_lock(port):
            result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Espressif ROM probe could not run: {error}") from error
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0:
        detail = next((line.strip() for line in reversed(output.splitlines()) if line.strip()), "No ROM response")
        raise ValueError(f"No Espressif target answered behind {port}: {detail}")
    parsed = _parse_probe(output)
    _PROBE_CACHE[port.upper()] = (time.time(), parsed)
    return parsed


def _bridge_name(profile: dict[str, Any]) -> str:
    identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
    if identity == ("10C4", "EA60"):
        return "Silicon Labs CP210x USB-to-UART bridge"
    if identity[0] == "1A86":
        return "WCH USB-to-UART bridge"
    if identity == ("0403", "6001"):
        return "FTDI USB-to-UART bridge"
    return profile.get("name") or "USB serial interface"


def _esp8266_identity(profile: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    flash_label = f"{probe.get('flash_size') or 'SPI'} flash"
    return {
        "model": "ESP8266 development board via USB-to-UART",
        "family": "Espressif ESP8266",
        "classification": "microcontroller_board",
        "manufacturer": "Espressif Systems",
        "mcu": probe["chip"],
        "architecture": "Tensilica L106 32-bit RISC",
        "runtime": "Firmware dependent",
        "confidence": 0.97,
        "candidates": [
            "NodeMCU ESP8266 development board (ESP-12E/F)",
            "Generic ESP8266 development board",
        ],
        "capabilities": [
            {"id": "usb_uart", "name": "USB-to-UART transport", "status": "verified", "source": "Host USB enumeration"},
            {"id": "wifi_24", "name": "2.4 GHz Wi-Fi", "status": "verified", "source": "Espressif ROM chip feature report"},
            {"id": "uart", "name": "UART", "status": "verified", "source": "Espressif ROM communication"},
            {"id": "gpio", "name": "GPIO", "status": "expected", "source": "ESP8266EX capability"},
            {"id": "i2c", "name": "I2C via software controller", "status": "expected", "source": "ESP8266 board profile"},
            {"id": "spi", "name": "SPI", "status": "expected", "source": "ESP8266EX capability"},
            {"id": "adc", "name": "10-bit ADC", "status": "expected", "source": "ESP8266EX capability"},
        ],
        "components": [
            {"id": "esp8266ex", "name": probe["chip"], "type": "microcontroller and Wi-Fi SoC", "status": "verified", "source": "Espressif ROM handshake"},
            {"id": "spi_flash", "name": flash_label, "type": "storage", "bus": "SPI", "status": "verified", "source": f"JEDEC manufacturer {probe.get('flash_manufacturer') or '--'}, device {probe.get('flash_device') or '--'}"},
            {"id": "usb_uart_bridge", "name": _bridge_name(profile), "type": "USB-to-UART bridge", "bus": "USB / UART", "status": "verified", "source": "Host USB descriptor"},
            {"id": "esp12_module", "name": "ESP-12E/ESP-12F module", "type": "radio module", "status": "declared", "source": "NodeMCU board profile and supplied board photos", "variant": "NodeMCU ESP8266 development board (ESP-12E/F)"},
            {"id": "ams1117", "name": "AMS1117 3.3 V regulator", "type": "power regulator", "status": "declared", "source": "Supplied board photo and NodeMCU board profile", "variant": "NodeMCU ESP8266 development board (ESP-12E/F)"},
        ],
        "resources": [
            {"title": "ESP8266EX documentation", "url": "https://www.espressif.com/en/products/socs/esp8266ex/resources", "provider": "Espressif", "kind": "documentation"},
            {"title": "esptool ESP8266 documentation", "url": "https://docs.espressif.com/projects/esptool/en/latest/esp8266/", "provider": "Espressif", "kind": "tool documentation"},
        ],
    }


class EspressifRomAdapter:
    adapter_id = "espressif_rom"
    name = "Espressif ROM target probe"
    manifest = AdapterManifest(
        id=adapter_id,
        name=name,
        version="1.0",
        transports=("USB serial", "USB-to-UART"),
        families=("ESP8266", "ESP32", "ESP32-S2", "ESP32-S3", "ESP32-C3", "ESP32-C6"),
        inspection_modes=("disruptive",),
        timeout_seconds=20,
        safety="Opt-in ROM handshake may reset the target but uses no erase, write, or flash command.",
    )

    def supports(self, profile: dict[str, Any]) -> bool:
        identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
        return profile.get("kind") == "serial" and identity in SERIAL_BRIDGE_USB_IDS

    def inspect_passive(self, profile: dict[str, Any]) -> dict[str, Any]:
        port = str(profile.get("device", "")).upper()
        cached = _PROBE_CACHE.get(port)
        probe = cached[1] if cached and time.time() - cached[0] < 1800 else None
        layers = [
            {
                "id": "host_interface",
                "layer": "Host interface",
                "name": _bridge_name(profile),
                "status": "verified",
                "source": f"USB {profile.get('vid') or '----'}:{profile.get('pid') or '----'} on {profile.get('device')}",
            }
        ]
        identity = None
        pins: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        if probe and str(probe.get("chip", "")).upper().startswith("ESP8266"):
            identity = _esp8266_identity(profile, probe)
            layers.extend(
                [
                    {"id": "processor", "layer": "Target processor", "name": probe["chip"], "status": "verified", "source": "Espressif ROM handshake"},
                    {"id": "radio", "layer": "Integrated radio", "name": "2.4 GHz Wi-Fi", "status": "verified", "source": "ROM feature report; active broadcast requires firmware telemetry"},
                    {"id": "flash", "layer": "Program storage", "name": f"{probe.get('flash_size') or 'SPI'} flash", "status": "verified", "source": f"JEDEC {probe.get('flash_manufacturer') or '--'}:{probe.get('flash_device') or '--'}"},
                    {"id": "board", "layer": "Board profile", "name": "NodeMCU ESP8266 / generic ESP8266 candidate", "status": "detected", "source": "Processor plus USB-bridge topology; select the exact carrier model"},
                ]
            )
            evidence.append({"source": "Espressif ROM handshake", "claim": f"{probe['chip']} answered on {profile.get('device')}", "status": "verified"})
            evidence.append({"source": "SPI flash JEDEC query", "claim": f"{probe.get('flash_size') or 'SPI flash'} detected", "status": "verified"})
            pins = [
                {**pin, "status": "expected", "source": "NodeMCU ESP8266 candidate pin map; verify exact board model"}
                for pin in NODEMCU_ESP8266_PINS
            ]
        tests = [
            {
                "id": "esp_rom_probe",
                "action": "deep_probe",
                "name": "Identify processor and SPI flash behind UART",
                "risk": "disruptive",
                "available": _esptool_available(),
                "description": "Resets the serial target into its ROM loader, reads the chip and flash identity without writing storage, then restarts the existing firmware.",
            }
        ]
        if identity:
            tests.append(
                {
                    "id": "esp_wifi_capability",
                    "action": "wireless_test",
                    "name": "Verify ESP8266 2.4 GHz Wi-Fi capability",
                    "risk": "read-only",
                    "available": True,
                    "description": "Confirms that the processor identified by its ROM includes 2.4 GHz Wi-Fi. It does not claim that the current firmware is broadcasting or connected.",
                }
            )
        return {
            "adapter": {"id": self.adapter_id, "name": self.name, "mode": "opt-in ROM identification"},
            "identity": identity,
            "identity_layers": layers,
            "telemetry": {
                "firmware": "Firmware dependent" if probe else None,
                "processor": probe.get("chip") if probe else None,
                "flash_size": probe.get("flash_size") if probe else None,
                "cpu_frequency": next((item for item in probe.get("features", []) if "MHz" in item), None) if probe else None,
                "radio_capabilities": ["Wi-Fi 2.4 GHz"] if identity else [],
            },
            "evidence": evidence,
            "tests": tests,
            "pins": pins,
            "attached_peripherals": [],
            "probe": probe,
        }

    def run_test(self, profile: dict[str, Any], test_id: str) -> dict[str, Any] | None:
        port = str(profile.get("device", ""))
        if test_id == "esp_rom_probe":
            result = _probe_target(port)
            return {
                "passed": True,
                "summary": f"{result['chip']} and {result.get('flash_size') or 'SPI flash'} verified behind {_bridge_name(profile)}.",
                "evidence": result,
            }
        if test_id == "esp_wifi_capability":
            cached = _PROBE_CACHE.get(port.upper())
            probe = cached[1] if cached else None
            passed = bool(probe and str(probe.get("chip", "")).upper().startswith("ESP8266") and "Wi-Fi" in probe.get("features", []))
            return {
                "passed": passed,
                "summary": "ESP8266 ROM verified integrated 2.4 GHz Wi-Fi hardware." if passed else "Run the processor identification probe before testing Wi-Fi capability.",
                "evidence": probe or {},
            }
        return None
