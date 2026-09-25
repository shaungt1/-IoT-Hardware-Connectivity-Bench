from __future__ import annotations

import os
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def tool_executable(command: str) -> str | None:
    """Resolve a hardware CLI without importing it into the API environment."""
    resolved = shutil.which(command)
    if resolved:
        return resolved
    suffixes = (".exe", ".cmd", ".bat", "") if os.name == "nt" else ("",)
    script_dirs = (
        PROJECT_ROOT / ".tool-venv" / ("Scripts" if os.name == "nt" else "bin"),
        PROJECT_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin"),
    )
    for scripts in script_dirs:
        for suffix in suffixes:
            candidate = scripts / f"{command}{suffix}"
            if candidate.is_file():
                return str(candidate)
    return None
