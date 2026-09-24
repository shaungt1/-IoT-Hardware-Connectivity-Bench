from __future__ import annotations

import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path

from .device_intelligence import arduino_cli_path


TOOLS = (
    {"id": "pyusb", "name": "PyUSB", "category": "USB discovery", "risk": "passive", "package": "pyusb"},
    {"id": "libusb", "name": "libusb", "category": "USB discovery", "risk": "passive", "package": "libusb-package"},
    {"id": "psutil", "name": "psutil", "category": "Host inventory", "risk": "passive", "package": "psutil"},
    {"id": "zeroconf", "name": "Zeroconf", "category": "Network discovery", "risk": "passive", "package": "zeroconf"},
    {"id": "pyserial", "name": "pySerial", "category": "Serial transport", "risk": "read-only", "package": "pyserial"},
    {"id": "bleak", "name": "Bleak", "category": "Bluetooth LE", "risk": "read-only", "package": "bleak"},
    {"id": "platformio", "name": "PlatformIO Core", "category": "Build and flash", "risk": "destructive", "module": "platformio"},
    {"id": "arduino-cli", "name": "Arduino CLI", "category": "Build and flash", "risk": "destructive", "command": "arduino-cli"},
    {"id": "esptool-inspect", "name": "esptool ROM identification", "category": "Espressif processor and flash identification", "risk": "disruptive", "command": "esptool", "package": "esptool"},
    {"id": "esptool-flash", "name": "esptool flashing", "category": "Espressif firmware flash", "risk": "destructive", "command": "esptool", "package": "esptool"},
    {"id": "mpremote", "name": "mpremote", "category": "MicroPython", "risk": "disruptive", "command": "mpremote", "package": "mpremote"},
    {"id": "openocd", "name": "OpenOCD", "category": "Debug", "risk": "disruptive", "command": "openocd"},
    {"id": "pyocd", "name": "pyOCD", "category": "Debug", "risk": "disruptive", "command": "pyocd", "package": "pyocd"},
    {"id": "probe-rs", "name": "probe-rs", "category": "Debug", "risk": "disruptive", "command": "probe-rs"},
    {"id": "avrdude", "name": "AVRDUDE", "category": "Flash", "risk": "destructive", "command": "avrdude"},
    {"id": "dfu-util", "name": "dfu-util", "category": "Flash", "risk": "destructive", "command": "dfu-util"},
    {"id": "bossac", "name": "BOSSA / bossac", "category": "SAMD flash", "risk": "destructive", "command": "bossac"},
    {"id": "picotool", "name": "picotool", "category": "RP2040/RP2350 inspect and flash", "risk": "disruptive", "command": "picotool"},
    {"id": "nrfutil", "name": "nRF Util", "category": "Nordic inspect and flash", "risk": "disruptive", "command": "nrfutil"},
    {"id": "stm32cubeprogrammer", "name": "STM32CubeProgrammer", "category": "STM32 inspect and flash", "risk": "destructive", "command": "STM32_Programmer_CLI"},
    {"id": "rpiboot", "name": "rpiboot", "category": "Raspberry Pi USB boot", "risk": "disruptive", "command": "rpiboot"},
    {"id": "rpi-eeprom-config", "name": "rpi-eeprom-config", "category": "Raspberry Pi EEPROM", "risk": "destructive", "command": "rpi-eeprom-config"},
    {"id": "ltchiptool", "name": "ltchiptool", "category": "Beken and LibreTiny", "risk": "destructive", "command": "ltchiptool", "package": "ltchiptool"},
    {"id": "hailortcli", "name": "HailoRT CLI", "category": "Hailo accelerator", "risk": "read-only", "command": "hailortcli"},
    {"id": "nvidia-smi", "name": "NVIDIA System Management Interface", "category": "NVIDIA GPU and accelerator inventory", "risk": "read-only", "command": "nvidia-smi"},
    {"id": "hackrf-info", "name": "hackrf_info", "category": "HackRF identity and firmware", "risk": "read-only", "command": "hackrf_info"},
    {"id": "rkdeveloptool", "name": "rkdeveloptool", "category": "Rockchip inspect and flash", "risk": "destructive", "command": "rkdeveloptool"},
    {"id": "sunxi-fel", "name": "sunxi-fel", "category": "Allwinner FEL", "risk": "destructive", "command": "sunxi-fel"},
    {"id": "usbipd", "name": "usbipd-win", "category": "USB passthrough to Linux tools", "risk": "disruptive", "command": "usbipd"},
    {"id": "i2cdetect", "name": "i2c-tools", "category": "Linux I2C bus inspection", "risk": "disruptive", "command": "i2cdetect"},
    {"id": "lsusb", "name": "lsusb", "category": "Linux USB inventory", "risk": "passive", "command": "lsusb"},
    {"id": "ffprobe", "name": "FFprobe", "category": "Camera and media", "risk": "read-only", "command": "ffprobe"},
    {"id": "sigrok-cli", "name": "sigrok-cli", "category": "Signal analysis", "risk": "read-only", "command": "sigrok-cli"},
    {"id": "pulseview", "name": "PulseView", "category": "Interactive logic analysis", "risk": "read-only", "command": "pulseview"},
    {"id": "renode", "name": "Renode", "category": "Firmware emulation and automated peripheral tests", "risk": "read-only", "command": "renode"},
    {"id": "kicad-cli", "name": "KiCad CLI", "category": "Schematic, BOM, and PCB evidence import", "risk": "read-only", "command": "kicad-cli"},
    {"id": "west", "name": "Zephyr west", "category": "Zephyr board metadata, build, and flash", "risk": "destructive", "command": "west"},
    {"id": "fritzing", "name": "Fritzing", "category": "Breadboard and wiring documentation", "risk": "read-only", "command": "Fritzing"},
    {"id": "circuitjs", "name": "CircuitJS", "category": "Circuit simulation; not physical discovery", "risk": "passive"},
    {"id": "wsl", "name": "Windows Subsystem for Linux", "category": "Linux tools", "risk": "read-only", "command": "wsl"},
)

PLATFORMIO_COMMANDS = {
    "openocd": ("tool-openocd/bin/openocd.exe", "tool-openocd-esp32/bin/openocd.exe"),
    "bossac": ("tool-bossac-nordicnrf52/bossac.exe",),
    "dfu-util": ("tool-stm32duino/dfu-util.exe", "tool-stm32duino/dfu-util-0.9-win64/dfu-util.exe"),
}


def _package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def _module_version(module: str) -> str | None:
    try:
        result = subprocess.run(
            [sys.executable, "-m", module, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr).strip().splitlines()[0]


def _command_path(command: str) -> str | None:
    resolved = shutil.which(command)
    if resolved:
        return resolved
    scripts = Path(sys.executable).parent
    for candidate in (scripts / command, scripts / f"{command}.exe", scripts / f"{command}.cmd"):
        if candidate.is_file():
            return str(candidate)
    platformio_home = Path.home() / ".platformio" / "packages"
    for relative in PLATFORMIO_COMMANDS.get(command, ()):
        candidate = platformio_home / relative
        if candidate.is_file():
            return str(candidate)
    return None


def tool_registry() -> dict:
    tools: list[dict] = []
    for definition in TOOLS:
        record = dict(definition)
        package = record.pop("package", None)
        module = record.pop("module", None)
        command = record.get("command")
        path = arduino_cli_path() if command == "arduino-cli" else _command_path(command) if command else None
        version = _package_version(package) if package else _module_version(module) if module else None
        record.update(
            {
                "available": bool(version or path),
                "version": version,
                "path": path,
                "capability": "active" if version or path else "planned",
            }
        )
        tools.append(record)
    return {
        "risk_levels": {
            "passive": "Non-mutating inventory; may read OS or USB descriptors but never claims an interface or changes the target.",
            "read-only": "May open a transport or send a non-mutating query.",
            "disruptive": "May claim an interface, reset a link, or pause target execution.",
            "destructive": "May erase, flash, or replace target data and requires explicit confirmation.",
        },
        "available_count": sum(1 for item in tools if item["available"]),
        "tools": tools,
    }
