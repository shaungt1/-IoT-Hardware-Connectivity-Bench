from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .firmware_intelligence import FirmwareAnalysisError, analyze_firmware


class EmulationError(ValueError):
    pass


def renode_path(root: Path) -> Path | None:
    configured = os.getenv("IOT_BENCH_RENODE")
    candidates = [Path(configured)] if configured else []
    candidates.extend((root / ".tools" / "renode").glob("**/renode.exe"))
    return next((item for item in candidates if item.is_file()), None)


def platform_catalog(root: Path, identity: str = "") -> dict[str, Any]:
    executable = renode_path(root)
    if executable is None:
        return {"engine": "renode", "installed": False, "platforms": [], "exact_match": None}
    boards = executable.parent / "platforms" / "boards"
    query_tokens = {token for token in re.findall(r"[a-z0-9]+", identity.lower()) if len(token) > 2}
    platforms = []
    for path in sorted(boards.glob("*.repl")):
        identifier = path.stem
        tokens = set(re.findall(r"[a-z0-9]+", identifier.lower()))
        score = len(query_tokens & tokens)
        platforms.append({
            "id": identifier,
            "label": identifier.replace("_", " ").replace("-", " "),
            "definition": f"platforms/boards/{path.name}",
            "match_score": score,
            "source": "Installed Renode platform library",
        })
    platforms.sort(key=lambda item: (-item["match_score"], item["label"]))
    exact = next((item for item in platforms if item["match_score"] >= 2), None)
    return {
        "engine": "renode",
        "installed": True,
        "version": _version(executable),
        "count": len(platforms),
        "identity": identity,
        "exact_match": exact,
        "platforms": platforms,
        "limitation": "A platform definition models a supported virtual board; it does not prove the identity of connected hardware.",
    }


def verify_platform(root: Path, platform_id: str) -> dict[str, Any]:
    executable = renode_path(root)
    if executable is None:
        raise EmulationError("Renode is not installed")
    catalog = platform_catalog(root)
    platform = next((item for item in catalog["platforms"] if item["id"] == platform_id), None)
    if platform is None:
        raise EmulationError("Platform is not in the installed Renode board library")
    command = f"mach create; machine LoadPlatformDescription @{platform['definition']}; peripherals; quit"
    try:
        result = subprocess.run(
            [str(executable), "--disable-gui", "--plain", "--console", "-e", command],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
            cwd=executable.parent,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EmulationError(f"Renode platform verification failed: {error}") from error
    output = (result.stdout + "\n" + result.stderr).replace("\r", "")
    if result.returncode != 0 or "available peripherals:" not in output.lower():
        raise EmulationError("Renode could not load the selected platform definition")
    peripherals = []
    for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]*) \(([^)]+)\)", output):
        record = {"name": match.group(1), "model": match.group(2)}
        if record not in peripherals:
            peripherals.append(record)
    return {
        "engine": "renode",
        "version": catalog["version"],
        "platform": platform,
        "loaded": True,
        "peripheral_count": len(peripherals),
        "peripherals": peripherals,
        "architectures": _platform_architectures(peripherals),
        "firmware_executed": False,
        "physical_hardware_changed": False,
    }


def run_firmware(
    root: Path,
    platform_id: str,
    firmware: bytes,
    filename: str,
    runtime_ms: int = 50,
    proof_address: int | None = None,
    proof_value: int | None = None,
) -> dict[str, Any]:
    if not 10 <= runtime_ms <= 1000:
        raise EmulationError("Firmware runtime must be between 10 and 1000 ms")
    if proof_value is not None and proof_address is None:
        raise EmulationError("A proof value requires a proof address")
    try:
        analysis = analyze_firmware(firmware, filename)
    except FirmwareAnalysisError as error:
        raise EmulationError(str(error)) from error
    if analysis["format"] != "elf":
        raise EmulationError("Renode execution currently accepts structured ELF firmware only")

    platform_report = verify_platform(root, platform_id)
    architecture = analysis.get("architecture")
    compatible = platform_report["architectures"]
    if not architecture or architecture not in compatible:
        expected = ", ".join(compatible) or "an architecture reported by the virtual CPU"
        raise EmulationError(f"ELF architecture {architecture or 'unknown'} is not compatible with {platform_id}; expected {expected}")

    executable = renode_path(root)
    if executable is None:
        raise EmulationError("Renode is not installed")
    temp_root = executable.parent / "tmp"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="iot-bench-", dir=temp_root) as directory:
        guest = Path(directory) / "guest.elf"
        guest.write_bytes(firmware)
        definition = platform_report["platform"]["definition"]
        command = (
            f"mach create; machine LoadPlatformDescription @{definition}; "
            f"sysbus LoadELF @{guest.as_posix()}; start; sleep {runtime_ms / 1000:.3f}; pause; "
        )
        if proof_address is not None:
            command += f"sysbus ReadDoubleWord 0x{proof_address:08X}; "
        command += "quit"
        try:
            result = subprocess.run(
                [str(executable), "--disable-gui", "--plain", "--console", "-e", command],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                cwd=executable.parent,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise EmulationError(f"Renode firmware execution failed: {error}") from error

    output = (result.stdout + "\n" + result.stderr).replace("\r", "")
    loaded = "loading block of" in output.lower()
    started = "machine started" in output.lower()
    paused = "machine paused" in output.lower()
    if result.returncode != 0 or not (loaded and started and paused):
        raise EmulationError("Renode did not complete the bounded firmware run")
    observed = None
    if proof_address is not None:
        matches = re.findall(r"(?m)^0x([0-9A-Fa-f]{8})\s*$", output)
        observed = int(matches[-1], 16) if matches else None
    proof_matched = proof_value is not None and observed == proof_value
    return {
        "engine": "renode",
        "version": platform_report["version"],
        "platform": platform_report["platform"],
        "firmware": {
            "filename": analysis["filename"],
            "sha256": analysis["sha256"],
            "format": analysis["format"],
            "architecture": architecture,
            "size_bytes": analysis["size_bytes"],
        },
        "runtime_ms": runtime_ms,
        "firmware_loaded": loaded,
        "firmware_executed": started and paused,
        "execution_proven": proof_matched,
        "proof": {
            "address": f"0x{proof_address:08X}" if proof_address is not None else None,
            "expected": f"0x{proof_value:08X}" if proof_value is not None else None,
            "observed": f"0x{observed:08X}" if observed is not None else None,
        },
        "trace": [line.strip() for line in output.splitlines() if any(token in line.lower() for token in ("loading block", "initial values", "machine started", "machine paused"))][:20],
        "physical_hardware_changed": False,
        "safety": {
            "platform_allowlisted": True,
            "architecture_checked": True,
            "runtime_bounded": True,
            "process_timeout_seconds": 30,
            "guest_file_deleted": not guest.exists(),
        },
    }


def _platform_architectures(peripherals: list[dict[str, str]]) -> list[str]:
    models = " ".join(item["model"] for item in peripherals).lower()
    architectures = []
    for token, label in (("cortex", "ARM"), ("arm", "ARM"), ("riscv", "RISC-V"), ("xtensa", "Xtensa"), ("avr", "AVR"), ("x86", "x86")):
        if token in models and label not in architectures:
            architectures.append(label)
    return architectures


def _version(executable: Path) -> str:
    try:
        result = subprocess.run([str(executable), "--version"], capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "installed"
    match = re.search(r"Renode v([^\s]+)", result.stdout)
    return match.group(1) if match else "installed"
