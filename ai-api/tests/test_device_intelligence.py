from app.device_intelligence import apply_runtime_identity, enrich_hardware_list, inspect_hardware


def nano_profile() -> dict:
    return {
        "id": "serial:COM10",
        "kind": "serial",
        "device": "COM10",
        "name": "USB Serial Device (COM10)",
        "description": "USB Serial Device (COM10)",
        "manufacturer": "Microsoft",
        "serial_number": "C987EF1FB5A08A70",
        "vid": "2341",
        "pid": "805A",
        "is_esp32": False,
        "is_lichee": False,
        "transport": "USB serial",
    }


def test_nano_family_has_sourced_variant_components() -> None:
    result = inspect_hardware(nano_profile())

    assert result["family"] == "Arduino Nano 33 BLE family"
    assert result["mcu"] == "Nordic nRF52840"
    assert "Arduino Nano 33 BLE Sense (original)" in result["candidates"]
    assert any(component["id"] == "lsm9ds1" for component in result["components"])
    assert all(component["status"] == "expected" for component in result["components"])
    assert result["tests"][-1]["available"] is False


def test_assigned_model_does_not_promote_expected_components_to_verified() -> None:
    result = inspect_hardware(nano_profile(), assigned_model="Arduino Nano 33 BLE Sense (original)")

    assert result["model"] == "Arduino Nano 33 BLE Sense (original)"
    assert next(item for item in result["components"] if item["id"] == "apds9960")["status"] == "expected"
    assert not any(item["id"] == "bmi270" for item in result["components"])


def test_regular_nano_model_does_not_claim_sense_sensors() -> None:
    result = inspect_hardware(nano_profile(), assigned_model="Arduino Nano 33 BLE")

    assert [item["id"] for item in result["components"]] == ["nrf52840"]
    assert not any(test["id"] == "sensor_diagnostic" for test in result["tests"])


def test_enrichment_uses_catalog_without_opening_serial(monkeypatch) -> None:
    monkeypatch.setattr("app.device_intelligence.arduino_board_inventory", lambda force=False: {})

    result = enrich_hardware_list([nano_profile()])[0]

    assert result["name"] == "Arduino Nano 33 BLE family"
    assert result["classification"] == "microcontroller_board"


def test_cp2102_never_claims_a_target_from_bridge_identity_alone(monkeypatch) -> None:
    monkeypatch.setattr("app.device_intelligence.arduino_board_inventory", lambda force=False: {})
    profile = {
        "id": "serial:COM9",
        "kind": "serial",
        "device": "COM9",
        "name": "CP210x USB to UART Bridge",
        "vid": "10C4",
        "pid": "EA60",
    }

    bridge_only = inspect_hardware(profile)
    assert not bridge_only["components"]
    assert bridge_only["candidates"] == ["Silicon Labs CP210x USB-to-UART bridge"]
    assert not any(item["id"] in {"wifi_24", "ble"} for item in bridge_only["capabilities"])
    assert any("bridge, not the processor" in limitation for limitation in bridge_only["limitations"])


def test_live_sensor_manifest_enables_individual_nano_tests() -> None:
    live = {
        "diagnostic": {
            "ready": True,
            "protocol": "iot-bench-sensors/1",
            "sensors": {"lsm9ds1": True, "apds9960": True, "hts221": False, "lps22hb": True, "mp34dt05": True},
        }
    }

    result = inspect_hardware(nano_profile(), live=live, assigned_model="Arduino Nano 33 BLE Sense (original)")

    tests = {test["id"]: test for test in result["tests"]}
    assert tests["sensor:lsm9ds1"]["available"] is True
    assert tests["sensor:hts221"]["available"] is False
    assert tests["serial_protocol"]["available"] is True
    assert tests["i2c_inventory"]["available"] is True
    assert next(component for component in result["components"] if component["id"] == "lsm9ds1")["status"] == "verified"


def test_lichee_usb_identity_without_runtime_does_not_claim_linux_is_live(monkeypatch) -> None:
    monkeypatch.setattr("app.device_intelligence.arduino_board_inventory", lambda force=False: {})
    profile = {
        "id": "usb:359F:2120:1:28",
        "kind": "usb_identity",
        "device": "USB 1:28",
        "name": "Sipeed LicheeRV Nano",
        "vid": "359F",
        "pid": "2120",
    }

    result = inspect_hardware(profile)

    assert "not verified" in result["runtime"]
    assert next(item for item in result["capabilities"] if item["id"] == "linux")["status"] == "expected"
    assert result["services"] == []


def test_raw_usb_device_keeps_host_classification_during_inspection(monkeypatch) -> None:
    monkeypatch.setattr("app.device_intelligence.arduino_board_inventory", lambda force=False: {})
    profile = {
        "id": "usb:046D:0944:1:27",
        "kind": "usb_identity",
        "device": "USB 1:27",
        "name": "Logitech MX Brio",
        "vid": "046D",
        "pid": "0944",
        "classification": "camera_peripheral",
        "confidence": 0.99,
    }

    result = inspect_hardware(profile)

    assert result["model"] == "Logitech MX Brio"
    assert result["classification"] == "camera_peripheral"
    assert {item["id"] for item in result["capabilities"]} == {"usb", "camera"}


def test_compatible_runtime_merges_camera_ble_wifi_and_health_tests(monkeypatch) -> None:
    monkeypatch.setattr("app.device_intelligence.arduino_board_inventory", lambda force=False: {})
    profile = {
        "id": "serial:COM6",
        "kind": "serial",
        "device": "COM6",
        "name": "USB JTAG/serial debug unit",
        "vid": "303A",
        "pid": "1001",
    }
    live = {
        "telemetry": {
            "device": "XIAO-ESP32S3-SENSE-TEST",
            "firmware": "iot-test-0.4.1",
            "camera_ready": True,
            "camera_sensor_pid": 0x60,
            "ble_advertising": True,
            "wifi_ap_active": True,
            "wifi_station_connected": True,
        }
    }

    result = inspect_hardware(profile, live=live)

    capability_ids = {item["id"] for item in result["capabilities"]}
    component_ids = {item["id"] for item in result["components"]}
    tests = {item["id"]: item for item in result["tests"]}
    assert {"camera", "ble", "wifi_24"} <= capability_ids
    assert {"runtime_camera", "runtime_ble_radio", "runtime_wifi_radio"} <= component_ids
    assert result["runtime"] == "iot-test-0.4.1"
    assert tests["camera_stream"]["available"] is True
    assert tests["ble_runtime"]["available"] is True
    assert tests["wifi_runtime"]["available"] is True


def test_authenticated_xiao_runtime_replaces_generic_espressif_family(monkeypatch) -> None:
    monkeypatch.setattr("app.device_intelligence.arduino_board_inventory", lambda force=False: {})
    profile = {
        "id": "serial:COM6",
        "kind": "serial",
        "device": "COM6",
        "name": "Espressif ESP32 USB JTAG/serial family",
        "vid": "303A",
        "pid": "1001",
    }
    live = {
        "telemetry": {
            "device": "XIAO-ESP32S3-SENSE-61C0",
            "firmware": "iot-bench-0.5.0",
            "board_id": "seeed_xiao_esp32s3_sense",
            "board_model": "Seeed Studio XIAO ESP32-S3 Sense",
            "mcu": "Espressif ESP32-S3R8",
            "architecture": "Xtensa LX7 dual-core",
            "pin_map_version": "seeed-xiao-esp32s3-sense-v1",
            "camera_ready": True,
            "camera_sensor_pid": 0x60,
            "psram_bytes": 8_388_608,
            "ble_advertising": True,
            "wifi_ap_active": True,
        }
    }

    result = inspect_hardware(profile, live=live)

    assert result["model"] == "Seeed Studio XIAO ESP32-S3 Sense"
    assert result["mcu"] == "Espressif ESP32-S3R8"
    assert result["confidence"] == 0.99
    assert len(result["pins"]) == 14
    assert [pin["name"] for pin in result["pins"][:2]] == ["D0", "D1"]
    assert result["pins"][0]["electrical"]["absolute_input_max_v"] == 3.6
    assert result["pins"][0]["electrical"]["five_volt_tolerant"] is False
    assert next(pin for pin in result["pins"] if pin["name"] == "5V")["electrical"]["rail"] == "USB VBUS"
    assert {"sense_camera", "sense_microphone", "sense_microsd", "psram_8mb"} <= {
        component["id"] for component in result["components"]
    }


def test_authenticated_runtime_promotes_host_inventory_identity() -> None:
    inventory = [{
        "id": "serial:COM6",
        "kind": "serial",
        "device": "COM6",
        "name": "Espressif ESP32 USB JTAG/serial family",
        "confidence": 0.82,
    }]
    snapshot = {
        "connected": True,
        "port": "COM6",
        "telemetry": {
            "device": "XIAO-ESP32S3-SENSE-TEST",
            "board_id": "seeed_xiao_esp32s3_sense",
            "board_model": "Seeed Studio XIAO ESP32-S3 Sense",
        },
    }

    result = apply_runtime_identity(inventory, snapshot)

    assert result[0]["name"] == "Seeed Studio XIAO ESP32-S3 Sense"
    assert result[0]["runtime_identity_verified"] is True
    assert result[0]["confidence"] == 0.99
    assert inventory[0]["name"] == "Espressif ESP32 USB JTAG/serial family"
