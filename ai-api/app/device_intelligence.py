from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LOCAL_ARDUINO_CLI = ROOT / ".tools" / "arduino-cli" / "arduino-cli.exe"
_arduino_cache: tuple[float, dict[str, dict]] = (0.0, {})


def _component(
    component_id: str,
    name: str,
    component_type: str,
    status: str,
    source: str,
    *,
    bus: str | None = None,
    variant: str | None = None,
    test_id: str | None = None,
) -> dict:
    return {
        "id": component_id,
        "name": name,
        "type": component_type,
        "bus": bus,
        "status": status,
        "source": source,
        "variant": variant,
        "test_id": test_id,
    }


BOARD_CATALOG: dict[str, dict[str, Any]] = {
    "2341:805A": {
        "family": "Arduino Nano 33 BLE family",
        "manufacturer": "Arduino",
        "classification": "microcontroller_board",
        "mcu": "Nordic nRF52840",
        "architecture": "Arm Cortex-M4F",
        "runtime": "Arduino Mbed OS core",
        "confidence": 0.93,
        "candidates": [
            "Arduino Nano 33 BLE",
            "Arduino Nano 33 BLE Sense (original)",
            "Arduino Nano 33 BLE Sense Rev2",
        ],
        "capabilities": [
            {"id": "usb_serial", "name": "USB serial", "status": "verified", "source": "Windows USB enumeration"},
            {"id": "ble", "name": "Bluetooth Low Energy", "status": "expected", "source": "Arduino board family"},
            {"id": "gpio", "name": "GPIO", "status": "expected", "source": "Arduino board family"},
            {"id": "i2c", "name": "I2C", "status": "expected", "source": "Arduino board family"},
            {"id": "spi", "name": "SPI", "status": "expected", "source": "Arduino board family"},
        ],
        "components": [
            _component("nrf52840", "Nordic nRF52840", "microcontroller", "expected", "Arduino board definition"),
            _component("lsm9ds1", "LSM9DS1 accelerometer, gyroscope, and magnetometer", "sensor", "expected", "Arduino product specification", bus="I2C/SPI", variant="Nano 33 BLE Sense (original)", test_id="sensor_diagnostic"),
            _component("apds9960", "APDS9960 color, light, proximity, and gesture sensor", "sensor", "expected", "Arduino product specification", bus="I2C", variant="Nano 33 BLE Sense (original)", test_id="sensor_diagnostic"),
            _component("hts221", "HTS221 temperature and humidity sensor", "sensor", "expected", "Arduino product specification", bus="I2C", variant="Nano 33 BLE Sense (original)", test_id="sensor_diagnostic"),
            _component("lps22hb", "LPS22HB barometric pressure sensor", "sensor", "expected", "Arduino product specification", bus="I2C", variant="Nano 33 BLE Sense (original)", test_id="sensor_diagnostic"),
            _component("mp34dt05", "MP34DT05 digital microphone", "sensor", "expected", "Arduino product specification", bus="PDM", variant="Nano 33 BLE Sense (original)", test_id="sensor_diagnostic"),
            _component("bmi270", "BMI270 accelerometer and gyroscope", "sensor", "expected", "Arduino Rev2 specification", bus="I2C/SPI", variant="Nano 33 BLE Sense Rev2", test_id="sensor_diagnostic"),
            _component("bmm150", "BMM150 magnetometer", "sensor", "expected", "Arduino Rev2 specification", bus="I2C", variant="Nano 33 BLE Sense Rev2", test_id="sensor_diagnostic"),
        ],
        "resources": [
            {"title": "Arduino Nano 33 BLE Sense", "url": "https://docs.arduino.cc/hardware/nano-33-ble-sense", "provider": "Arduino", "kind": "product"},
            {"title": "Arduino Mbed core definition", "url": "https://github.com/arduino/ArduinoCore-mbed/tree/main/variants/ARDUINO_NANO33BLE", "provider": "Arduino", "kind": "source"},
        ],
    },
    "2341:005A": {
        "alias_of": "2341:805A",
        "mode": "bootloader",
    },
    "239A:8023": {
        "family": "Adafruit Feather M0 Express",
        "manufacturer": "Adafruit",
        "classification": "microcontroller_board",
        "mcu": "Microchip ATSAMD21G18",
        "architecture": "Arm Cortex-M0+",
        "runtime": "CircuitPython",
        "confidence": 0.99,
        "candidates": ["Adafruit Feather M0 Express"],
        "capabilities": [
            {"id": "usb_serial", "name": "USB serial", "status": "verified", "source": "Windows USB enumeration"},
            {"id": "circuitpython", "name": "CircuitPython runtime", "status": "verified", "source": "Adafruit runtime USB identity"},
            {"id": "mass_storage", "name": "CircuitPython storage", "status": "expected", "source": "CircuitPython runtime"},
            {"id": "gpio", "name": "GPIO", "status": "expected", "source": "Board definition"},
            {"id": "i2c", "name": "I2C", "status": "expected", "source": "Board definition"},
            {"id": "spi", "name": "SPI", "status": "expected", "source": "Board definition"},
        ],
        "components": [
            _component("samd21g18", "Microchip ATSAMD21G18", "microcontroller", "expected", "Adafruit board definition"),
            _component("spi_flash", "2 MB SPI flash", "storage", "expected", "Adafruit board specification", bus="SPI"),
            _component("neopixel", "Single RGB NeoPixel", "output", "expected", "Adafruit board specification", bus="GPIO D8"),
        ],
        "resources": [
            {"title": "Feather M0 Express guide", "url": "https://learn.adafruit.com/adafruit-feather-m0-express-designed-for-circuit-python-circuitpython", "provider": "Adafruit", "kind": "guide"},
            {"title": "CircuitPython board source", "url": "https://github.com/adafruit/circuitpython/tree/main/ports/atmel-samd/boards/feather_m0_express", "provider": "Adafruit", "kind": "source"},
        ],
    },
    "1D50:6018": {
        "family": "Great Scott Gadgets HackRF One",
        "manufacturer": "Great Scott Gadgets",
        "classification": "software_defined_radio",
        "mcu": "NXP LPC4320",
        "architecture": "Arm Cortex-M4 / Cortex-M0",
        "runtime": "HackRF firmware",
        "confidence": 0.99,
        "candidates": ["Great Scott Gadgets HackRF One"],
        "capabilities": [
            {"id": "usb", "name": "USB control and sample transport", "status": "verified", "source": "USB identity 1D50:6018"},
            {"id": "sdr", "name": "Software-defined radio", "status": "expected", "source": "HackRF One hardware profile"},
            {"id": "rf_half_duplex", "name": "Half-duplex RF receive and transmit", "status": "expected", "source": "HackRF One hardware profile"},
        ],
        "components": [
            _component("lpc4320", "NXP LPC4320", "microcontroller", "expected", "HackRF One hardware profile"),
            _component("max2837", "MAX2837", "RF transceiver", "expected", "HackRF One hardware profile"),
            _component("rffc5072", "RFFC5072", "frequency mixer", "expected", "HackRF One hardware profile"),
            _component("si5351c", "Si5351C", "clock generator", "expected", "HackRF One hardware profile"),
        ],
        "resources": [
            {"title": "HackRF One documentation", "url": "https://hackrf.readthedocs.io/en/latest/hackrf_one.html", "provider": "Great Scott Gadgets", "kind": "documentation"},
        ],
    },
    "303A:1001": {
        "family": "Espressif ESP32 USB JTAG/serial family",
        "manufacturer": "Espressif",
        "classification": "microcontroller_board",
        "mcu": "ESP32 family",
        "architecture": "Xtensa or RISC-V, variant dependent",
        "runtime": "Firmware dependent",
        "confidence": 0.82,
        "candidates": ["ESP32 USB JTAG/serial device"],
        "capabilities": [
            {"id": "usb_serial", "name": "USB serial", "status": "verified", "source": "USB identity"},
            {"id": "jtag", "name": "USB JTAG", "status": "expected", "source": "USB identity"},
        ],
        "components": [],
        "resources": [
            {"title": "Espressif documentation", "url": "https://docs.espressif.com/", "provider": "Espressif", "kind": "documentation"},
        ],
    },
    "359F:2120": {
        "family": "Sipeed LicheeRV Nano",
        "manufacturer": "Sipeed",
        "classification": "linux_single_board_computer",
        "mcu": "Sophgo SG2002",
        "architecture": "RISC-V / Arm heterogeneous SoC",
        "runtime": "Linux",
        "confidence": 0.99,
        "candidates": ["Sipeed LicheeRV Nano"],
        "capabilities": [
            {"id": "usb_network", "name": "USB networking", "status": "expected", "source": "Sipeed board specification"},
            {"id": "linux", "name": "Linux operating system", "status": "expected", "source": "Requires bootable media and a responding runtime"},
            {"id": "ssh", "name": "SSH server", "status": "expected", "source": "Requires a responding Linux image"},
            {"id": "http", "name": "HTTP service", "status": "expected", "source": "Requires a responding PicoClaw service"},
        ],
        "components": [
            _component("sg2002", "Sophgo SG2002", "system-on-chip", "expected", "Sipeed board specification"),
            _component("gc4653", "GC4653 camera sensor", "camera", "unknown", "Device configuration", bus="I2C", test_id="service_check"),
        ],
        "resources": [
            {"title": "LicheeRV Nano documentation", "url": "https://en.wiki.sipeed.com/hardware/en/lichee/RV_Nano/1_intro.html", "provider": "Sipeed", "kind": "documentation"},
            {"title": "PicoClaw documentation", "url": "https://en.wiki.sipeed.com/hardware/en/lichee/RV_Nano/7_picoclaw_board.html", "provider": "Sipeed", "kind": "documentation"},
        ],
    },
    "10C4:EA60": {
        "family": "Silicon Labs CP210x USB-to-UART bridge",
        "manufacturer": "Silicon Labs",
        "classification": "usb_uart_bridge",
        "mcu": "Target behind UART is not identified by USB",
        "architecture": "Unknown until a target protocol answers",
        "runtime": "Unknown",
        "confidence": 0.99,
        "candidates": ["Silicon Labs CP210x USB-to-UART bridge"],
        "capabilities": [
            {"id": "usb_uart", "name": "USB-to-UART transport", "status": "verified", "source": "Silicon Labs USB identity"},
        ],
        "components": [],
        "resources": [
            {"title": "CP2102 USB-to-UART bridge", "url": "https://www.silabs.com/interface/usb-bridges/classic/device.cp2102", "provider": "Silicon Labs", "kind": "documentation"},
        ],
    },
}


def arduino_cli_path() -> str | None:
    configured = os.getenv("ARDUINO_CLI_PATH")
    if configured and Path(configured).is_file():
        return configured
    if LOCAL_ARDUINO_CLI.is_file():
        return str(LOCAL_ARDUINO_CLI)
    return shutil.which("arduino-cli")


def arduino_board_inventory(force: bool = False) -> dict[str, dict]:
    global _arduino_cache
    now = time.monotonic()
    if not force and now - _arduino_cache[0] < 5:
        return deepcopy(_arduino_cache[1])
    executable = arduino_cli_path()
    if not executable:
        return {}
    try:
        result = subprocess.run(
            [executable, "board", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        payload = json.loads(result.stdout) if result.returncode == 0 and result.stdout else {}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}
    inventory: dict[str, dict] = {}
    for detected in payload.get("detected_ports", []):
        port = detected.get("port", {})
        address = port.get("address")
        if not address:
            continue
        boards = detected.get("matching_boards", [])
        properties = port.get("properties", {})
        inventory[address] = {
            "address": address,
            "protocol": port.get("protocol_label") or port.get("protocol"),
            "product": properties.get("product"),
            "manufacturer": properties.get("manufacturer"),
            "serial_number": properties.get("serialNumber"),
            "boards": boards,
        }
    _arduino_cache = (now, inventory)
    return deepcopy(inventory)


def _catalog_record(identity: str) -> dict[str, Any] | None:
    record = BOARD_CATALOG.get(identity)
    if not record:
        return None
    if "alias_of" in record:
        canonical = deepcopy(BOARD_CATALOG[record["alias_of"]])
        canonical["mode"] = record.get("mode")
        return canonical
    return deepcopy(record)


def enrich_hardware_list(hardware: list[dict[str, Any]]) -> list[dict[str, Any]]:
    arduino = arduino_board_inventory()
    enriched = []
    for original in hardware:
        item = dict(original)
        identity = f"{item.get('vid')}:{item.get('pid')}" if item.get("vid") and item.get("pid") else ""
        catalog = _catalog_record(identity)
        cli = arduino.get(str(item.get("device")))
        if catalog:
            item["name"] = catalog["family"]
            item["classification"] = catalog["classification"]
            item["confidence"] = catalog["confidence"]
        if cli and cli.get("boards"):
            item["name"] = cli["boards"][0]["name"]
            item["board_fqbn"] = cli["boards"][0].get("fqbn")
            item["metadata_provider"] = "Arduino CLI"
        classification = str(item.get("classification") or "")
        if classification in {"microcontroller_board", "linux_single_board_computer", "software_defined_radio", "ai_accelerator"}:
            item["device_category"] = "Circuit, controller, or compute target"
        elif classification in {"usb_uart_bridge", "debug_probe"}:
            item["device_category"] = "Programming or debug interface"
        elif item.get("kind") == "serial":
            item["device_category"] = "Unresolved serial target"
        else:
            item["device_category"] = item.get("device_category") or "Host peripheral"
        enriched.append(item)
    return enriched


def inspect_hardware(profile: dict[str, Any], live: dict[str, Any] | None = None, assigned_model: str | None = None) -> dict:
    identity = f"{profile.get('vid')}:{profile.get('pid')}" if profile.get("vid") and profile.get("pid") else ""
    catalog = _catalog_record(identity)
    cli = arduino_board_inventory().get(str(profile.get("device")))
    evidence = [
        {"source": "host enumeration", "claim": "Interface is currently present", "status": "verified"},
    ]
    if identity:
        evidence.append({"source": "USB descriptor", "claim": f"USB identity {identity}", "status": "verified"})
    if cli and cli.get("boards"):
        for board in cli["boards"]:
            evidence.append({"source": "Arduino CLI", "claim": f"{board['name']} ({board.get('fqbn', 'no FQBN')})", "status": "verified"})
    if catalog:
        model = assigned_model or catalog["family"]
        family = catalog.get("family")
        manufacturer = catalog.get("manufacturer")
        capabilities = catalog.get("capabilities", [])
        components = catalog.get("components", [])
        if not assigned_model and catalog.get("family") in catalog.get("candidates", []):
            capabilities = [capability for capability in capabilities if not capability.get("variant")]
            components = [component for component in components if not component.get("variant")]
        if assigned_model:
            capabilities = [
                capability
                for capability in capabilities
                if not capability.get("variant") or assigned_model == capability["variant"]
            ]
            components = [
                component
                for component in components
                if not component.get("variant") or assigned_model.endswith(component["variant"]) or assigned_model == component["variant"]
            ]
            evidence.append(
                {
                    "source": "saved bench profile",
                    "claim": f"Exact model selected as {assigned_model}",
                    "status": "declared",
                }
            )
        resources = catalog.get("resources", [])
        candidates = catalog.get("candidates", [])
        confidence = catalog.get("confidence", 0.5)
        classification = catalog.get("classification", "unknown")
        mcu = catalog.get("mcu")
        architecture = catalog.get("architecture")
        runtime = catalog.get("runtime")
    else:
        model = assigned_model or profile.get("name") or profile.get("description") or "Unidentified hardware"
        family = None
        manufacturer = profile.get("manufacturer")
        if profile.get("kind") == "serial":
            capabilities = [{"id": "usb_serial", "name": "USB serial", "status": "detected", "source": "Host enumeration"}]
        elif profile.get("kind") == "usb_identity":
            capabilities = [{"id": "usb", "name": "USB device interface", "status": "verified", "source": "Host USB enumeration"}]
        else:
            capabilities = []
        if profile.get("classification") == "camera_peripheral":
            capabilities.append({"id": "camera", "name": "Camera / video capture", "status": "detected", "source": "Host device classification"})
        elif profile.get("classification") == "audio_video_peripheral":
            capabilities.append({"id": "audio_video", "name": "Audio / video interface", "status": "detected", "source": "Host device classification"})
        elif profile.get("classification") == "display_adapter":
            capabilities.append({"id": "display", "name": "Display adapter", "status": "detected", "source": "Host device classification"})
        components = []
        resources = []
        candidates = []
        confidence = profile.get("confidence", 0.4)
        classification = profile.get("classification") or "unclassified_device"
        mcu = architecture = runtime = None

    services: list[dict] = []
    if live:
        live_identity = live.get("identity")
        if live_identity:
            model = assigned_model or live_identity.get("model") or model
            family = live_identity.get("family") or family
            classification = live_identity.get("classification") or classification
            manufacturer = live_identity.get("manufacturer") or manufacturer
            mcu = live_identity.get("mcu") or mcu
            architecture = live_identity.get("architecture") or architecture
            runtime = live_identity.get("runtime") or runtime
            confidence = live_identity.get("confidence", confidence)
            candidates = list(live_identity.get("candidates", candidates))
            capabilities = list(live_identity.get("capabilities", capabilities))
            components = list(live_identity.get("components", components))
            resources = list(live_identity.get("resources", resources))
            if assigned_model:
                capabilities = [item for item in capabilities if not item.get("variant") or item.get("variant") == assigned_model]
                components = [item for item in components if not item.get("variant") or item.get("variant") == assigned_model]
                model_claim = f"Exact model selected as {assigned_model}"
                if not any(item.get("claim") == model_claim for item in evidence):
                    evidence.append({"source": "saved bench profile", "claim": model_claim, "status": "declared"})
            else:
                capabilities = [item for item in capabilities if not item.get("variant")]
                components = [item for item in components if not item.get("variant")]
        telemetry = live.get("telemetry", {})
        if telemetry.get("firmware"):
            runtime = telemetry["firmware"]
            evidence.append({"source": "authenticated device inspection", "claim": f"Runtime {runtime}", "status": "verified"})
        live_services = live.get("services", {})
        if live_services.get("ssh"):
            services.append({"name": "SSH", "address": profile.get("ip_address"), "port": 22, "status": "verified"})
        if live_services.get("web"):
            services.append({"name": live_services.get("web_title") or "HTTP", "address": profile.get("ip_address"), "port": 18800, "url": profile.get("web_url"), "status": "verified"})
        verified_capabilities = {
            "usb_network": bool(live.get("online")),
            "linux": bool(telemetry.get("ssh_authenticated")),
            "ssh": bool(live_services.get("ssh")),
            "http": bool(live_services.get("web")),
        }
        for capability in capabilities:
            if verified_capabilities.get(capability.get("id")):
                capability["status"] = "verified"
                capability["source"] = "Live target inspection"
        for component in components:
            if component["id"] == "gc4653":
                component["status"] = "verified" if telemetry.get("camera_ready") else "unavailable"
                component["source"] = telemetry.get("camera_status") or component["source"]
        diagnostic = live.get("diagnostic", {})
        if diagnostic.get("ready"):
            runtime = diagnostic.get("protocol")
            evidence.append({"source": "serial diagnostic handshake", "claim": f"Compatible protocol {runtime}", "status": "verified"})
            reported_sensors = diagnostic.get("sensors", {})
            for component in components:
                if component["id"] in reported_sensors:
                    component["status"] = "verified" if reported_sensors[component["id"]] else "unavailable"
                    component["source"] = "Live diagnostic firmware initialization"
        adapter = live.get("adapter")
        if adapter:
            evidence.extend(live.get("evidence", []))
            if telemetry.get("storage_mount"):
                for capability in capabilities:
                    if capability.get("id") in {"circuitpython", "mass_storage"}:
                        capability["status"] = "verified"
                        capability["source"] = f"Mounted CIRCUITPY volume {telemetry['storage_mount']}"
                for component in components:
                    if component.get("id") in {"samd21g18", "spi_flash"}:
                        component["status"] = "verified"
                        component["source"] = "CircuitPython boot metadata and mounted storage"
            if live.get("probe") and adapter.get("id") == "circuitpython":
                for capability in capabilities:
                    if capability.get("id") in {"gpio", "i2c"}:
                        capability["status"] = "verified"
                        capability["source"] = "Controlled CircuitPython runtime probe"
    elif identity == "359F:2120":
        runtime = "Linux expected; boot media and runtime not verified"

    tests = [
        {"id": "presence", "name": "Verify host connection", "risk": "passive", "available": True, "description": "Confirm that the selected interface is still present on this host."},
    ]
    if profile.get("kind") == "usb_network":
        tests.append({"id": "service_check", "name": "Verify target services", "risk": "read-only", "available": True, "description": "Recheck the selected target's network, SSH, HTTP, and telemetry endpoints."})
    if profile.get("kind") == "serial" and not (live or {}).get("adapter"):
        diagnostic_ready = bool((live or {}).get("diagnostic", {}).get("ready"))
        tests.append({"id": "serial_protocol", "name": "Verify serial diagnostic protocol", "risk": "read-only", "available": diagnostic_ready, "description": "Rechecks the identified diagnostic handshake without sending arbitrary bytes." if diagnostic_ready else "Requires a compatible runtime or diagnostic firmware; the bench will not send arbitrary bytes."})
    for component in components:
        if component.get("type") == "sensor":
            diagnostic_ready = bool((live or {}).get("diagnostic", {}).get("ready"))
            sensor_ready = bool((live or {}).get("diagnostic", {}).get("sensors", {}).get(component["id"]))
            tests.append(
                {
                    "id": f"sensor:{component['id']}",
                    "name": f"Test {component['name']}",
                    "risk": "read-only" if diagnostic_ready else "destructive",
                    "available": diagnostic_ready and sensor_ready,
                    "description": "Samples this sensor through the identified diagnostic protocol." if diagnostic_ready else "Requires compatible diagnostic firmware. Installing it replaces the board's current sketch; the bench will never flash it automatically.",
                }
            )
    adapter_tests = list((live or {}).get("tests", []))
    tests.extend(adapter_tests)
    if any(capability.get("id") == "i2c" for capability in capabilities) and not any(test.get("id") == "circuitpython_i2c_scan" for test in adapter_tests):
        tests.append(
            {
                "id": "i2c_inventory",
                "name": "Inventory attached I2C addresses",
                "risk": "disruptive",
                "available": bool((live or {}).get("diagnostic", {}).get("ready")),
                "description": "Scans the exposed external I2C controller for responding addresses. Addresses do not prove a unique part model." if (live or {}).get("diagnostic", {}).get("ready") else "Requires firmware, an operating-system I2C adapter, or a debug probe that exposes the bus. Addresses do not prove a unique part model.",
            }
        )

    connection_interfaces = []
    connection_rules = {
        "i2c": ("I2C", "Address enumeration requires an exposed controller. An address usually does not identify a unique part."),
        "spi": ("SPI", "SPI has no generic discovery or address-enumeration protocol; a chip-select map and safe driver are required."),
        "uart": ("UART", "UART requires known voltage, baud rate, and protocol. The bench will not transmit blind probe bytes."),
        "gpio": ("GPIO / analog pins", "Passive pins do not report what is wired to them. Driving an unknown pin can damage attached hardware."),
        "sdio": ("SDIO", "Enumeration requires the selected device to expose an SDIO host controller and driver."),
    }
    capability_ids = {capability.get("id") for capability in capabilities}
    for interface_id, (name, limitation) in connection_rules.items():
        if interface_id not in capability_ids:
            continue
        verified = interface_id == "i2c" and bool((live or {}).get("telemetry", {}).get("i2c_adapters"))
        connection_interfaces.append(
            {
                "id": interface_id,
                "name": name,
                "status": "verified" if verified else "expected",
                "adapter": (live or {}).get("telemetry", {}).get("i2c_adapters") if verified else None,
                "limitation": limitation,
            }
        )

    return {
        "identifier": profile["id"],
        "interface": profile.get("device"),
        "identity": identity or None,
        "model": model,
        "family": family,
        "classification": classification,
        "confidence": confidence,
        "manufacturer": manufacturer,
        "mcu": mcu,
        "architecture": architecture,
        "runtime": runtime,
        "candidates": candidates,
        "evidence": evidence,
        "capabilities": capabilities,
        "components": components,
        "services": services,
        "connection_interfaces": connection_interfaces,
        "pins": list((live or {}).get("pins", [])),
        "attached_peripherals": list((live or {}).get("attached_peripherals", [])),
        "identity_layers": list((live or {}).get("identity_layers", [])),
        "adapter": (live or {}).get("adapter"),
        "telemetry": (live or {}).get("telemetry", {}),
        "tests": tests,
        "resources": resources,
        "limitations": [
            "USB and serial enumeration cannot reveal unexposed sensors or attached circuits.",
            "Expected components become verified only after a compatible runtime, debug probe, or approved diagnostic firmware reports them.",
            "SPI, UART, GPIO, analog pins, and passive terminal connections have no universal discovery protocol and are never driven blindly.",
            "A USB-to-UART bridge identifies the bridge, not the processor wired behind it; target identity requires a safe protocol handshake or a declared board profile.",
        ],
    }


def metadata_providers() -> list[dict]:
    return [
        {"id": "local_catalog", "name": "Bench board catalog", "scope": "USB identities, components, and test definitions", "available": True, "requires_key": False, "mode": "offline"},
        {"id": "arduino_cli", "name": "Arduino CLI", "scope": "Arduino board identity, FQBN, cores, build, and upload metadata", "available": bool(arduino_cli_path()), "requires_key": False, "mode": "local"},
        {"id": "platformio", "name": "PlatformIO", "scope": "Cross-vendor board, MCU, framework, build, and upload metadata", "available": True, "requires_key": False, "mode": "local and registry"},
        {"id": "circuitpython", "name": "CircuitPython board definitions", "scope": "CircuitPython runtime identities and board definitions", "available": True, "requires_key": False, "mode": "cached public source"},
        {"id": "github", "name": "GitHub source metadata", "scope": "Authoritative vendor board definitions and documentation", "available": bool(os.getenv("GITHUB_TOKEN")), "requires_key": True, "mode": "optional online"},
        {"id": "nexar", "name": "Nexar component API", "scope": "Electronic component specifications and manufacturer data", "available": bool(os.getenv("NEXAR_CLIENT_ID") and os.getenv("NEXAR_CLIENT_SECRET")), "requires_key": True, "mode": "optional online"},
        {"id": "digikey", "name": "DigiKey Product Information API", "scope": "Component specifications, datasheets, and lifecycle information", "available": bool(os.getenv("DIGIKEY_CLIENT_ID") and os.getenv("DIGIKEY_CLIENT_SECRET")), "requires_key": True, "mode": "optional online"},
        {"id": "cmsis_packs", "name": "CMSIS Device Family Packs", "scope": "Arm processor, memory, register, debug, and flash algorithms", "available": False, "requires_key": False, "mode": "local pack cache through pyOCD"},
        {"id": "zephyr", "name": "Zephyr board definitions", "scope": "Devicetree, pin control, buses, peripherals, and supported features", "available": False, "requires_key": False, "mode": "local west workspace"},
        {"id": "kicad", "name": "KiCad design evidence", "scope": "Expected components, nets, footprints, and BOM from user-owned design files", "available": bool(shutil.which("kicad-cli")), "requires_key": False, "mode": "local project import"},
        {"id": "renode", "name": "Renode platform models", "scope": "Known CPU, bus, peripheral, and automated firmware-test models", "available": bool(shutil.which("renode")), "requires_key": False, "mode": "local emulator"},
    ]
