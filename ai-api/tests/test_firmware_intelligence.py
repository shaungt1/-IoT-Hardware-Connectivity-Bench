from __future__ import annotations

import base64
import asyncio
import struct

from fastapi import HTTPException

from app.firmware_intelligence import FirmwareAnalysisError, analyze_firmware
from app.main import FirmwareAnalysisRequest, firmware_analysis


def test_analyzes_elf_architecture_without_executing_input() -> None:
    payload = bytearray(64)
    payload[:6] = b"\x7fELF\x01\x01"
    payload[18:20] = (243).to_bytes(2, "little")
    payload[24:48] = b"https://device.local/v1\x00"
    result = analyze_firmware(bytes(payload), "target.elf")
    assert result["format"] == "elf"
    assert result["architecture"] == "RISC-V"
    assert result["urls"] == ["https://device.local/v1"]
    assert result["safety"]["uploaded_bytes_executed"] is False


def test_analyzes_valid_uf2_blocks() -> None:
    block = bytearray(512)
    struct.pack_into("<8I", block, 0, 0x0A324655, 0x9E5D5157, 0x2000, 0x10000000, 4, 0, 1, 0xE48BFF56)
    struct.pack_into("<I", block, 508, 0x0AB16F30)
    result = analyze_firmware(bytes(block), "target.uf2")
    assert result["format"] == "uf2"
    assert result["format_details"]["valid_blocks"] == 1
    assert result["format_details"]["family_ids"] == ["0xe48bff56"]


def test_analyzes_intel_hex_checksum() -> None:
    result = analyze_firmware(b":0400000001020304F2\n:00000001FF\n", "target.hex")
    assert result["format"] == "intel-hex"
    assert result["format_details"]["valid_checksums"] is True
    assert result["format_details"]["payload_bytes"] == 4


def test_analyzes_espressif_image_header() -> None:
    result = analyze_firmware(b"\xe9\x03\x02\x20" + struct.pack("<I", 0x40001000), "target.bin")
    assert result["format"] == "espressif-image"
    assert result["format_details"]["segment_count"] == 3
    assert result["format_details"]["entry_address"] == "0x40001000"


def test_rejects_empty_input() -> None:
    try:
        analyze_firmware(b"", "empty.bin")
    except FirmwareAnalysisError as error:
        assert "empty" in str(error).lower()
    else:
        raise AssertionError("empty firmware should be rejected")


def test_firmware_analysis_api_rejects_invalid_base64() -> None:
    try:
        asyncio.run(firmware_analysis(FirmwareAnalysisRequest(filename="bad.bin", content_base64="%%%")))
    except HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("invalid base64 should be rejected")


def test_firmware_analysis_api_returns_static_report() -> None:
    payload = b"\xe9\x01\x00\x00" + struct.pack("<I", 0x40000000)
    response = asyncio.run(firmware_analysis(FirmwareAnalysisRequest(
        filename="firmware.bin",
        content_base64=base64.b64encode(payload).decode("ascii"),
    )))
    assert response["safety"]["uploaded_bytes_executed"] is False
