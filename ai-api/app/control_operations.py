from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

from .control_profile import build_control_profile
from .storage import StateStore


APPROVAL_SECONDS = 120


@dataclass
class ControlPlan:
    id: str
    identifier: str
    action: str
    pin: str
    value: int | None
    command: str
    fingerprint: str
    created_at: float
    approval_token: str | None = None
    approved_at: float | None = None


class ControlError(ValueError):
    pass


class ControlOperationManager:
    def __init__(self, store: StateStore) -> None:
        self.store = store
        self._plans: dict[str, ControlPlan] = {}
        self._guard = threading.Lock()

    def create_plan(
        self,
        identifier: str,
        action: str,
        pin: str,
        value: int | None,
        inspection: dict[str, Any],
        connected: bool,
    ) -> dict[str, Any]:
        profile = build_control_profile(inspection, connected)
        capability = next((item for item in profile["capabilities"] if item["id"] == action), None)
        if capability is None or not capability["available"]:
            raise ControlError(capability["reason"] if capability else "Unknown physical-control action")
        defined_pin = next((item for item in inspection.get("pins") or [] if str(item.get("name")) == pin), None)
        if defined_pin is None:
            raise ControlError("The requested pin is not in the verified external pin map")
        functions = " ".join(str(item) for item in defined_pin.get("functions") or []).lower()
        if pin.upper() in {"GND", "3V3", "5V", "VBUS"} or "power" in functions or "ground" in functions:
            raise ControlError("Power and ground terminals cannot be used as runtime I/O")
        if action == "gpio_write" and value not in {0, 1}:
            raise ControlError("GPIO writes require a value of 0 or 1")
        if action != "gpio_write" and value is not None:
            raise ControlError("This read action does not accept a value")
        if action == "adc_read" and not any("adc" in str(item).lower() or "analog" in str(item).lower() for item in defined_pin.get("functions") or []):
            raise ControlError("The verified pin map does not expose ADC on this terminal")
        command = {
            "gpio_read": f"GPIO READ\t{pin}",
            "gpio_write": f"GPIO WRITE\t{pin}\t{value}",
            "adc_read": f"ADC READ\t{pin}",
        }.get(action)
        if command is None:
            raise ControlError("The negotiated action has no installed execution adapter")
        plan = ControlPlan(
            id=uuid.uuid4().hex,
            identifier=identifier,
            action=action,
            pin=pin,
            value=value,
            command=command,
            fingerprint=self.fingerprint(inspection),
            created_at=time.time(),
        )
        with self._guard:
            self._plans[plan.id] = plan
        preview = self._preview(plan)
        self.store.record_operation(plan.id, identifier, f"control:{action}", "disruptive", "planned", preview, "")
        return self._public(plan)

    def approve(self, plan_id: str, identifier: str) -> dict[str, Any]:
        plan = self._get(plan_id, identifier)
        if time.time() - plan.created_at > APPROVAL_SECONDS:
            raise ControlError("The physical-control plan expired")
        plan.approval_token = secrets.token_urlsafe(24)
        plan.approved_at = time.time()
        self.store.record_operation(plan.id, identifier, f"control:{plan.action}", "disruptive", "approved", self._preview(plan), "")
        return {**self._public(plan), "approval_token": plan.approval_token}

    def prepare(self, plan_id: str, identifier: str, approval_token: str | None, inspection: dict[str, Any]) -> ControlPlan:
        plan = self._get(plan_id, identifier)
        if plan.fingerprint != self.fingerprint(inspection):
            raise ControlError("The target identity or verified pin map changed; create a new control plan")
        if not plan.approval_token or not secrets.compare_digest(plan.approval_token, approval_token or ""):
            raise ControlError("A matching physical-control approval token is required")
        if plan.approved_at is None or time.time() - plan.approved_at > APPROVAL_SECONDS:
            raise ControlError("The physical-control approval expired")
        return plan

    def finish(self, plan: ControlPlan, passed: bool, output: str) -> dict[str, Any]:
        status = "completed" if passed else "failed"
        self.store.record_operation(plan.id, plan.identifier, f"control:{plan.action}", "disruptive", status, self._preview(plan), output)
        with self._guard:
            self._plans.pop(plan.id, None)
        return {"plan_id": plan.id, "action": plan.action, "pin": plan.pin, "passed": passed, "status": status, "output": output}

    def cancel_identifier(self, identifier: str) -> int:
        with self._guard:
            plans = [plan for plan in self._plans.values() if plan.identifier == identifier]
            for plan in plans:
                self._plans.pop(plan.id, None)
        for plan in plans:
            self.store.record_operation(plan.id, identifier, f"control:{plan.action}", "disruptive", "cancelled", self._preview(plan), "Target disconnected")
        return len(plans)

    @staticmethod
    def fingerprint(inspection: dict[str, Any]) -> str:
        telemetry = inspection.get("telemetry") or {}
        payload = {
            "identifier": inspection.get("identifier"),
            "board_id": telemetry.get("board_id"),
            "pin_map_version": telemetry.get("pin_map_version"),
            "protocol": telemetry.get("control_protocol"),
            "pins": [item.get("name") for item in inspection.get("pins") or []],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _get(self, plan_id: str, identifier: str) -> ControlPlan:
        with self._guard:
            plan = self._plans.get(plan_id)
        if plan is None or plan.identifier != identifier:
            raise ControlError("The physical-control plan is missing or belongs to another target")
        return plan

    @staticmethod
    def _preview(plan: ControlPlan) -> str:
        return f"{plan.action.replace('_', ' ')} on verified terminal {plan.pin}" + (f" with value {plan.value}" if plan.value is not None else "")

    def _public(self, plan: ControlPlan) -> dict[str, Any]:
        return {
            "plan_id": plan.id,
            "identifier": plan.identifier,
            "action": plan.action,
            "pin": plan.pin,
            "value": plan.value,
            "risk": "disruptive",
            "preview": self._preview(plan),
            "requires_approval": True,
            "expires_in_seconds": APPROVAL_SECONDS,
        }
