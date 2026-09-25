from __future__ import annotations

import hashlib
import math
import re
import shutil
import struct
from collections import Counter
from pathlib import Path
from typing import Any


MAX_FIRMWARE_BYTES = 16 * 1024 * 1024
PRINTABLE = re.compile(rb"[\x20-\x7e]{4,}")
URL = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)

ELF_MACHINES = {
    3: "x86",
    8: "MIPS",
    40: "ARM",
    62: "x86-64",
    83: "AVR",
    94: "Xtensa",
    183: "AArch64",
    243: "RISC-V",
}

OPTIONAL_ENGINES = (
    ("binwalk", "Binwalk", "container extraction and signatures"),
    ("rizin", "Rizin", "disassembly and binary structure"),
    ("ghidraRun", "Ghidra", "headless decompilation and processor analysis"),
    ("emba", "EMBA", "firmware filesystem and SBOM pipeline"),
)


class FirmwareAnalysisError(ValueError):
    pass


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return round(-sum((count / length) * math.log2(count / length) for count in counts.values()), 4)


def _elf_details(data: bytes) -> dict[str, Any]:
    if len(data) < 20:
        return {}
    byte_order = "little" if data[5] == 1 else "big" if data[5] == 2 else "unknown"
    if byte_order == "unknown":
        return {"class": f"ELF{32 if data[4] == 1 else 64 if data[4] == 2 else '?'}", "byte_order": byte_order}
    machine = int.from_bytes(data[18:20], byte_order)
    return {
        "class": f"ELF{32 if data[4] == 1 else 64 if data[4] == 2 else '?'}",
        "byte_order": byte_order,
        "machine_id": machine,
        "architecture": ELF_MACHINES.get(machine, f"ELF machine {machine}"),
    }


def _uf2_details(data: bytes) -> dict[str, Any]:
    if len(data) < 512:
        return {}
    blocks = len(data) // 512
    families: set[str] = set()
    targets: list[int] = []
    valid = 0
    for offset in range(0, blocks * 512, 512):
        block = data[offset : offset + 512]
        if struct.unpack_from("<I", block, 0)[0] != 0x0A324655 or struct.unpack_from("<I", block, 508)[0] != 0x0AB16F30:
            continue
        _, flags, target, _, _, _, family = struct.unpack_from("<7I", block, 4)
        valid += 1
        targets.append(target)
        if flags & 0x00002000:
            families.add(f"0x{family:08x}")
    return {
        "valid_blocks": valid,
        "total_blocks": blocks,
        "family_ids": sorted(families),
        "target_address_min": f"0x{min(targets):08x}" if targets else None,
        "target_address_max": f"0x{max(targets):08x}" if targets else None,
    }


def _intel_hex_details(data: bytes) -> dict[str, Any]:
    records = 0
    data_bytes = 0
    record_types: Counter[int] = Counter()
    valid = True
    for raw_line in data.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith(b":"):
            valid = False
            break
        try:
            decoded = bytes.fromhex(line[1:].decode("ascii"))
        except (ValueError, UnicodeDecodeError):
            valid = False
            break
        if len(decoded) < 5 or sum(decoded) & 0xFF:
            valid = False
            break
        records += 1
        data_bytes += decoded[0] if decoded[3] == 0 else 0
        record_types[decoded[3]] += 1
    return {"valid_checksums": valid, "records": records, "payload_bytes": data_bytes, "record_types": dict(record_types)}


def _esp_details(data: bytes) -> dict[str, Any]:
    if len(data) < 8:
        return {}
    return {
        "segment_count": data[1],
        "flash_mode": {0: "QIO", 1: "QOUT", 2: "DIO", 3: "DOUT"}.get(data[2], f"mode-{data[2]}"),
        "flash_size_frequency_byte": f"0x{data[3]:02x}",
        "entry_address": f"0x{struct.unpack_from('<I', data, 4)[0]:08x}",
    }


def _detect_format(data: bytes, filename: str) -> tuple[str, dict[str, Any]]:
    if data.startswith(b"\x7fELF"):
        return "elf", _elf_details(data)
    if len(data) >= 512 and struct.unpack_from("<I", data, 0)[0] == 0x0A324655:
        return "uf2", _uf2_details(data)
    if data.lstrip().startswith(b":"):
        return "intel-hex", _intel_hex_details(data)
    if data.startswith(b"\xe9"):
        return "espressif-image", _esp_details(data)
    suffix = Path(filename).suffix.lower()
    return ("raw-binary" if suffix in {".bin", ".img", ".rom", ".fw"} else "unknown"), {}


def analyze_firmware(data: bytes, filename: str) -> dict[str, Any]:
    if not data:
        raise FirmwareAnalysisError("Firmware input is empty")
    if len(data) > MAX_FIRMWARE_BYTES:
        raise FirmwareAnalysisError(f"Firmware input exceeds the {MAX_FIRMWARE_BYTES // (1024 * 1024)} MiB analysis limit")

    file_format, details = _detect_format(data, filename)
    decoded_strings = [match.group().decode("ascii", "replace") for match in PRINTABLE.finditer(data)]
    strings = decoded_strings[:100]
    urls = list(dict.fromkeys(url for value in strings for url in URL.findall(value)))[:25]
    architecture = details.get("architecture")
    evidence = [{
        "claim": f"Container format is {file_format}",
        "status": "verified" if file_format != "unknown" else "unknown",
        "source": "firmware magic and structure",
    }]
    if architecture:
        evidence.append({"claim": f"Target architecture is {architecture}", "status": "verified", "source": "ELF e_machine field"})
    else:
        evidence.append({"claim": "Target architecture is not proven by this file", "status": "unknown", "source": "bounded static analysis"})

    engines = [{
        "id": command.lower(),
        "name": name,
        "purpose": purpose,
        "available": bool(shutil.which(command)),
        "invoked": False,
    } for command, name, purpose in OPTIONAL_ENGINES]

    return {
        "schema_version": "1.0",
        "filename": Path(filename).name or "firmware.bin",
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "entropy_bits_per_byte": _entropy(data),
        "format": file_format,
        "architecture": architecture,
        "format_details": details,
        "strings": strings,
        "urls": urls,
        "engines": engines,
        "evidence": evidence,
        "safety": {
            "uploaded_bytes_executed": False,
            "external_engines_invoked": False,
            "maximum_input_bytes": MAX_FIRMWARE_BYTES,
        },
    }
