from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import os
import struct
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import psutil

from .adapters import adapter_registry, passive_inspect_device, run_adapter_test
from .api_contract import API_VERSION, api_contract
from .ble import BleMonitor
from .bridge import SerialBridge
from .device_intelligence import (
    apply_runtime_identity,
    arduino_board_inventory,
    enrich_hardware_list,
    inspect_hardware,
    metadata_providers,
)
from .device_state import DeviceStateManager
from .discovery_report import build_discovery_report
from .control_profile import build_control_profile
from .probe_matrix import build_probe_matrix
from .pin_attachments import apply_pin_attachments, find_pin
from .control_operations import ControlError, ControlOperationManager
from .host_wifi import scan_host_wifi
from .hardware import discover_usb_network_devices, inspect_usb_network_device, run_usb_network_diagnostic
from .hardware_definitions import DefinitionError, import_hardware_definition
from .evidence_graph import build_evidence_graph
from .evidence_policy import inspection_calibration
from .emulation import EmulationError, platform_catalog, run_firmware, verify_platform
from .firmware_intelligence import FirmwareAnalysisError, analyze_firmware
from .host_inventory import host_network_inventory
from .hotplug import HostDeviceEvents, current_local_device_ids, filter_present_local_devices
from .instruments import scan_instruments
from .local_security import local_request_allowed
from .network_discovery import discover_network_devices
from .operations import OperationError, OperationManager
from .prototype import PrototypeProject, reconcile_project, seed_project, validate_project
from .service_discovery import discover_services
from .simulation import SimulationError, simulate_project
from .serial_diagnostics import probe_sensor_diagnostics, run_sensor_diagnostic, supports_sensor_diagnostics
from .storage import StateStore
from .ssh_targets import SshTargetError, SshTargetManager
from .tool_registry import diagnose_tool, tool_registry
from .test_packs import build_test_pack
from .usb_inventory import scan_usb_devices
from .visual_intelligence import VisualAnalysisError, analyze_board_image
from .workspace import DeviceWorkspace, WorkspaceError


ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "web"
load_dotenv(ROOT / ".env")
store = StateStore(Path(os.getenv("IOT_BENCH_DB", ROOT / "ai-api" / "data" / "iot.db")))
workspace = DeviceWorkspace(ROOT)
operations = OperationManager(ROOT, store, workspace)
control_operations = ControlOperationManager(store)
bridge = SerialBridge(os.getenv("IOT_BENCH_PORT"))
ble_monitor = BleMonitor()
device_state = DeviceStateManager()
host_device_events = HostDeviceEvents()
ssh_targets = SshTargetManager()
inventory_lock = asyncio.Lock()
inventory_cache: dict[str, object] = {"hardware": [], "usb": None}
inspection_cache: dict[str, dict] = {}
camera_transport_metrics: dict[str, float | int | str] = {
    "mode": "latest_frame",
    "selected_mode": "websocket",
    "send_duration_ms": 0.0,
    "frames_sent": 0,
    "frames_skipped": 0,
}


async def ble_loop() -> None:
    while True:
        await ble_monitor.scan()
        await asyncio.sleep(2)


async def device_state_loop() -> None:
    while True:
        native_event = await host_device_events.wait(reconciliation_seconds=2.0)
        if native_event:
            await asyncio.sleep(0.05)
        cached = device_state.snapshot().get("hardware") or inventory_cache.get("hardware") or []
        presence = await asyncio.to_thread(current_local_device_ids)
        _apply_device_state(filter_present_local_devices(cached, presence))
        if not native_event:
            continue
        try:
            await hardware(force=True)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    host_device_events.start()
    bridge.start()
    ble_task = asyncio.create_task(ble_loop())
    state_task = asyncio.create_task(device_state_loop())
    try:
        yield
    finally:
        ble_task.cancel()
        state_task.cancel()
        with suppress(asyncio.CancelledError):
            await ble_task
        with suppress(asyncio.CancelledError):
            await state_task
        host_device_events.stop()
        bridge.stop()


app = FastAPI(title="IoT Hardware Connectivity Bench API", version=API_VERSION, lifespan=lifespan)


@app.middleware("http")
async def enforce_local_api_boundary(request: Request, call_next):
    client_host = request.client.host if request.client else None
    if not local_request_allowed(client_host, request.headers.get("origin")):
        return JSONResponse(status_code=403, content={"detail": "The hardware API accepts loopback clients and loopback browser origins only"})
    response = await call_next(request)
    response.headers["X-IoT-Bench-API-Version"] = API_VERSION
    return response


class WifiConfiguration(BaseModel):
    ssid: str = Field(min_length=1, max_length=32)
    password: str = Field(default="", max_length=63)
    remember: bool = True


class PortSelection(BaseModel):
    port: str = Field(min_length=1, max_length=32)


class HardwareSelection(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)


class PowerSelection(BaseModel):
    enabled: bool


class ServiceDiscoveryRequest(BaseModel):
    timeout_seconds: float = Field(default=2.5, ge=0.5, le=5.0)


class DeviceInspectionRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)


class DeviceModelSelection(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    model: str = Field(min_length=1, max_length=128)


class DeviceTestRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    test_id: str = Field(min_length=1, max_length=64)


class DeviceAccessConfiguration(BaseModel):
    name: str = Field(min_length=1, max_length=24)
    password: str = Field(default="", max_length=63)


class CameraControl(BaseModel):
    setting: str = Field(pattern="^(brightness|contrast|saturation|sharpness|exposure|quality)$")
    value: int


class CameraTransportRequest(BaseModel):
    mode: str = Field(pattern="^(direct|websocket)$")


class NetworkDiscoveryRequest(BaseModel):
    mode: str = Field(default="standard", pattern="^(standard|deep)$")
    target: str | None = Field(default=None, max_length=45)


class DeviceCommandRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    command_id: str = Field(min_length=1, max_length=64)


class OperationPlanRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=256)
    parameters: dict = Field(default_factory=dict)


class OperationApprovalRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)


class OperationExecuteRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    approval_token: str | None = Field(default=None, max_length=256)


class OperationCancelRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)


class WorkspaceWritePlanRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    root_id: str = Field(min_length=1, max_length=64)
    path: str = Field(min_length=1, max_length=512)
    content: str = Field(max_length=524_288)
    expected_sha256: str = Field(min_length=64, max_length=64)


class HardwareDefinitionRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    format: str = Field(min_length=1, max_length=32)
    source_name: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=5_600_000)


class HistoryRetentionRequest(BaseModel):
    per_device: int = Field(ge=1, le=1000)


class HistoryDeleteRequest(BaseModel):
    identifier: str | None = Field(default=None, max_length=512)
    confirm: bool = False


class SshProbeRequest(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=22, ge=1, le=65535)


class SshEnrollmentRequest(SshProbeRequest):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)
    expected_fingerprint: str = Field(min_length=8, max_length=256)


class ControlPlanRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    action: str = Field(pattern="^(gpio_read|gpio_write|adc_read)$")
    pin: str = Field(min_length=1, max_length=128)
    value: int | None = None


class ControlApprovalRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)


class ControlExecuteRequest(ControlApprovalRequest):
    approval_token: str = Field(min_length=1, max_length=256)


class FirmwareAnalysisRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=256)
    content_base64: str = Field(min_length=1, max_length=23_000_000)


class EmulationPlatformRequest(BaseModel):
    platform_id: str = Field(min_length=1, max_length=160, pattern="^[A-Za-z0-9_.-]+$")


class EmulationFirmwareRequest(EmulationPlatformRequest, FirmwareAnalysisRequest):
    runtime_ms: int = Field(default=50, ge=10, le=1000)
    proof_address: int | None = Field(default=None, ge=0, le=0xFFFFFFFF)
    proof_value: int | None = Field(default=None, ge=0, le=0xFFFFFFFF)


class VisualAnalysisRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=256)
    content_base64: str = Field(min_length=1, max_length=17_000_000)


class VisualEvidenceConfirmation(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    image_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    marking: str = Field(min_length=3, max_length=32, pattern="^[A-Za-z0-9._-]+$")
    role: str = Field(pattern="^(board|mcu_soc|usb_uart_bridge|voltage_regulator|camera_sensor|sensor|component_marking)$")
    confidence: float = Field(ge=0, le=1)
    source_text: str = Field(min_length=1, max_length=512)
    confirm: bool


class PinAttachmentRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    pin: str = Field(min_length=1, max_length=128)
    component_name: str = Field(min_length=1, max_length=128)
    component_type: str = Field(default="user_defined", min_length=1, max_length=64)
    interface: str = Field(default="direct_pin", min_length=1, max_length=64)
    notes: str = Field(default="", max_length=512)


class PinAttachmentDeleteRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    pin: str = Field(min_length=1, max_length=128)


async def status_payload() -> dict:
    payload = bridge.snapshot()
    payload["camera_transport"] = dict(camera_transport_metrics)
    payload["ble"] = await ble_monitor.snapshot()
    payload["device_state"] = device_state.snapshot()
    payload["device_events"] = host_device_events.snapshot()
    payload["operations"] = operations.snapshot()
    process = psutil.Process()
    payload["runtime"] = {
        "rss_bytes": process.memory_info().rss,
        "threads": process.num_threads(),
        "open_handles": process.num_handles() if hasattr(process, "num_handles") else None,
    }
    return payload


async def wait_for_telemetry(key: str, expected: object, timeout: float = 4.0) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    snapshot = bridge.snapshot()
    while asyncio.get_running_loop().time() < deadline:
        snapshot = bridge.snapshot()
        if snapshot["telemetry"].get(key) == expected:
            return snapshot
        await asyncio.sleep(0.1)
    return snapshot


async def wait_for_telemetry_change(key: str, previous: object, timeout: float) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    snapshot = bridge.snapshot()
    while asyncio.get_running_loop().time() < deadline:
        snapshot = bridge.snapshot()
        if snapshot["telemetry"].get(key) != previous:
            return snapshot
        await asyncio.sleep(0.1)
    return snapshot


@app.get("/api/health")
async def health() -> dict:
    return {
        "ok": True,
        "service": "iot-hardware-connectivity-bench",
        "html_enabled": os.getenv("IOT_BENCH_SERVE_HTML", "false").lower() in {"1", "true", "yes"},
    }


@app.get("/api/contract")
async def contract() -> dict[str, object]:
    return api_contract()


@app.get("/api/mcp/manifest")
async def mcp_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "transport": "stdio",
        "default_scope": "read",
        "scopes": {
            "read": ["inventory", "inspection", "evidence", "definitions", "probe_matrix", "instruments", "prototype", "simulation", "emulation", "workspace", "status", "events"],
            "test": ["capability_advertised_tests_only"],
            "plan": ["operation_plan_creation_only"],
            "approve": [],
            "execute": [],
        },
        "safety": {
            "physical_mutation_via_mcp": False,
            "approval_tokens_exposed_via_mcp": False,
            "credentials_exposed_via_mcp": False,
            "arbitrary_commands_via_mcp": False,
            "event_delivery": "pollable resource snapshot",
        },
        "contracts": {"openapi": "/openapi.json", "events": "bench://events", "capabilities": "bench://capabilities"},
    }


@app.get("/api/status")
async def status() -> dict:
    return await status_payload()


@app.get("/api/ports")
async def ports() -> list[dict]:
    return bridge.ports()


@app.post("/api/ssh/probe")
async def probe_ssh_target(request: SshProbeRequest) -> dict:
    try:
        return await asyncio.to_thread(ssh_targets.probe, request.host, request.port)
    except SshTargetError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/ssh/enroll")
async def enroll_ssh_target(request: SshEnrollmentRequest) -> dict:
    try:
        result = await asyncio.to_thread(
            ssh_targets.enroll,
            request.host,
            request.port,
            request.username,
            request.password,
            request.expected_fingerprint,
        )
    except SshTargetError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    await hardware(force=True)
    return result


@app.delete("/api/ssh/enroll/{identifier:path}")
async def remove_ssh_target(identifier: str) -> dict:
    removed = await asyncio.to_thread(ssh_targets.remove, identifier)
    if not removed:
        raise HTTPException(status_code=404, detail="SSH target is not enrolled")
    await hardware(force=True)
    return {"removed": True, "identifier": identifier}


async def _refresh_hardware_inventory() -> tuple[list[dict], dict]:
    serial_devices, network_devices, raw_usb, _ = await asyncio.gather(
        asyncio.to_thread(bridge.ports),
        asyncio.to_thread(discover_usb_network_devices),
        asyncio.to_thread(scan_usb_devices),
        asyncio.to_thread(arduino_board_inventory),
    )
    represented = {
        (str(item.get("vid") or "").upper(), str(item.get("pid") or "").upper())
        for item in [*serial_devices, *network_devices]
    }
    passive_devices = []
    for device in raw_usb.get("devices", []):
        identity = (str(device.get("vendor_id") or "").upper(), str(device.get("product_id") or "").upper())
        if identity in represented or device.get("classification") == "usb_hub":
            continue
        passive_devices.append(
            {
                "id": device["id"],
                "kind": "usb_identity",
                "device": f"USB {device['bus']}:{device['address']}",
                "name": device.get("name") or device.get("product") or "USB development device",
                "description": device.get("class_name") or "Raw USB identity",
                "manufacturer": device.get("manufacturer"),
                "serial_number": device.get("serial_number"),
                "vid": device.get("vendor_id"),
                "pid": device.get("product_id"),
                "is_esp32": False,
                "is_lichee": identity == ("359F", "2120"),
                "transport": "USB identity (passive)",
                "classification": device.get("classification") or "usb_peripheral",
                "device_category": "circuit target" if device.get("development_candidate") else "host peripheral",
                "bus": device.get("bus"),
                "address": device.get("address"),
            }
        )
    inventory = await asyncio.to_thread(
        enrich_hardware_list,
        [*serial_devices, *network_devices, *passive_devices, *ssh_targets.inventory()],
    )
    inventory_cache["hardware"] = inventory
    inventory_cache["usb"] = raw_usb
    return inventory, raw_usb


@app.get("/api/hardware")
async def hardware(force: bool = False) -> list[dict]:
    inventory = inventory_cache.get("hardware")
    if force or not isinstance(inventory, list) or not inventory:
        async with inventory_lock:
            inventory = inventory_cache.get("hardware")
            if force or not isinstance(inventory, list) or not inventory:
                inventory, _ = await _refresh_hardware_inventory()
    inventory = apply_runtime_identity(inventory, bridge.snapshot())
    _apply_device_state(inventory)
    return inventory


def _apply_device_state(inventory: list[dict]) -> None:
    if device_state.update(inventory):
        delta = device_state.last_delta()
        for identifier in delta["removed"]:
            operations.cancel_identifier(identifier)
            control_operations.cancel_identifier(identifier)
            inspection_cache.pop(identifier, None)
        for identifier in delta["added"]:
            operations.mark_present(identifier)


def _model_setting_key(identifier: str) -> str:
    return f"device_model:{hashlib.sha256(identifier.encode('utf-8')).hexdigest()}"


def _definition_setting_key(identifier: str) -> str:
    return f"hardware_definitions:{hashlib.sha256(identifier.encode('utf-8')).hexdigest()}"


def _pin_attachment_setting_key(identifier: str) -> str:
    return f"pin_attachments:{hashlib.sha256(identifier.encode('utf-8')).hexdigest()}"


def _stored_definitions(identifier: str) -> list[dict]:
    value = store.get_setting(_definition_setting_key(identifier))
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _stored_pin_attachments(identifier: str) -> list[dict]:
    value = store.get_setting(_pin_attachment_setting_key(identifier))
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


async def _find_hardware(identifier: str) -> dict:
    profile = next((item for item in await hardware() if item["id"] == identifier), None)
    if profile is None:
        raise HTTPException(status_code=404, detail="The selected hardware is no longer available")
    return profile


async def _inspect_profile(profile: dict) -> dict:
    live = None
    if profile.get("kind") == "usb_network":
        try:
            live = await asyncio.to_thread(inspect_usb_network_device, profile["id"])
        except ValueError:
            live = None
    elif profile.get("kind") == "ssh_target":
        live = await asyncio.to_thread(ssh_targets.inspect, str(profile["id"]))
    elif profile.get("kind") in {"serial", "usb_identity"}:
        live = await asyncio.to_thread(passive_inspect_device, profile)
        if profile.get("kind") == "serial":
            snapshot = bridge.snapshot()
            selected_port = str(profile.get("device") or "").upper()
            bridge_port = str(snapshot.get("port") or "").upper()
            if snapshot.get("connected") and selected_port and selected_port == bridge_port:
                live = live or {}
                live["telemetry"] = {
                    **(live.get("telemetry") or {}),
                    **(snapshot.get("telemetry") or {}),
                }
            if supports_sensor_diagnostics(profile):
                live = live or {}
                live["diagnostic"] = await asyncio.to_thread(probe_sensor_diagnostics, str(profile["device"]))
    assigned_model = store.get_setting(_model_setting_key(str(profile["id"])))
    inspection = await asyncio.to_thread(inspect_hardware, profile, live, assigned_model)
    inspection["definitions"] = _stored_definitions(str(profile["id"]))
    visual_evidence = await asyncio.to_thread(store.visual_evidence, str(profile["id"]))
    inspection["visual_evidence"] = visual_evidence
    for item in visual_evidence:
        source = f"User-confirmed local OCR, image sha256 {item['image_sha256'][:12]}"
        inspection["evidence"].append({"claim": f"Visible marking {item['marking']} is present", "status": "detected", "source": source})
        if item["role"] == "board":
            inspection["identity_layers"].append({"id": f"visual-board:{item['sequence']}", "layer": "Board photo", "name": item["marking"], "source": source, "status": "detected"})
        elif not any(component.get("name", "").upper() == item["marking"] for component in inspection["components"]):
            inspection["components"].append({"id": f"visual:{item['sequence']}", "name": item["marking"], "type": item["role"], "bus": None, "variant": None, "status": "detected", "source": source})
    apply_pin_attachments(inspection, _stored_pin_attachments(str(profile["id"])))
    inspection["confidence_calibration"] = inspection_calibration(inspection)
    inspection["evidence_graph"] = build_evidence_graph(inspection)
    inspection["probe_matrix"] = build_probe_matrix(inspection, connected=True)
    inspection["discovery"] = build_discovery_report(profile, inspection, live, inspection["probe_matrix"])
    inspection["history_receipt"] = await asyncio.to_thread(
        store.record_inspection, str(profile["id"]), inspection
    )
    inspection_cache[str(profile["id"])] = inspection
    return inspection


async def _cached_inspection(profile: dict) -> dict:
    cached = inspection_cache.get(str(profile["id"]))
    return cached if cached is not None else await _inspect_profile(profile)


@app.get("/api/metadata/providers")
async def metadata_provider_status() -> dict:
    providers = await asyncio.to_thread(metadata_providers)
    return {"providers": providers, "available_count": sum(1 for item in providers if item["available"])}


@app.get("/api/tools/{tool_id}/diagnose")
async def tool_diagnostic(tool_id: str) -> dict:
    try:
        return await asyncio.to_thread(diagnose_tool, tool_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/adapters")
async def adapters() -> dict:
    return adapter_registry()


@app.get("/api/device/definitions")
async def device_definitions(identifier: str) -> dict:
    await _find_hardware(identifier)
    definitions = _stored_definitions(identifier)
    return {"identifier": identifier, "count": len(definitions), "definitions": definitions}


@app.post("/api/device/definitions/import")
async def import_device_definition(request: HardwareDefinitionRequest) -> dict:
    await _find_hardware(request.identifier)
    try:
        imported = await asyncio.to_thread(
            import_hardware_definition,
            request.format,
            request.content,
            request.source_name,
        )
    except DefinitionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    definitions = _stored_definitions(request.identifier)
    definitions = [item for item in definitions if item.get("source_sha256") != imported["source_sha256"]]
    definitions.append(imported)
    store.set_setting(_definition_setting_key(request.identifier), json.dumps(definitions))
    inspection_cache.pop(request.identifier, None)
    return {"identifier": request.identifier, "count": len(definitions), "imported": imported}


@app.get("/api/arduino/boards")
async def arduino_boards() -> dict:
    boards = await asyncio.to_thread(arduino_board_inventory, True)
    return {"provider": "Arduino CLI", "count": len(boards), "ports": list(boards.values())}


@app.post("/api/device/inspect")
async def inspect_selected_device(request: DeviceInspectionRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    inspection = await _inspect_profile(profile)
    return {"hardware": profile, "inspection": inspection}


@app.post("/api/device/model")
async def assign_device_model(selection: DeviceModelSelection) -> dict:
    profile = await _find_hardware(selection.identifier)
    live = await asyncio.to_thread(passive_inspect_device, profile) if profile.get("kind") == "serial" else None
    current = await asyncio.to_thread(inspect_hardware, profile, live, None)
    if current["candidates"] and selection.model not in current["candidates"]:
        raise HTTPException(status_code=422, detail="Model is not one of the evidence-supported candidates")
    store.set_setting(_model_setting_key(selection.identifier), selection.model)
    inspection_cache.pop(selection.identifier, None)
    return {"saved": True, "identifier": selection.identifier, "model": selection.model}


@app.get("/api/prototype")
async def prototype_project(identifier: str) -> dict:
    if not identifier or len(identifier) > 512:
        raise HTTPException(status_code=422, detail="A valid hardware identifier is required")
    profile = await _find_hardware(identifier)
    inspection = await _cached_inspection(profile)
    saved = store.get_prototype_project(identifier)
    if saved:
        return reconcile_project(saved, identifier, inspection).model_dump(mode="json")
    return seed_project(identifier, inspection).model_dump(mode="json")


@app.put("/api/prototype")
async def save_prototype_project(project: PrototypeProject) -> dict:
    project, _ = validate_project(project)
    try:
        saved = store.save_prototype_project(project.identifier, project.model_dump(mode="json"))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return PrototypeProject.model_validate(saved).model_dump(mode="json")


@app.post("/api/prototype/validate")
async def validate_prototype_project(project: PrototypeProject) -> dict:
    validated, issues = validate_project(project)
    return {"project": validated.model_dump(mode="json"), "issues": issues}


@app.post("/api/prototype/simulate")
async def simulate_prototype_project(project: PrototypeProject) -> dict:
    try:
        return await asyncio.to_thread(simulate_project, project, ROOT)
    except SimulationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/device/test")
async def run_device_test(request: DeviceTestRequest) -> dict:
    async def recorded(result: dict) -> dict:
        receipt = await asyncio.to_thread(store.record_test_result, request.identifier, request.test_id, result)
        return {**result, "history_receipt": receipt}

    profile = await _find_hardware(request.identifier)
    inspection = await _cached_inspection(profile)
    test_pack = build_test_pack(inspection)
    advertised = next((item for item in test_pack["tests"] if item["id"] == request.test_id), None)
    if advertised is None:
        raise HTTPException(status_code=409, detail="The requested test is not in the current target test pack")
    if not advertised["available"]:
        raise HTTPException(status_code=409, detail="The requested test is unavailable under current target evidence")
    if request.test_id == "presence":
        return await recorded({"test_id": request.test_id, "passed": True, "summary": f"{profile['name']} is present at {profile.get('device')}."})
    if request.test_id in {"camera_stream", "ble_runtime", "wifi_runtime"}:
        snapshot = bridge.snapshot()
        selected_port = str(profile.get("device") or "").upper()
        bridge_port = str(snapshot.get("port") or "").upper()
        if not snapshot.get("connected") or selected_port != bridge_port:
            raise HTTPException(status_code=409, detail="The compatible runtime is not connected on the selected interface")
        telemetry = snapshot.get("telemetry") or {}
        if request.test_id == "camera_stream":
            passed = telemetry.get("camera_ready") is True and int(snapshot.get("frame_sequence") or 0) > 0
            summary = "Camera runtime is ready and image frames are arriving." if passed else "The camera runtime is not delivering image frames."
        elif request.test_id == "ble_runtime":
            passed = any(key in telemetry for key in ("ble_advertising", "ble_device_address", "ble_connected_clients"))
            summary = "Bluetooth Low Energy runtime state is available." if passed else "No Bluetooth runtime state was reported."
        else:
            passed = any(key in telemetry for key in ("wifi_ap_active", "wifi_station_connected", "wifi_station_status"))
            summary = "Wi-Fi access-point and station state is available." if passed else "No Wi-Fi runtime state was reported."
        return await recorded({"test_id": request.test_id, "passed": passed, "summary": summary, "evidence": telemetry})
    if request.test_id == "service_check" and profile.get("kind") == "usb_network":
        checked = await asyncio.to_thread(inspect_usb_network_device, request.identifier)
        passed = bool(checked.get("online") and any(checked.get("services", {}).values()))
        return await recorded({"test_id": request.test_id, "passed": passed, "summary": "SSH and HTTP services verified." if passed else "No supported target service answered.", "evidence": checked})
    if request.test_id == "serial_protocol" and supports_sensor_diagnostics(profile):
        result = await asyncio.to_thread(probe_sensor_diagnostics, str(profile["device"]))
        passed = bool(result.get("ready"))
        return await recorded({"test_id": request.test_id, "passed": passed, "summary": "Compatible serial diagnostic protocol verified." if passed else "No compatible diagnostic protocol answered.", "evidence": result})
    if request.test_id == "i2c_inventory" and supports_sensor_diagnostics(profile):
        try:
            result = await asyncio.to_thread(run_sensor_diagnostic, str(profile["device"]), "i2c")
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return await recorded({"test_id": request.test_id, "passed": bool(result.get("passed")), "summary": f"I2C scan completed with {result.get('count', 0)} responding address(es).", "evidence": result})
    if request.test_id.startswith("sensor:") and supports_sensor_diagnostics(profile):
        sensor_id = request.test_id.split(":", 1)[1]
        try:
            result = await asyncio.to_thread(run_sensor_diagnostic, str(profile["device"]), sensor_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        passed = bool(result.get("passed"))
        return await recorded({
            "test_id": request.test_id,
            "passed": passed,
            "summary": f"{sensor_id} returned live data." if passed else f"{sensor_id} did not pass its live diagnostic.",
            "evidence": result,
        })
    try:
        adapter_result = await asyncio.to_thread(run_adapter_test, profile, request.test_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if adapter_result is not None:
        return await recorded({"test_id": request.test_id, **adapter_result})
    raise HTTPException(status_code=409, detail="This test requires a compatible adapter or approved diagnostic firmware")


@app.get("/api/device/test-pack")
async def device_test_pack(identifier: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _cached_inspection(profile)
    return build_test_pack(inspection)


@app.get("/api/tools")
async def tools() -> dict:
    return await asyncio.to_thread(tool_registry)


@app.get("/api/instruments")
async def instruments() -> dict:
    return await asyncio.to_thread(scan_instruments)


@app.post("/api/firmware/analyze")
async def firmware_analysis(request: FirmwareAnalysisRequest) -> dict:
    try:
        payload = base64.b64decode(request.content_base64, validate=True)
        return await asyncio.to_thread(analyze_firmware, payload, request.filename)
    except (binascii.Error, FirmwareAnalysisError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/visual/analyze")
async def visual_analysis(request: VisualAnalysisRequest) -> dict:
    try:
        payload = base64.b64decode(request.content_base64, validate=True)
        return await asyncio.to_thread(analyze_board_image, payload, request.filename)
    except binascii.Error as error:
        raise HTTPException(status_code=422, detail="Image content is not valid base64") from error
    except VisualAnalysisError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/device/visual-evidence/confirm")
async def confirm_visual_evidence(request: VisualEvidenceConfirmation) -> dict:
    await _find_hardware(request.identifier)
    if not request.confirm:
        raise HTTPException(status_code=409, detail="Explicit confirmation is required")
    receipt = await asyncio.to_thread(
        store.confirm_visual_evidence,
        request.identifier,
        request.image_sha256,
        request.marking.upper(),
        request.role,
        request.confidence,
        request.source_text,
    )
    if request.role == "board":
        store.set_setting(_model_setting_key(request.identifier), request.marking.upper())
    inspection_cache.pop(request.identifier, None)
    return {"confirmed": True, "identifier": request.identifier, "marking": request.marking.upper(), "role": request.role, "image_persisted": False, "receipt": receipt}


@app.post("/api/device/pin-attachments")
async def save_pin_attachment(request: PinAttachmentRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    inspection = await _cached_inspection(profile)
    pin = find_pin(inspection, request.pin)
    if pin is None:
        raise HTTPException(status_code=422, detail="The selected pin is not present in the current evidence map")
    attachment = {
        "pin": str(pin["name"]),
        "component_name": request.component_name.strip(),
        "component_type": request.component_type.strip().lower().replace(" ", "_"),
        "interface": request.interface.strip().lower().replace(" ", "_"),
        "notes": request.notes.strip(),
    }
    attachments = [
        item for item in _stored_pin_attachments(request.identifier)
        if str(item.get("pin") or "").casefold() != attachment["pin"].casefold()
    ]
    attachments.append(attachment)
    store.set_setting(_pin_attachment_setting_key(request.identifier), json.dumps(attachments, separators=(",", ":")))
    inspection_cache.pop(request.identifier, None)
    return {"saved": True, "identifier": request.identifier, "attachment": attachment, "evidence_status": "declared"}


@app.delete("/api/device/pin-attachments")
async def delete_pin_attachment(request: PinAttachmentDeleteRequest) -> dict:
    await _find_hardware(request.identifier)
    attachments = _stored_pin_attachments(request.identifier)
    remaining = [
        item for item in attachments
        if str(item.get("pin") or "").casefold() != request.pin.casefold()
    ]
    store.set_setting(_pin_attachment_setting_key(request.identifier), json.dumps(remaining, separators=(",", ":")))
    inspection_cache.pop(request.identifier, None)
    return {"deleted": len(remaining) != len(attachments), "identifier": request.identifier, "pin": request.pin}


@app.get("/api/emulation/platforms")
async def emulation_platforms(identity: str = "") -> dict:
    return await asyncio.to_thread(platform_catalog, ROOT, identity[:256])


@app.post("/api/emulation/platform/verify")
async def verify_emulation_platform(request: EmulationPlatformRequest) -> dict:
    try:
        return await asyncio.to_thread(verify_platform, ROOT, request.platform_id)
    except EmulationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/emulation/firmware/run")
async def run_emulated_firmware(request: EmulationFirmwareRequest) -> dict:
    try:
        payload = base64.b64decode(request.content_base64, validate=True)
        return await asyncio.to_thread(
            run_firmware,
            ROOT,
            request.platform_id,
            payload,
            request.filename,
            request.runtime_ms,
            request.proof_address,
            request.proof_value,
        )
    except binascii.Error as error:
        raise HTTPException(status_code=422, detail="Firmware content is not valid base64") from error
    except EmulationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/api/device/operations")
async def device_operations(identifier: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _inspect_profile(profile)
    items = await asyncio.to_thread(operations.capabilities, profile, inspection)
    return {"identifier": identifier, "operations": items}


@app.get("/api/device/control-profile")
async def device_control_profile(identifier: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _cached_inspection(profile)
    connected = any(item.get("id") == identifier for item in await hardware())
    return build_control_profile(inspection, connected)


@app.get("/api/device/probe-matrix")
async def device_probe_matrix(identifier: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _cached_inspection(profile)
    connected = any(item.get("id") == identifier for item in await hardware())
    return build_probe_matrix(inspection, connected)


@app.post("/api/control/plan")
async def plan_control_action(request: ControlPlanRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    inspection = await _inspect_profile(profile)
    try:
        return control_operations.create_plan(request.identifier, request.action, request.pin, request.value, inspection, True)
    except ControlError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/control/{plan_id}/approve")
async def approve_control_action(plan_id: str, request: ControlApprovalRequest) -> dict:
    try:
        return control_operations.approve(plan_id, request.identifier)
    except ControlError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/control/{plan_id}/execute")
async def execute_control_action(plan_id: str, request: ControlExecuteRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    inspection = await _inspect_profile(profile)
    try:
        plan = control_operations.prepare(plan_id, request.identifier, request.approval_token, inspection)
        previous = bridge.snapshot()["telemetry"].get("control_sequence", 0)
        bridge.command(plan.command)
    except (ControlError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    snapshot = await wait_for_telemetry_change("control_sequence", previous, timeout=4.0)
    telemetry = snapshot["telemetry"]
    acknowledged = telemetry.get("control_sequence", previous) != previous
    passed = acknowledged and telemetry.get("control_last_ok") is True and telemetry.get("control_last_pin") == plan.pin
    detail = telemetry.get("control_last_error") or (
        f"{telemetry.get('control_last_action')} {plan.pin} returned {telemetry.get('control_last_value')}"
        if acknowledged else "The runtime did not acknowledge the control command"
    )
    return control_operations.finish(plan, passed, str(detail))


@app.post("/api/operations/plan")
async def plan_operation(request: OperationPlanRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    inspection = await _inspect_profile(profile)
    try:
        return await asyncio.to_thread(
            operations.create_plan,
            profile,
            inspection,
            request.operation_id,
            request.parameters,
        )
    except OperationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/operations/{plan_id}/approve")
async def approve_operation(plan_id: str, request: OperationApprovalRequest) -> dict:
    try:
        return await asyncio.to_thread(operations.approve, plan_id, request.identifier)
    except OperationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/operations/{plan_id}/execute")
async def execute_operation(plan_id: str, request: OperationExecuteRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    inspection = await _inspect_profile(profile)
    try:
        return await asyncio.to_thread(
            operations.execute,
            plan_id,
            request.identifier,
            request.approval_token,
            profile,
            inspection,
        )
    except OperationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/operations/cancel")
async def cancel_operation(request: OperationCancelRequest) -> dict:
    return await asyncio.to_thread(operations.cancel_active, request.identifier)


@app.get("/api/operations/history")
async def operation_history(identifier: str | None = None) -> dict:
    items = await asyncio.to_thread(operations.history, identifier)
    return {"identifier": identifier, "events": items}


@app.get("/api/history")
async def evidence_history(identifier: str | None = None, limit: int = 100) -> dict:
    bounded = max(1, min(limit, 1000))
    inspections, tests = await asyncio.gather(
        asyncio.to_thread(store.inspection_history, identifier, bounded),
        asyncio.to_thread(store.test_history, identifier, bounded),
    )
    return {"identifier": identifier, "retention_per_device": store.history_retention(), "inspections": inspections, "tests": tests}


@app.get("/api/history/export")
async def export_evidence_history(identifier: str | None = None) -> dict:
    return await asyncio.to_thread(store.export_history, identifier)


@app.put("/api/history/retention")
async def update_history_retention(request: HistoryRetentionRequest) -> dict:
    bounded = await asyncio.to_thread(store.set_history_retention, request.per_device)
    return {"saved": True, "retention_per_device": bounded}


@app.post("/api/history/delete")
async def delete_evidence_history(request: HistoryDeleteRequest) -> dict:
    if not request.confirm:
        raise HTTPException(status_code=409, detail="History deletion requires confirm=true")
    removed = await asyncio.to_thread(store.delete_history, request.identifier)
    return {"deleted": True, "identifier": request.identifier, "removed": removed}


@app.get("/api/workspace")
async def device_workspace(identifier: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _cached_inspection(profile)
    return await asyncio.to_thread(workspace.inventory, inspection)


@app.get("/api/workspace/file")
async def workspace_file(identifier: str, root_id: str, path: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _cached_inspection(profile)
    try:
        return await asyncio.to_thread(workspace.read_text, root_id, path, inspection)
    except WorkspaceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/workspace/write-plan")
async def workspace_write_plan(request: WorkspaceWritePlanRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    inspection = await _inspect_profile(profile)
    return await asyncio.to_thread(
        operations.create_write_plan,
        request.identifier,
        request.root_id,
        request.path,
        request.content,
        request.expected_sha256,
        operations.fingerprint(profile, inspection),
    )


@app.get("/api/inventory/usb")
async def usb_inventory(force: bool = False) -> dict:
    cached = inventory_cache.get("usb")
    if force or not isinstance(cached, dict):
        async with inventory_lock:
            cached = inventory_cache.get("usb")
            if force or not isinstance(cached, dict):
                _, cached = await _refresh_hardware_inventory()
    return cached


@app.get("/api/inventory/host")
async def host_inventory() -> dict:
    return await asyncio.to_thread(host_network_inventory)


@app.post("/api/discovery/services")
async def network_services(request: ServiceDiscoveryRequest) -> dict:
    return await asyncio.to_thread(discover_services, request.timeout_seconds)


@app.post("/api/discovery/network")
async def network_devices(request: NetworkDiscoveryRequest) -> dict:
    try:
        return await asyncio.to_thread(discover_network_devices, request.mode, request.target)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/device/command")
async def device_command(request: DeviceCommandRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    if profile.get("kind") != "usb_network":
        raise HTTPException(status_code=409, detail="Selected hardware has no compatible operating-system adapter")
    try:
        return await asyncio.to_thread(run_usb_network_diagnostic, request.identifier, request.command_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/hardware/select")
async def select_hardware(selection: HardwareSelection) -> dict:
    if selection.identifier.startswith("serial:"):
        port = selection.identifier.removeprefix("serial:")
        profile = next((item for item in await hardware() if item["device"] == port), None)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Serial port {port} is not available")
        store.set_setting("selected_hardware", selection.identifier)
        if not profile["is_esp32"]:
            store.remember_profile(profile, "identified")
            inspection = await asyncio.to_thread(
                inspect_hardware,
                profile,
                None,
                store.get_setting(_model_setting_key(selection.identifier)),
            )
            return {
                "accepted": True,
                "confirmed": True,
                "interface_confirmed": True,
                "protocol_confirmed": False,
                "hardware": profile,
                "inspection": inspection,
                "error": None,
            }
        bridge.select_port(port)
        for _ in range(40):
            snapshot = bridge.snapshot()
            device_confirmed = bool(snapshot["telemetry"].get("device")) if profile["is_esp32"] else True
            if snapshot["connected"] and device_confirmed:
                store.remember_profile(profile, "connected")
                return {"accepted": True, "confirmed": True, "hardware": profile}
            await asyncio.sleep(0.1)
        snapshot = bridge.snapshot()
        store.remember_profile(profile, "unconfirmed")
        return {
            "accepted": True,
            "confirmed": False,
            "hardware": profile,
            "error": snapshot["error"] or "No compatible device telemetry received",
        }
    profile = next((item for item in await hardware() if item["id"] == selection.identifier), None)
    if profile and profile.get("kind") == "usb_identity":
        store.set_setting("selected_hardware", selection.identifier)
        inspection = await asyncio.to_thread(
            inspect_hardware,
            profile,
            None,
            store.get_setting(_model_setting_key(selection.identifier)),
        )
        return {
            "accepted": True,
            "confirmed": True,
            "interface_confirmed": True,
            "protocol_confirmed": False,
            "hardware": profile,
            "inspection": inspection,
            "error": None,
        }
    try:
        profile = await asyncio.to_thread(inspect_usb_network_device, selection.identifier)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    store.set_setting("selected_hardware", selection.identifier)
    return {
        "accepted": True,
        "confirmed": bool(profile["online"]),
        "hardware": profile,
        "error": None if profile["online"] else "The USB network device did not answer",
    }


@app.get("/api/profiles")
async def profiles() -> dict:
    return {
        "selected_port": store.get_setting("selected_port"),
        "selected_hardware": store.get_setting("selected_hardware"),
        "last_wifi_ssid": store.get_setting("last_wifi_ssid"),
        "profiles": store.profiles(),
        "wireless_profiles": store.wireless_profiles(),
    }


@app.post("/api/port")
async def select_port(selection: PortSelection) -> dict:
    result = await select_hardware(HardwareSelection(identifier=f"serial:{selection.port}"))
    return {
        **result,
        "port": selection.port,
        "profile": result["hardware"],
    }


@app.post("/api/ble/scan")
async def scan_ble() -> dict:
    return await ble_monitor.scan(timeout=6)


@app.post("/api/ble/connect")
async def connect_ble() -> dict:
    result = await ble_monitor.verify_connection()
    if result.get("verified"):
        snapshot = await ble_monitor.snapshot()
        store.remember_wireless_profile(
            "ble",
            str(result["address"]),
            str(snapshot.get("name") or result["address"]),
            {"service_uuids": snapshot.get("service_uuids", [])},
            "verified",
        )
    return result


@app.post("/api/ble/power")
async def set_ble_power(selection: PowerSelection) -> dict:
    try:
        bridge.command("BLE ON" if selection.enabled else "BLE OFF")
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    snapshot = await wait_for_telemetry("ble_advertising", selection.enabled)
    actual = snapshot["telemetry"].get("ble_advertising")
    return {
        "accepted": True,
        "confirmed": actual == selection.enabled,
        "enabled": actual,
        "error": snapshot["error"],
    }


@app.post("/api/device/status")
async def refresh_device_status() -> dict:
    try:
        bridge.command("STATUS")
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"accepted": True}


@app.post("/api/camera/control")
async def set_camera_control(control: CameraControl) -> dict:
    telemetry_key = "camera_ae_level" if control.setting == "exposure" else f"camera_{control.setting}"
    if control.setting == "quality":
        telemetry_key = "camera_jpeg_quality"
    previous = bridge.snapshot()["telemetry"].get(telemetry_key)
    try:
        bridge.configure_camera(control.setting, control.value)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    snapshot = await wait_for_telemetry_change(telemetry_key, previous, timeout=3.0)
    actual = snapshot["telemetry"].get(telemetry_key)
    return {
        "accepted": True,
        "confirmed": actual == control.value,
        "setting": control.setting,
        "value": actual,
        "error": snapshot.get("error"),
    }


@app.post("/api/camera/transport")
async def set_camera_transport(request: CameraTransportRequest) -> dict:
    snapshot = bridge.snapshot()
    telemetry = snapshot.get("telemetry") or {}
    if not snapshot.get("connected") or not telemetry.get("camera_ready"):
        raise HTTPException(status_code=409, detail="A compatible live camera target is required")
    direct_ip = telemetry.get("wifi_station_ip") or telemetry.get("wifi_ap_ip")
    if request.mode == "direct" and not direct_ip:
        raise HTTPException(status_code=409, detail="The selected camera has no browser-reachable network address")
    expected_usb = request.mode == "websocket"
    try:
        bridge.command("STREAM ON" if expected_usb else "STREAM OFF")
        bridge.command("STATUS")
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    confirmed = await wait_for_telemetry("usb_streaming", expected_usb, timeout=3.0)
    actual_usb = bool((confirmed.get("telemetry") or {}).get("usb_streaming"))
    applied = actual_usb == expected_usb
    if applied:
        camera_transport_metrics["selected_mode"] = request.mode
    return {
        "mode": request.mode if applied else "websocket" if actual_usb else "direct",
        "confirmed": applied,
        "direct_url": f"http://{direct_ip}/stream" if direct_ip else None,
        "usb_streaming": actual_usb,
    }


@app.post("/api/wifi/ap")
async def set_wifi_access_point(selection: PowerSelection) -> dict:
    try:
        bridge.command("WIFI AP ON" if selection.enabled else "WIFI AP OFF")
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    snapshot = await wait_for_telemetry("wifi_ap_active", selection.enabled)
    actual = snapshot["telemetry"].get("wifi_ap_active")
    return {
        "accepted": True,
        "confirmed": actual == selection.enabled,
        "enabled": actual,
        "ip": snapshot["telemetry"].get("wifi_ap_ip"),
        "error": snapshot["error"],
    }


@app.post("/api/wifi/scan")
async def scan_wifi() -> dict:
    previous = bridge.snapshot()["telemetry"].get("wifi_scan_id", 0)
    try:
        bridge.command("WIFI SCAN")
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    snapshot = await wait_for_telemetry_change("wifi_scan_id", previous, timeout=18.0)
    telemetry = snapshot["telemetry"]
    confirmed = telemetry.get("wifi_scan_id", previous) != previous
    return {
        "accepted": True,
        "confirmed": confirmed,
        "networks": telemetry.get("wifi_networks", []),
        "error": telemetry.get("wifi_scan_error") or snapshot["error"],
    }


@app.post("/api/wifi/internet-test")
async def test_device_internet() -> dict:
    previous = bridge.snapshot()["telemetry"].get("internet_probe_id", 0)
    try:
        bridge.command("INTERNET TEST")
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    snapshot = await wait_for_telemetry_change("internet_probe_id", previous, timeout=10.0)
    telemetry = snapshot["telemetry"]
    return {
        "accepted": True,
        "confirmed": telemetry.get("internet_probe_id", previous) != previous,
        "reachable": bool(telemetry.get("internet_reachable")),
        "status": telemetry.get("internet_probe_status", "unknown"),
        "latency_ms": telemetry.get("internet_probe_latency_ms", 0),
        "bytes_sent": telemetry.get("internet_bytes_sent", 0),
        "bytes_received": telemetry.get("internet_bytes_received", 0),
    }


@app.post("/api/host/wifi/scan")
async def scan_host_wireless() -> dict:
    return await asyncio.to_thread(scan_host_wifi)


@app.post("/api/device/access")
async def configure_device_access(configuration: DeviceAccessConfiguration) -> dict:
    if configuration.password and len(configuration.password) < 8:
        raise HTTPException(status_code=422, detail="A new direct Wi-Fi password must be at least 8 characters")
    try:
        bridge.configure_device_access(configuration.name.strip(), configuration.password)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    snapshot = await wait_for_telemetry("device", configuration.name.strip(), timeout=6.0)
    confirmed = snapshot["telemetry"].get("device") == configuration.name.strip()
    if confirmed:
        store.set_setting("device_name", configuration.name.strip())
    return {
        "accepted": True,
        "confirmed": confirmed,
        "name": snapshot["telemetry"].get("device"),
        "ap_active": snapshot["telemetry"].get("wifi_ap_active"),
        "ble_advertising": snapshot["telemetry"].get("ble_advertising"),
    }


@app.post("/api/wifi")
async def configure_wifi(configuration: WifiConfiguration) -> dict:
    previous_join_id = bridge.snapshot()["telemetry"].get("wifi_join_id", 0)
    try:
        bridge.configure_wifi(configuration.ssid, configuration.password, configuration.remember)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if configuration.remember:
        store.set_setting("last_wifi_ssid", configuration.ssid)
    snapshot = await wait_for_telemetry_change("wifi_join_id", previous_join_id, timeout=4.0)
    attempted = snapshot["telemetry"].get("wifi_join_id", previous_join_id) != previous_join_id
    deadline = asyncio.get_running_loop().time() + 15.0
    while attempted and asyncio.get_running_loop().time() < deadline:
        snapshot = bridge.snapshot()
        telemetry = snapshot["telemetry"]
        status = telemetry.get("wifi_station_status", "unknown")
        if telemetry.get("wifi_station_connected") or status in {"network_not_found", "connection_failed"}:
            break
        await asyncio.sleep(0.25)
    telemetry = snapshot["telemetry"]
    status = str(telemetry.get("wifi_station_status", "unknown"))
    if configuration.remember:
        store.remember_wireless_profile(
            "wifi",
            configuration.ssid,
            configuration.ssid,
            {"ip": telemetry.get("wifi_station_ip", "")},
            "connected" if telemetry.get("wifi_station_connected") else status,
        )
    return {
        "accepted": True,
        "attempted": attempted,
        "saved": telemetry.get("wifi_station_ssid") == configuration.ssid,
        "connected": bool(telemetry.get("wifi_station_connected")),
        "ssid": configuration.ssid,
        "status": status,
        "ip": telemetry.get("wifi_station_ip", ""),
    }


@app.get("/api/camera/snapshot.jpg")
async def camera_snapshot() -> Response:
    frame = bridge.latest_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="No camera frame received")
    return Response(frame, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/camera/stream.mjpeg")
async def camera_stream() -> StreamingResponse:
    if os.getenv("IOT_BENCH_ENABLE_MJPEG", "false").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=410, detail="Legacy MJPEG is disabled; use the latest-frame /ws/camera transport")

    async def frames():
        previous_sequence = -1
        while True:
            snapshot = bridge.snapshot()
            frame = bridge.latest_frame()
            if frame is not None and snapshot["frame_sequence"] != previous_sequence:
                previous_sequence = snapshot["frame_sequence"]
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(frame)}\r\n\r\n".encode()
                    + frame
                    + b"\r\n"
                )
            await asyncio.sleep(0.025)

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@app.websocket("/ws")
async def websocket_status(websocket: WebSocket) -> None:
    if not local_request_allowed(websocket.client.host if websocket.client else None, websocket.headers.get("origin")):
        await websocket.close(code=1008, reason="Loopback client and origin required")
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(await status_payload())
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/camera")
async def websocket_camera(websocket: WebSocket) -> None:
    if not local_request_allowed(websocket.client.host if websocket.client else None, websocket.headers.get("origin")):
        await websocket.close(code=1008, reason="Loopback client and origin required")
        return
    await websocket.accept()
    previous_sequence = -1
    try:
        while True:
            sequence, received_at, frame = await asyncio.to_thread(bridge.wait_for_latest_frame, previous_sequence, 1.0)
            if frame is not None and sequence != previous_sequence:
                if previous_sequence >= 0 and sequence > previous_sequence + 1:
                    camera_transport_metrics["frames_skipped"] = int(camera_transport_metrics["frames_skipped"]) + sequence - previous_sequence - 1
                previous_sequence = sequence
                header = b"ICAM" + struct.pack("<IdI", sequence, (received_at or 0) * 1000, len(frame))
                send_started = asyncio.get_running_loop().time()
                await websocket.send_bytes(header + frame)
                camera_transport_metrics["send_duration_ms"] = round((asyncio.get_running_loop().time() - send_started) * 1000, 2)
                camera_transport_metrics["frames_sent"] = int(camera_transport_metrics["frames_sent"]) + 1
    except (WebSocketDisconnect, RuntimeError):
        return


if os.getenv("IOT_BENCH_SERVE_HTML", "false").lower() in {"1", "true", "yes"}:
    app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="web")
