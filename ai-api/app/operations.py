from __future__ import annotations

import secrets
import hashlib
import json
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .storage import StateStore
from .workspace import DeviceWorkspace, WorkspaceError


APPROVAL_SECONDS = 120
OUTPUT_LIMIT = 64_000


@dataclass
class OperationPlan:
    id: str
    identifier: str
    operation_id: str
    label: str
    risk: str
    description: str
    preview: str
    created_at: float
    parameters: dict[str, Any]
    fingerprint: str
    approval_token: str | None = None
    approved_at: float | None = None


class OperationError(ValueError):
    pass


class OperationManager:
    def __init__(self, root: Path, store: StateStore, workspace: DeviceWorkspace) -> None:
        self.root = root.resolve()
        self.store = store
        self.workspace = workspace
        self._plans: dict[str, OperationPlan] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def capabilities(self, profile: dict[str, Any], inspection: dict[str, Any]) -> list[dict[str, Any]]:
        port = str(profile.get("device") or "") if profile.get("kind") == "serial" else ""
        operations: list[dict[str, Any]] = []
        for project in self._platformio_projects():
            name = project.relative_to(self.root).as_posix()
            compatible, compatibility_reason = self._project_compatibility(project, inspection)
            operations.append(self._capability(
                f"build:{name}", f"Build {project.name}", "read-only",
                "Compile this firmware locally without modifying connected hardware.",
                self._platformio_available(), "PlatformIO is not installed", project=name,
            ))
            operations.append(self._capability(
                f"flash:{name}", f"Flash {project.name}", "destructive",
                f"Build and upload this firmware to {port or 'the selected target'}; the existing program may be replaced.",
                bool(port and self._platformio_available() and compatible),
                compatibility_reason if port and self._platformio_available() else "A serial target and PlatformIO are required", project=name,
            ))
        mcu = str(inspection.get("mcu") or "").upper()
        flash_size = str((inspection.get("telemetry") or {}).get("flash_size") or "")
        operations.append(self._capability(
            "backup:espressif", "Back up Espressif flash", "disruptive",
            "Reset the verified Espressif target into its ROM loader and save a full flash image before changes.",
            bool(port and mcu.startswith("ESP") and flash_size and self._esptool_available()),
            "Run the Espressif identity probe first and ensure esptool is installed",
        ))
        return operations

    def create_plan(
        self,
        profile: dict[str, Any],
        inspection: dict[str, Any],
        operation_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        capability = next((item for item in self.capabilities(profile, inspection) if item["id"] == operation_id), None)
        if capability is None:
            raise OperationError("The requested operation is not defined for this target")
        if not capability["available"]:
            raise OperationError(str(capability["reason"]))
        plan = OperationPlan(
            id=uuid.uuid4().hex,
            identifier=str(profile["id"]),
            operation_id=operation_id,
            label=str(capability["label"]),
            risk=str(capability["risk"]),
            description=str(capability["description"]),
            preview=self._preview(profile, inspection, operation_id),
            created_at=time.time(),
            parameters=dict(parameters or {}),
            fingerprint=self.fingerprint(profile, inspection),
        )
        self._plans[plan.id] = plan
        self.store.record_operation(plan.id, plan.identifier, plan.operation_id, plan.risk, "planned", plan.preview, "")
        return self._public_plan(plan)

    def create_write_plan(
        self,
        identifier: str,
        root_id: str,
        path: str,
        content: str,
        expected_sha256: str,
        fingerprint: str,
    ) -> dict[str, Any]:
        plan = OperationPlan(
            id=uuid.uuid4().hex,
            identifier=identifier,
            operation_id="workspace:write",
            label=f"Save {Path(path).name}",
            risk="disruptive",
            description="Update a source/configuration file in an allowlisted workspace root.",
            preview=f"Write UTF-8 text to {root_id}/{path} after checking its content hash.",
            created_at=time.time(),
            parameters={"root_id": root_id, "relative_path": path, "content": content, "expected_sha256": expected_sha256},
            fingerprint=fingerprint,
        )
        self._plans[plan.id] = plan
        self.store.record_operation(plan.id, identifier, plan.operation_id, plan.risk, "planned", plan.preview, "")
        return self._public_plan(plan)

    def approve(self, plan_id: str, identifier: str) -> dict[str, Any]:
        plan = self._get(plan_id, identifier)
        if time.time() - plan.created_at > APPROVAL_SECONDS:
            raise OperationError("The operation plan expired; create a fresh plan")
        plan.approval_token = secrets.token_urlsafe(24)
        plan.approved_at = time.time()
        self.store.record_operation(plan.id, plan.identifier, plan.operation_id, plan.risk, "approved", plan.preview, "")
        return {**self._public_plan(plan), "approval_token": plan.approval_token}

    def execute(
        self,
        plan_id: str,
        identifier: str,
        approval_token: str | None,
        profile: dict[str, Any],
        inspection: dict[str, Any],
    ) -> dict[str, Any]:
        plan = self._get(plan_id, identifier)
        if plan.fingerprint != self.fingerprint(profile, inspection):
            raise OperationError("The physical target changed after this plan was created; create a fresh plan")
        if plan.risk in {"disruptive", "destructive"}:
            if not plan.approval_token or not secrets.compare_digest(plan.approval_token, approval_token or ""):
                raise OperationError("A matching approval token is required")
            if plan.approved_at is None or time.time() - plan.approved_at > APPROVAL_SECONDS:
                raise OperationError("The operation approval expired; create a fresh plan")
        lock = self._target_lock(identifier)
        if not lock.acquire(blocking=False):
            raise OperationError("Another operation is already using this target")
        started = time.time()
        try:
            if plan.operation_id == "workspace:write":
                result = self.workspace.write_text(inspection=inspection, **plan.parameters)
                output = f"Saved {result['path']} ({result['size']} bytes, sha256 {result['sha256']})."
                return self._finish(plan, True, output, started)
            command = self._command(profile, inspection, plan.operation_id)
            completed = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()[-OUTPUT_LIMIT:]
            return self._finish(plan, completed.returncode == 0, output or "Operation completed without output.", started)
        except (OSError, subprocess.TimeoutExpired, WorkspaceError) as error:
            return self._finish(plan, False, str(error), started)
        finally:
            lock.release()

    def history(self, identifier: str | None = None) -> list[dict[str, Any]]:
        return self.store.operation_history(identifier)

    def _finish(self, plan: OperationPlan, passed: bool, output: str, started: float) -> dict[str, Any]:
        status = "completed" if passed else "failed"
        self.store.record_operation(plan.id, plan.identifier, plan.operation_id, plan.risk, status, plan.preview, output)
        self._plans.pop(plan.id, None)
        return {
            "plan_id": plan.id,
            "operation_id": plan.operation_id,
            "passed": passed,
            "status": status,
            "output": output,
            "duration_ms": round((time.time() - started) * 1000),
        }

    def _command(self, profile: dict[str, Any], inspection: dict[str, Any], operation_id: str) -> list[str]:
        if operation_id.startswith("build:") or operation_id.startswith("flash:"):
            relative = operation_id.split(":", 1)[1]
            project = (self.root / relative).resolve()
            if self.root not in project.parents or not (project / "platformio.ini").is_file():
                raise OperationError("The firmware project is outside the bench workspace")
            command = [sys.executable, "-m", "platformio", "run", "-d", str(project)]
            if operation_id.startswith("flash:"):
                command.extend(["--target", "upload", "--upload-port", str(profile.get("device") or "")])
            return command
        if operation_id == "backup:espressif":
            size = self._flash_bytes(str((inspection.get("telemetry") or {}).get("flash_size") or ""))
            destination = self.root / ".artifacts" / "backups" / f"{profile.get('device')}-{int(time.time())}.bin"
            destination.parent.mkdir(parents=True, exist_ok=True)
            return [sys.executable, "-m", "esptool", "--port", str(profile.get("device")), "read-flash", "0", str(size), str(destination)]
        raise OperationError("The operation has no executable adapter")

    def _preview(self, profile: dict[str, Any], inspection: dict[str, Any], operation_id: str) -> str:
        if operation_id.startswith("build:"):
            return f"Compile {operation_id.split(':', 1)[1]} locally. No target write."
        if operation_id.startswith("flash:"):
            return f"Compile and upload {operation_id.split(':', 1)[1]} to {profile.get('device')}. Existing firmware may be replaced."
        if operation_id == "backup:espressif":
            return f"Read {(inspection.get('telemetry') or {}).get('flash_size')} from {profile.get('device')} into .artifacts/backups."
        return operation_id

    def _platformio_projects(self) -> list[Path]:
        return sorted(path.parent for path in (self.root / "firmware").rglob("platformio.ini"))

    @staticmethod
    def _project_compatibility(project: Path, inspection: dict[str, Any]) -> tuple[bool, str]:
        try:
            manifest = (project / "platformio.ini").read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            return False, "The project manifest could not be read"
        identity = " ".join(
            str(inspection.get(key) or "")
            for key in ("model", "family", "mcu", "architecture")
        ).lower().replace("-", "")
        rules = {
            "seeed_xiao_esp32s3": ("esp32s3", "This project targets a Seeed XIAO ESP32-S3"),
            "board = nano33ble": ("nrf52840", "This project targets an nRF52840 Nano 33 BLE family board"),
        }
        for marker, (identity_marker, reason) in rules.items():
            if marker in manifest:
                return identity_marker in identity, reason
        return False, "The project target is not mapped to this selected board"

    @staticmethod
    def _platformio_available() -> bool:
        try:
            import platformio  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _esptool_available() -> bool:
        try:
            import esptool  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _flash_bytes(value: str) -> int:
        normalized = value.strip().upper()
        if normalized.endswith("MB") and normalized[:-2].strip().isdigit():
            return int(normalized[:-2].strip()) * 1024 * 1024
        raise OperationError("A verified flash size is required before backup")

    @staticmethod
    def _capability(
        operation_id: str,
        label: str,
        risk: str,
        description: str,
        available: bool,
        reason: str,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "id": operation_id,
            "label": label,
            "risk": risk,
            "description": description,
            "available": available,
            "reason": "" if available else reason,
            **extra,
        }

    def _get(self, plan_id: str, identifier: str) -> OperationPlan:
        plan = self._plans.get(plan_id)
        if plan is None or plan.identifier != identifier:
            raise OperationError("The operation plan is missing or belongs to another target")
        return plan

    def _target_lock(self, identifier: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(identifier, threading.Lock())

    @staticmethod
    def fingerprint(profile: dict[str, Any], inspection: dict[str, Any]) -> str:
        adapter = inspection.get("adapter") or {}
        payload = {
            "identifier": profile.get("id"),
            "vid": profile.get("vid"),
            "pid": profile.get("pid"),
            "serial_number": profile.get("serial_number"),
            "model": inspection.get("model"),
            "mcu": inspection.get("mcu"),
            "adapter": adapter.get("id"),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    @staticmethod
    def _public_plan(plan: OperationPlan) -> dict[str, Any]:
        return {
            "plan_id": plan.id,
            "identifier": plan.identifier,
            "operation_id": plan.operation_id,
            "label": plan.label,
            "risk": plan.risk,
            "description": plan.description,
            "preview": plan.preview,
            "requires_approval": plan.risk in {"disruptive", "destructive"},
            "expires_in_seconds": APPROVAL_SECONDS,
        }
