from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".h", ".hpp", ".ino", ".json", ".md", ".py",
    ".toml", ".txt", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".csv",
}
MAX_TEXT_BYTES = 512 * 1024


class WorkspaceError(ValueError):
    pass


class DeviceWorkspace:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def roots(self, inspection: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        roots = [
            {
                "id": "bench-firmware",
                "name": "Bench firmware projects",
                "path": str((self.project_root / "firmware").resolve()),
                "writable": True,
                "source": "local project",
            }
        ]
        mount = str(((inspection or {}).get("telemetry") or {}).get("storage_mount") or "").strip()
        if mount:
            candidate = Path(mount)
            if candidate.exists() and candidate.is_dir():
                roots.append(
                    {
                        "id": "device-storage",
                        "name": "Selected device storage",
                        "path": str(candidate.resolve()),
                        "writable": True,
                        "source": "mounted device runtime",
                    }
                )
        return roots

    def inventory(self, inspection: dict[str, Any] | None = None) -> dict[str, Any]:
        roots = self.roots(inspection)
        return {
            "roots": [{key: value for key, value in root.items() if key != "path"} for root in roots],
            "files": [item for root in roots for item in self._walk(root)],
        }

    def read_text(self, root_id: str, relative_path: str, inspection: dict[str, Any] | None = None) -> dict[str, Any]:
        path = self._resolve(root_id, relative_path, inspection)
        if not path.is_file():
            raise WorkspaceError("The requested workspace file does not exist")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            raise WorkspaceError("Only recognized text source and configuration files can be opened")
        payload = path.read_bytes()
        if len(payload) > MAX_TEXT_BYTES:
            raise WorkspaceError("The requested file is larger than the 512 KiB editor limit")
        try:
            content = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise WorkspaceError("The requested file is not UTF-8 text") from error
        return {
            "root_id": root_id,
            "path": relative_path.replace("\\", "/"),
            "content": content,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        }

    def write_text(
        self,
        root_id: str,
        relative_path: str,
        content: str,
        expected_sha256: str,
        inspection: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_TEXT_BYTES:
            raise WorkspaceError("The updated file exceeds the 512 KiB editor limit")
        path = self._resolve(root_id, relative_path, inspection)
        if path.suffix.lower() not in TEXT_SUFFIXES:
            raise WorkspaceError("This file type is not writable through the bench")
        current = path.read_bytes() if path.exists() else b""
        current_hash = hashlib.sha256(current).hexdigest()
        if current_hash != expected_sha256:
            raise WorkspaceError("The file changed after it was opened; refresh it before saving")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
        return {
            "root_id": root_id,
            "path": relative_path.replace("\\", "/"),
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "size": len(encoded),
        }

    def _walk(self, root: dict[str, Any]) -> list[dict[str, Any]]:
        root_path = Path(str(root["path"]))
        if not root_path.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(root_path.rglob("*")):
            relative = path.relative_to(root_path)
            if len(relative.parts) > 5 or any(part.startswith(".") for part in relative.parts):
                continue
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                records.append(
                    {
                        "root_id": root["id"],
                        "path": relative.as_posix(),
                        "name": path.name,
                        "size": path.stat().st_size,
                        "writable": bool(root["writable"]),
                    }
                )
            if len(records) >= 300:
                break
        return records

    def _resolve(self, root_id: str, relative_path: str, inspection: dict[str, Any] | None) -> Path:
        root = next((item for item in self.roots(inspection) if item["id"] == root_id), None)
        if root is None:
            raise WorkspaceError("The requested workspace root is not available for this device")
        clean = Path(relative_path.replace("\\", "/"))
        if clean.is_absolute() or ".." in clean.parts:
            raise WorkspaceError("Workspace paths must remain inside the selected root")
        root_path = Path(str(root["path"])).resolve()
        candidate = (root_path / clean).resolve()
        if candidate != root_path and root_path not in candidate.parents:
            raise WorkspaceError("Workspace paths must remain inside the selected root")
        return candidate
