from __future__ import annotations

import base64
import io
import time
import zipfile

import pytest

from app.hardware_definitions import DefinitionError, import_hardware_definition


SVD = """<?xml version="1.0"?>
<device><vendor>Acme</vendor><name>ACM32</name><description>Fixture MCU</description>
<cpu><name>CM4</name><revision>r0p1</revision><endian>little</endian></cpu>
<peripherals><peripheral><name>GPIOA</name><baseAddress>0x40020000</baseAddress>
<interrupt><name>GPIO_IRQ</name><value>6</value></interrupt><registers><register><name>MODER</name>
<addressOffset>0x00</addressOffset><size>32</size><access>read-write</access><resetValue>0</resetValue>
<fields><field><name>MODE0</name><bitOffset>0</bitOffset><bitWidth>2</bitWidth></field></fields>
</register></registers></peripheral></peripherals></device>"""


DTS = """/dts-v1/;
/ {
  compatible = "acme,fixture-board";
  aliases { sensor0 = &imu; };
  i2c0: i2c@40003000 {
    compatible = "acme,i2c";
    status = "okay";
    reg = <0x40003000 0x1000>;
    imu: sensor@68 { compatible = "invensense,mpu6050"; reg = <0x68>; };
  };
};"""


KICAD_SCHEMATIC = """(kicad_sch
  (version 20231120)
  (generator eeschema)
  (symbol
    (lib_id "Device:R")
    (unit 1)
    (uuid "component-1")
    (property "Reference" "R1")
    (property "Value" "10k")
    (property "Footprint" "Resistor_SMD:R_0603")
    (property "Datasheet" "https://example.test/r")
    (pin "1" (uuid "pin-1"))
    (pin "2" (uuid "pin-2")))
  (wire (pts (xy 10 20) (xy 30 20)) (uuid "wire-1"))
  (label "SENSE" (at 30 20 0) (uuid "label-1"))
  (junction (at 30 20) (uuid "junction-1"))
  (no_connect (at 50 50) (uuid "nc-1")))"""


FRITZING_PART = """<?xml version="1.0" encoding="UTF-8"?>
<module moduleId="fixture.part">
  <version>1</version><author>Fixture</author><title>Fixture sensor</title><label>U</label>
  <taxonomy>Sensors</taxonomy>
  <properties><property name="family">Fixture</property><property name="variant">I2C</property></properties>
  <views><breadboardView><layers image="breadboard/fixture.svg" /></breadboardView></views>
  <connectors>
    <connector id="connector0" name="VCC" type="male"><description>Power</description><views><breadboardView><p svgId="connector0pin" terminalId="connector0terminal" /></breadboardView></views></connector>
    <connector id="connector1" name="SDA" type="male"><description>Data</description><views><breadboardView><p svgId="connector1pin" /></breadboardView></views></connector>
  </connectors>
  <buses><bus id="i2c"><nodeMember connectorId="connector1" /></bus></buses>
</module>"""


def test_import_cmsis_svd_maps_registers_fields_and_interrupts() -> None:
    result = import_hardware_definition("cmsis-svd", SVD, "ACM32.svd")
    assert result["scope"] == "mcu_internal"
    assert result["device"] == "ACM32"
    assert result["peripherals"][0]["base_address"] == 0x40020000
    assert result["peripherals"][0]["registers"][0]["fields"][0]["bit_width"] == 2
    assert result["counts"] == {"peripherals": 1, "registers": 1, "fields": 1, "interrupts": 1}


def test_import_zephyr_devicetree_maps_board_topology() -> None:
    result = import_hardware_definition("zephyr-devicetree", DTS, "zephyr.dts")
    assert result["scope"] == "board_topology"
    assert any(item["compatible"] == "invensense,mpu6050" for item in result["components"])
    assert any(item["name"] == "i2c" for item in result["buses"])
    assert result["provenance"]["confidence"] == "definition_exact"
    bus = next(item for item in result["buses"] if item["name"] == "i2c")
    assert bus["properties"]["reg"] == [0x40003000, 0x1000]
    assert bus["compatible"] == "acme,i2c"
    assert "invensense,mpu6050" not in str(bus["properties"])


def test_devicetree_import_scales_linearly_for_large_generated_board() -> None:
    nodes = "\n".join(
        f'  sensor{i}: sensor@{i:x} {{ compatible = "acme,sensor-{i}"; reg = <0x{i:x}>; }};'
        for i in range(2000)
    )
    started = time.perf_counter()
    result = import_hardware_definition("dts", f"/dts-v1/;\n/ {{\n{nodes}\n}};", "large-zephyr.dts")
    elapsed = time.perf_counter() - started
    assert result["counts"]["components"] == 2000
    assert elapsed < 2.0


def test_import_kicad_schematic_preserves_design_components_and_nets() -> None:
    result = import_hardware_definition("kicad-schematic", KICAD_SCHEMATIC, "fixture.kicad_sch")
    assert result["scope"] == "design_evidence"
    assert result["components"][0] == {
        "reference": "R1",
        "value": "10k",
        "lib_id": "Device:R",
        "footprint": "Resistor_SMD:R_0603",
        "datasheet": "https://example.test/r",
        "unit": 1,
        "uuid": "component-1",
        "pins": ["1", "2"],
    }
    assert result["wires"][0]["points"] == [[10.0, 20.0], [30.0, 20.0]]
    assert result["labels"][0]["name"] == "SENSE"
    assert result["counts"] == {
        "components": 1,
        "pins": 2,
        "wires": 1,
        "labels": 1,
        "junctions": 1,
        "no_connects": 1,
    }


def test_kicad_import_ignores_library_symbol_declarations() -> None:
    content = """(kicad_sch (version 20231120) (lib_symbols (symbol "Device:R"))
      (wire (pts (xy 0 0) (xy 1 1)) (uuid "wire")))"""
    result = import_hardware_definition("kicad", content, "library-boundary.kicad_sch")
    assert result["counts"]["components"] == 0
    assert result["counts"]["wires"] == 1


def test_import_fritzing_part_preserves_connectors_and_svg_bindings() -> None:
    result = import_hardware_definition("fritzing-part", FRITZING_PART, "fixture.fzp")
    assert result["scope"] == "component_definition"
    assert result["title"] == "Fixture sensor"
    assert result["properties"] == {"family": "Fixture", "variant": "I2C"}
    assert result["connectors"][0]["views"]["breadboardView"] == {
        "svgId": "connector0pin",
        "terminalId": "connector0terminal",
    }
    assert result["views"]["breadboardView"]["image"] == "breadboard/fixture.svg"
    assert result["buses"] == [{"id": "i2c", "members": ["connector1"]}]


def test_import_fritzing_bundle_sanitizes_and_embeds_visual_assets() -> None:
    bundle = io.BytesIO()
    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" onclick="alert(1)"><script>alert(1)</script><rect id="connector0pin" width="10" height="10"/><image href="https://example.test/tracker.png"/></svg>'''
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("part.fixture.fzp", FRITZING_PART)
        archive.writestr("svg.breadboard.fixture.svg", svg)
    result = import_hardware_definition("fzpz", base64.b64encode(bundle.getvalue()).decode(), "fixture.fzpz")
    assert result["format"] == "fritzing-bundle"
    assert result["counts"]["visual_assets"] == 1
    sanitized = result["visual_assets"][0]["svg"]
    assert "script" not in sanitized
    assert "onclick" not in sanitized
    assert "https://" not in sanitized
    assert "connector0pin" in sanitized


def test_import_fritzing_bundle_rejects_path_traversal() -> None:
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("../part.fzp", FRITZING_PART)
    with pytest.raises(DefinitionError, match="unsafe path"):
        import_hardware_definition("fzpz", base64.b64encode(bundle.getvalue()).decode(), "unsafe.fzpz")


def test_definition_import_rejects_unknown_format() -> None:
    with pytest.raises(DefinitionError, match="Supported definition formats"):
        import_hardware_definition("binary", "abc", "file.bin")
