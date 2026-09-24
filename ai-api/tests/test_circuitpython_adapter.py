from app.adapters import circuitpython
from app.adapters.circuitpython import CircuitPythonAdapter


def feather_profile() -> dict:
    return {
        "id": "serial:COM8",
        "kind": "serial",
        "device": "COM8",
        "name": "Adafruit Feather M0 Express",
        "vid": "239A",
        "pid": "8023",
    }


def test_feather_passive_adapter_exposes_runtime_pins_and_tests(monkeypatch) -> None:
    monkeypatch.setattr(circuitpython, "_find_volume", lambda profile: {
        "path": "F:\\",
        "version": "2.2.4 on 2018-03-07",
        "size_bytes": 2_072_576,
        "free_bytes": 1_819_648,
        "code_files": ["main.py"],
        "imports": ["board", "digitalio"],
        "libraries": ["neopixel.mpy"],
        "label": "CIRCUITPY",
        "boot": "Adafruit CircuitPython 2.2.4; Adafruit Feather M0 Express with samd21g18",
    })
    circuitpython._PROBE_CACHE.clear()

    adapter = CircuitPythonAdapter()
    result = adapter.inspect_passive(feather_profile())

    assert adapter.supports(feather_profile()) is True
    assert result["telemetry"]["firmware"].startswith("CircuitPython 2.2.4")
    assert len(result["pins"]) == 29
    assert {test["id"] for test in result["tests"]} == {
        "circuitpython_storage",
        "circuitpython_runtime_probe",
        "circuitpython_i2c_scan",
    }
    assert all(test["available"] for test in result["tests"])


def test_probe_parser_keeps_stable_and_transient_i2c_evidence_separate() -> None:
    parsed = circuitpython._parse_probe(
        "\n".join([
            "__BENCH_PINS=SDA,SCL,D13",
            "__BENCH_HEAP=17024",
            "__BENCH_FREQUENCY=47972352",
            "__BENCH_I2C=44",
            "__BENCH_I2C_SEEN=1F,44,62",
            "__BENCH_DONE=1",
        ])
    )

    assert parsed["ready"] is True
    assert parsed["i2c_addresses"] == [0x44]
    assert parsed["i2c_seen_addresses"] == [0x1F, 0x44, 0x62]
    assert parsed["pins"] == ["SDA", "SCL", "D13"]
