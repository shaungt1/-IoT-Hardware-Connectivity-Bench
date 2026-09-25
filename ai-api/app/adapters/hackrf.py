from __future__ import annotations

import shutil
import subprocess
from typing import Any

from .base import AdapterManifest


HACKRF_ONE_USB_IDS = {("1D50", "6018"), ("1D50", "6089")}


def _pin(header: str, number: int, function: str) -> dict[str, Any]:
    normalized = function.replace(" (One)", "")
    direction = "power" if normalized in {"GND", "VCC", "VBUS", "VBAT", "VIN", "3V3AUX"} else "bidirectional"
    return {
        "name": f"{header}.{number}",
        "aliases": [normalized],
        "group": header,
        "functions": [normalized],
        "direction": direction,
        "status": "expected",
        "source": "Great Scott Gadgets HackRF expansion-interface documentation",
    }


P20 = (
    "VBAT", "RTC_ALARM", "VCC", "WAKEUP", "GPIO3_8", "GPIO3_0", "GPIO3_10", "GPIO3_11",
    "GPIO3_12", "GPIO3_13", "GPIO3_14", "GPIO3_15", "GND", "ADC0_6", "GND", "ADC0_2",
    "VBUSCTRL", "ADC0_5", "GND", "ADC0_0", "VBUS", "VIN",
)
P22 = (
    "CLKOUT", "CLKIN", "RESET", "GND", "I2C1_SCL", "I2C1_SDA", "SPIFI_MISO", "SPIFI_SCK",
    "SPIFI_MOSI", "GND", "VCC", "I2S0_RX_SCK", "I2S0_RX_SDA", "I2S0_RX_MCLK", "I2S0_RX_WS",
    "I2S0_TX_SCK", "I2S0_TX_MCLK", "GND", "U0_RXD", "U0_TXD", "P2_9", "P2_13", "P2_8",
    "SDA", "CLK6", "SCL",
)
P28 = (
    "VCC", "GND", "SD_CD", "SD_DAT3", "SD_DAT2", "SD_DAT1", "SD_DAT0", "SD_VOLT0", "SD_CMD",
    "SD_POW", "SD_CLK", "GND", "GCK2", "GCK1", "TRIGGER_OUT", "TRIGGER_IN", "CPLD_TCK",
    "BANK2F3M2", "CPLD_TDI", "BANK2F3M6", "BANK2F3M12", "BANK2F3M4",
)
P9 = (
    "GND", "GND", "GND", "RXBBQ-", "RXBBI-", "RXBBQ+", "RXBBI+", "GND", "GND", "TXBBI-",
    "TXBBQ+", "TXBBI+", "TXBBQ-", "GND", "GND", "GND",
)
HACKRF_ONE_PINS = [
    _pin(header, index, function)
    for header, functions in (("P20", P20), ("P22", P22), ("P28", P28), ("P9", P9))
    for index, function in enumerate(functions, 1)
]


def _tool_path() -> str | None:
    return shutil.which("hackrf_info")


def _runtime_info() -> dict[str, Any]:
    executable = _tool_path()
    if not executable:
        raise ValueError("hackrf_info is not installed; the USB identity and documented connector map remain available")
    try:
        result = subprocess.run([executable], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"hackrf_info could not complete: {error}") from error
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0:
        detail = next((line.strip() for line in reversed(output.splitlines()) if line.strip()), "No HackRF response")
        raise ValueError(f"HackRF runtime query failed: {detail}")
    fields: dict[str, str] = {}
    for line in output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower().replace(" ", "_")] = value.strip()
    return {"ready": True, "fields": fields, "raw_summary": output[:16_384]}


class HackRfAdapter:
    adapter_id = "hackrf_one"
    name = "HackRF One USB adapter"
    manifest = AdapterManifest(
        id=adapter_id,
        name=name,
        version="1.0",
        transports=("USB control", "USB sample stream", "USB serial identity"),
        families=("HackRF One", "HackRF Pro"),
        inspection_modes=("passive", "read-only"),
        timeout_seconds=10,
        safety="USB descriptors and the published expansion map are passive; hackrf_info performs bounded read-only control queries and never enables transmit.",
    )

    def supports(self, profile: dict[str, Any]) -> bool:
        identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
        return identity in HACKRF_ONE_USB_IDS

    def inspect_passive(self, profile: dict[str, Any]) -> dict[str, Any]:
        identity = f"{str(profile.get('vid', '')).upper()}:{str(profile.get('pid', '')).upper()}"
        return {
            "adapter": {"id": self.adapter_id, "name": self.name, "mode": "passive USB identity and published connector map"},
            "identity": {
                "model": "Great Scott Gadgets HackRF One",
                "family": "HackRF",
                "classification": "software_defined_radio",
                "manufacturer": "Great Scott Gadgets",
                "mcu": "NXP LPC4320",
                "architecture": "Arm Cortex-M4 / Cortex-M0",
                "runtime": "HackRF firmware; version not queried",
                "confidence": 0.99,
                "candidates": ["Great Scott Gadgets HackRF One"],
                "capabilities": [
                    {"id": "usb", "name": "USB control and sample transport", "status": "verified", "source": f"USB identity {identity}"},
                    {"id": "sdr", "name": "Software-defined radio", "status": "verified", "source": f"Great Scott Gadgets USB identity {identity}"},
                    {"id": "gpio", "name": "Expansion GPIO", "status": "expected", "source": "HackRF expansion-interface documentation"},
                    {"id": "i2c", "name": "Expansion I2C", "status": "expected", "source": "HackRF P22 connector map"},
                    {"id": "spi", "name": "Expansion SPI / SPIFI", "status": "expected", "source": "HackRF P22 connector map"},
                    {"id": "uart", "name": "Expansion UART", "status": "expected", "source": "HackRF P22 connector map"},
                    {"id": "sdio", "name": "Expansion SDIO", "status": "expected", "source": "HackRF P28 connector map"},
                ],
                "components": [
                    {"id": "lpc4320", "name": "NXP LPC4320", "type": "microcontroller", "status": "expected", "source": "HackRF One design documentation"},
                    {"id": "max2837", "name": "MAX2837", "type": "RF transceiver", "status": "expected", "source": "HackRF One design documentation"},
                    {"id": "rffc5072", "name": "RFFC5072", "type": "frequency mixer", "status": "expected", "source": "HackRF One design documentation"},
                    {"id": "si5351c", "name": "Si5351C", "type": "clock generator", "status": "expected", "source": "HackRF One design documentation"},
                ],
                "resources": [{"title": "HackRF expansion interface", "url": "https://hackrf.readthedocs.io/en/latest/expansion_interface.html", "provider": "Great Scott Gadgets", "kind": "connector map"}],
            },
            "identity_layers": [
                {"id": "usb_interface", "layer": "Host interface", "name": f"HackRF USB {identity}", "status": "verified", "source": "Host USB enumeration"},
                {"id": "board", "layer": "Board", "name": "HackRF One", "status": "verified", "source": f"Assigned vendor USB identity {identity}"},
                {"id": "connectors", "layer": "Expansion topology", "name": "P20, P22, P28 and P9", "status": "expected", "source": "Great Scott Gadgets connector documentation"},
            ],
            "telemetry": {"runtime_query_available": bool(_tool_path()), "connector_count": 4, "documented_pin_count": len(HACKRF_ONE_PINS)},
            "evidence": [{"source": "USB descriptor", "claim": f"Great Scott Gadgets HackRF identity {identity}", "status": "verified"}],
            "tests": [
                {"id": "hackrf_usb_identity", "name": "Verify HackRF USB identity", "risk": "passive", "available": True, "description": "Rechecks the assigned Great Scott Gadgets USB vendor/product identity without transmitting RF."},
                {"id": "hackrf_runtime_info", "name": "Read HackRF board and firmware information", "risk": "read-only", "available": bool(_tool_path()), "description": "Uses hackrf_info for bounded read-only USB control queries. It never starts RF transmit."},
            ],
            "pins": HACKRF_ONE_PINS,
            "attached_peripherals": [],
        }

    def run_test(self, profile: dict[str, Any], test_id: str) -> dict[str, Any] | None:
        if test_id == "hackrf_usb_identity":
            identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
            passed = identity in HACKRF_ONE_USB_IDS
            return {"passed": passed, "summary": "Assigned HackRF USB identity is present." if passed else "The selected interface is not an assigned HackRF USB identity.", "evidence": {"vid": identity[0], "pid": identity[1]}}
        if test_id == "hackrf_runtime_info":
            result = _runtime_info()
            return {"passed": True, "summary": "HackRF board and firmware information answered through read-only USB control queries.", "evidence": result}
        return None
