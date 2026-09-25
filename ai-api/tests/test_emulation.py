from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess

import pytest

from app.emulation import EmulationError, platform_catalog, run_firmware, verify_platform


ROOT = Path(__file__).resolve().parents[2]


def test_catalog_only_lists_installed_board_definitions() -> None:
    catalog = platform_catalog(ROOT, "Arduino Nano 33 BLE")
    if not catalog["installed"]:
        pytest.skip("local Renode resource is not installed")
    ids = {item["id"] for item in catalog["platforms"]}
    assert "arduino_nano_33_ble" in ids
    assert catalog["exact_match"]["id"] == "arduino_nano_33_ble"
    assert all(".." not in item["definition"] for item in catalog["platforms"])


def test_installed_renode_loads_platform_without_guest_firmware() -> None:
    if not platform_catalog(ROOT)["installed"]:
        pytest.skip("local Renode resource is not installed")
    report = verify_platform(ROOT, "arduino_nano_33_ble")
    assert report["loaded"] is True
    assert report["firmware_executed"] is False
    assert report["physical_hardware_changed"] is False
    assert any(item["name"] == "cpu" for item in report["peripherals"])
    assert "ARM" in report["architectures"]


def test_installed_renode_runs_compatible_elf_and_reads_proof(tmp_path: Path) -> None:
    if not platform_catalog(ROOT)["installed"]:
        pytest.skip("local Renode resource is not installed")
    compiler = shutil.which("arm-none-eabi-gcc")
    if compiler is None:
        candidate = Path.home() / ".platformio" / "packages" / "toolchain-gccarmnoneeabi" / "bin" / ("arm-none-eabi-gcc.exe" if os.name == "nt" else "arm-none-eabi-gcc")
        compiler = str(candidate) if candidate.is_file() else None
    if compiler is None:
        pytest.skip("ARM cross compiler is not installed")
    firmware = tmp_path / "guest.elf"
    subprocess.run([
        compiler,
        "-mcpu=cortex-m4",
        "-mthumb",
        "-nostdlib",
        "-Wl,--build-id=none",
        f"-Wl,-T,{ROOT / 'ai-api' / 'tests' / 'fixtures' / 'cortex_m_guest.ld'}",
        "-o",
        str(firmware),
        str(ROOT / "ai-api" / "tests" / "fixtures" / "cortex_m_guest.c"),
    ], check=True, capture_output=True)
    report = run_firmware(
        ROOT,
        "arduino_nano_33_ble",
        firmware.read_bytes(),
        firmware.name,
        runtime_ms=50,
        proof_address=0x20000000,
        proof_value=0xC0DEC0DE,
    )
    assert report["firmware_executed"] is True
    assert report["execution_proven"] is True
    assert report["proof"]["observed"] == "0xC0DEC0DE"
    assert report["physical_hardware_changed"] is False
    assert report["safety"]["guest_file_deleted"] is True


def test_renode_execution_rejects_non_elf() -> None:
    with pytest.raises(EmulationError, match="ELF"):
        run_firmware(ROOT, "arduino_nano_33_ble", b"not an elf", "firmware.bin")
