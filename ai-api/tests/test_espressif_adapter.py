from types import SimpleNamespace

from app.adapters import espressif
from app.adapters.espressif import EspressifRomAdapter
from app.device_intelligence import inspect_hardware


PROFILE = {
    "id": "serial:COM11",
    "kind": "serial",
    "device": "COM11",
    "name": "Silicon Labs CP210x USB-to-UART bridge",
    "vid": "10C4",
    "pid": "EA60",
}


ESPTOOL_OUTPUT = """esptool v5.4.0
Connected to ESP8266 on COM11:
Chip type:          ESP8266EX
Features:           Wi-Fi, 160MHz
Crystal frequency:  26MHz
MAC:                00:11:22:33:44:55
Flash Memory Information:
Manufacturer: c2
Device: 2516
Detected flash size: 4MB
"""


def test_cp210x_adapter_offers_target_probe_without_claiming_processor(monkeypatch) -> None:
    monkeypatch.setattr(espressif, "_esptool_available", lambda: True)
    espressif._PROBE_CACHE.clear()

    live = EspressifRomAdapter().inspect_passive(PROFILE)

    assert live["identity"] is None
    assert live["identity_layers"][0]["name"].startswith("Silicon Labs CP210x")
    assert next(test for test in live["tests"] if test["id"] == "esp_rom_probe")["available"] is True


def test_rom_probe_adds_processor_flash_wifi_and_nodemcu_pin_map(monkeypatch) -> None:
    monkeypatch.setattr(espressif, "_esptool_available", lambda: True)
    monkeypatch.setattr(espressif.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=ESPTOOL_OUTPUT, stderr=""))
    monkeypatch.setattr("app.device_intelligence.arduino_board_inventory", lambda force=False: {})
    espressif._PROBE_CACHE.clear()
    adapter = EspressifRomAdapter()

    result = adapter.run_test(PROFILE, "esp_rom_probe")
    live = adapter.inspect_passive(PROFILE)
    inspection = inspect_hardware(PROFILE, live=live)

    assert result and result["passed"] is True
    assert inspection["mcu"] == "ESP8266EX"
    assert inspection["classification"] == "microcontroller_board"
    assert any(item["id"] == "wifi_24" and item["status"] == "verified" for item in inspection["capabilities"])
    assert not any(item["id"] == "ble" for item in inspection["capabilities"])
    assert any(item["id"] == "spi_flash" and "4MB" in item["name"] for item in inspection["components"])
    assert any(pin["name"] == "D1" and "SCL" in pin["aliases"] for pin in inspection["pins"])
    assert {layer["id"] for layer in inspection["identity_layers"]} >= {"host_interface", "processor", "radio", "flash", "board"}


def test_declared_nodemcu_profile_adds_photo_verified_board_components(monkeypatch) -> None:
    monkeypatch.setattr("app.device_intelligence.arduino_board_inventory", lambda force=False: {})
    probe = espressif._parse_probe(ESPTOOL_OUTPUT)
    espressif._PROBE_CACHE["COM11"] = (espressif.time.time(), probe)
    live = EspressifRomAdapter().inspect_passive(PROFILE)

    inspection = inspect_hardware(PROFILE, live=live, assigned_model="NodeMCU ESP8266 development board (ESP-12E/F)")

    component_ids = {item["id"] for item in inspection["components"]}
    assert {"esp8266ex", "spi_flash", "usb_uart_bridge", "esp12_module", "ams1117"} <= component_ids
