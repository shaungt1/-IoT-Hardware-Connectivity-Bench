from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .adapters import passive_inspect_device, run_adapter_test
from .ble import BleMonitor
from .bridge import SerialBridge
from .device_intelligence import (
    arduino_board_inventory,
    enrich_hardware_list,
    inspect_hardware,
    metadata_providers,
)
from .host_wifi import scan_host_wifi
from .hardware import discover_usb_network_devices, inspect_usb_network_device, run_usb_network_diagnostic
from .host_inventory import host_network_inventory
from .network_discovery import discover_network_devices
from .operations import OperationError, OperationManager
from .service_discovery import discover_services
from .serial_diagnostics import probe_sensor_diagnostics, run_sensor_diagnostic, supports_sensor_diagnostics
from .storage import StateStore
from .tool_registry import tool_registry
from .usb_inventory import scan_usb_devices
from .workspace import DeviceWorkspace, WorkspaceError


ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "web"
load_dotenv(ROOT / ".env")
store = StateStore(Path(os.getenv("IOT_BENCH_DB") or os.getenv("LUMNI_IOT_DB", ROOT / "ai-api" / "data" / "iot.db")))
workspace = DeviceWorkspace(ROOT)
operations = OperationManager(ROOT, store, workspace)
bridge = SerialBridge(os.getenv("IOT_BENCH_PORT") or os.getenv("LUMNI_IOT_PORT"))
ble_monitor = BleMonitor()


async def ble_loop() -> None:
    while True:
        await ble_monitor.scan()
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(_: FastAPI):
    bridge.start()
    task = asyncio.create_task(ble_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        bridge.stop()


app = FastAPI(title="IoT Hardware Connectivity Bench API", version="0.2.0", lifespan=lifespan)


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


class WorkspaceWritePlanRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=512)
    root_id: str = Field(min_length=1, max_length=64)
    path: str = Field(min_length=1, max_length=512)
    content: str = Field(max_length=524_288)
    expected_sha256: str = Field(min_length=64, max_length=64)


async def status_payload() -> dict:
    payload = bridge.snapshot()
    payload["ble"] = await ble_monitor.snapshot()
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
    return {"ok": True, "service": "iot-hardware-connectivity-bench"}


@app.get("/api/status")
async def status() -> dict:
    return await status_payload()


@app.get("/api/ports")
async def ports() -> list[dict]:
    return bridge.ports()


@app.get("/api/hardware")
async def hardware() -> list[dict]:
    serial_devices = bridge.ports()
    network_devices = await asyncio.to_thread(discover_usb_network_devices)
    raw_usb = await asyncio.to_thread(scan_usb_devices)
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
    return await asyncio.to_thread(enrich_hardware_list, [*serial_devices, *network_devices, *passive_devices])


def _model_setting_key(identifier: str) -> str:
    import hashlib

    return f"device_model:{hashlib.sha256(identifier.encode('utf-8')).hexdigest()}"


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
    elif profile.get("kind") == "serial":
        live = await asyncio.to_thread(passive_inspect_device, profile)
        if supports_sensor_diagnostics(profile):
            live = live or {}
            live["diagnostic"] = await asyncio.to_thread(probe_sensor_diagnostics, str(profile["device"]))
    assigned_model = store.get_setting(_model_setting_key(str(profile["id"])))
    return await asyncio.to_thread(inspect_hardware, profile, live, assigned_model)


@app.get("/api/metadata/providers")
async def metadata_provider_status() -> dict:
    providers = await asyncio.to_thread(metadata_providers)
    return {"providers": providers, "available_count": sum(1 for item in providers if item["available"])}


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
    return {"saved": True, "identifier": selection.identifier, "model": selection.model}


@app.post("/api/device/test")
async def run_device_test(request: DeviceTestRequest) -> dict:
    profile = await _find_hardware(request.identifier)
    if request.test_id == "presence":
        return {"test_id": request.test_id, "passed": True, "summary": f"{profile['name']} is present at {profile.get('device')}."}
    if request.test_id == "service_check" and profile.get("kind") == "usb_network":
        checked = await asyncio.to_thread(inspect_usb_network_device, request.identifier)
        passed = bool(checked.get("online") and any(checked.get("services", {}).values()))
        return {"test_id": request.test_id, "passed": passed, "summary": "SSH and HTTP services verified." if passed else "No supported target service answered.", "evidence": checked}
    if request.test_id == "serial_protocol" and supports_sensor_diagnostics(profile):
        result = await asyncio.to_thread(probe_sensor_diagnostics, str(profile["device"]))
        passed = bool(result.get("ready"))
        return {"test_id": request.test_id, "passed": passed, "summary": "Compatible serial diagnostic protocol verified." if passed else "No compatible diagnostic protocol answered.", "evidence": result}
    if request.test_id == "i2c_inventory" and supports_sensor_diagnostics(profile):
        try:
            result = await asyncio.to_thread(run_sensor_diagnostic, str(profile["device"]), "i2c")
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"test_id": request.test_id, "passed": bool(result.get("passed")), "summary": f"I2C scan completed with {result.get('count', 0)} responding address(es).", "evidence": result}
    if request.test_id.startswith("sensor:") and supports_sensor_diagnostics(profile):
        sensor_id = request.test_id.split(":", 1)[1]
        try:
            result = await asyncio.to_thread(run_sensor_diagnostic, str(profile["device"]), sensor_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        passed = bool(result.get("passed"))
        return {
            "test_id": request.test_id,
            "passed": passed,
            "summary": f"{sensor_id} returned live data." if passed else f"{sensor_id} did not pass its live diagnostic.",
            "evidence": result,
        }
    try:
        adapter_result = await asyncio.to_thread(run_adapter_test, profile, request.test_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if adapter_result is not None:
        return {"test_id": request.test_id, **adapter_result}
    raise HTTPException(status_code=409, detail="This test requires a compatible adapter or approved diagnostic firmware")


@app.get("/api/tools")
async def tools() -> dict:
    return await asyncio.to_thread(tool_registry)


@app.get("/api/device/operations")
async def device_operations(identifier: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _inspect_profile(profile)
    items = await asyncio.to_thread(operations.capabilities, profile, inspection)
    return {"identifier": identifier, "operations": items}


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


@app.get("/api/operations/history")
async def operation_history(identifier: str | None = None) -> dict:
    items = await asyncio.to_thread(operations.history, identifier)
    return {"identifier": identifier, "events": items}


@app.get("/api/workspace")
async def device_workspace(identifier: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _inspect_profile(profile)
    return await asyncio.to_thread(workspace.inventory, inspection)


@app.get("/api/workspace/file")
async def workspace_file(identifier: str, root_id: str, path: str) -> dict:
    profile = await _find_hardware(identifier)
    inspection = await _inspect_profile(profile)
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
async def usb_inventory() -> dict:
    return await asyncio.to_thread(scan_usb_devices)


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
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(await status_payload())
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return


app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="web")
