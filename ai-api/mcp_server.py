from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


API_BASE = os.getenv("IOT_BENCH_API", "http://127.0.0.1:8765").rstrip("/")
mcp = FastMCP(
    "IoT Hardware Connectivity Bench",
    instructions=(
        "Inspect connected hardware and bench evidence before making claims. "
        "Operation tools create plans only; physical mutation still requires explicit approval in the bench UI/API."
    ),
)


async def api(method: str, path: str, **kwargs: Any) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        response = await client.request(method, path, **kwargs)
    if response.is_error:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text[:500]
        raise RuntimeError(f"IoT bench API returned {response.status_code}: {detail}")
    return response.json()


@mcp.tool()
async def list_hardware(force_reconcile: bool = False) -> list[dict[str, Any]]:
    """List host-visible circuit targets and passive peripherals without opening either."""
    return await api("GET", "/api/hardware", params={"force": str(force_reconcile).lower()})


@mcp.tool()
async def inspect_device(identifier: str) -> dict[str, Any]:
    """Run the bench's evidence-based inspection for one hardware identifier."""
    return await api("POST", "/api/device/inspect", json={"identifier": identifier})


@mcp.tool()
async def bench_status() -> dict[str, Any]:
    """Read current bridge, camera, radio, telemetry, and hotplug status."""
    return await api("GET", "/api/status")


@mcp.tool()
async def get_mcp_permissions() -> dict[str, Any]:
    """Read the MCP permission manifest and its explicit mutation boundaries."""
    return await api("GET", "/api/mcp/manifest")


@mcp.tool()
async def get_api_contract() -> dict[str, Any]:
    """Read API/schema versions, compatibility policy, surfaces, and hosted-release boundary."""
    return await api("GET", "/api/contract")


@mcp.tool()
async def list_adapter_manifests() -> dict[str, Any]:
    """List installed hardware-adapter contracts, transports, families, timeouts, and safety modes."""
    return await api("GET", "/api/adapters")


@mcp.tool()
async def get_prototype(identifier: str) -> dict[str, Any]:
    """Read the versioned physical, simulated, and hybrid circuit graph for a device."""
    return await api("GET", "/api/prototype", params={"identifier": identifier})


@mcp.tool()
async def simulate_prototype(project: dict[str, Any]) -> dict[str, Any]:
    """Run isolated ngspice analysis for a supplied prototype graph; this never drives physical hardware."""
    return await api("POST", "/api/prototype/simulate", json=project)


@mcp.tool()
async def list_emulation_platforms(identity: str = "") -> dict[str, Any]:
    """List installed Renode virtual-board definitions and conservative identity matches."""
    return await api("GET", "/api/emulation/platforms", params={"identity": identity})


@mcp.tool()
async def verify_emulation_platform(platform_id: str) -> dict[str, Any]:
    """Load one allowlisted Renode platform model without running guest firmware or touching physical hardware."""
    return await api("POST", "/api/emulation/platform/verify", json={"platform_id": platform_id})


@mcp.tool()
async def run_emulated_firmware(
    platform_id: str,
    filename: str,
    content_base64: str,
    runtime_ms: int = 50,
    proof_address: int | None = None,
    proof_value: int | None = None,
) -> dict[str, Any]:
    """Run compatible ELF firmware for a bounded interval on an allowlisted virtual Renode board only."""
    return await api("POST", "/api/emulation/firmware/run", json={
        "platform_id": platform_id,
        "filename": filename,
        "content_base64": content_base64,
        "runtime_ms": runtime_ms,
        "proof_address": proof_address,
        "proof_value": proof_value,
    })


@mcp.tool()
async def analyze_board_image(filename: str, content_base64: str) -> dict[str, Any]:
    """Run local OCR on a board photo and return unconfirmed marking candidates without persisting image bytes."""
    return await api("POST", "/api/visual/analyze", json={"filename": filename, "content_base64": content_base64})


@mcp.tool()
async def diagnose_bench_tool(tool_id: str) -> dict[str, Any]:
    """Run the allowlisted passive diagnostic for one registered bench tool without touching target hardware."""
    return await api("GET", f"/api/tools/{tool_id}/diagnose")


@mcp.tool()
async def get_probe_matrix(identifier: str) -> dict[str, Any]:
    """Read safe probe coverage across runtime, buses, GPIO, debug, and external instruments."""
    return await api("GET", "/api/device/probe-matrix", params={"identifier": identifier})


@mcp.tool()
async def scan_bench_instruments() -> dict[str, Any]:
    """Passively inventory host-side debug probes and logic analyzers without opening a target."""
    return await api("GET", "/api/instruments")


@mcp.tool()
async def list_device_operations(identifier: str) -> dict[str, Any]:
    """List build, flash, backup, recovery, and file operations supported by current evidence."""
    return await api("GET", "/api/device/operations", params={"identifier": identifier})


@mcp.tool()
async def plan_device_operation(
    identifier: str,
    operation_id: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a reviewable operation plan. This never approves or executes physical mutation."""
    return await api(
        "POST",
        "/api/operations/plan",
        json={"identifier": identifier, "operation_id": operation_id, "parameters": parameters or {}},
    )


@mcp.tool()
async def run_supported_test(identifier: str, test_id: str) -> dict[str, Any]:
    """Run a capability-advertised bench test; unsupported or unsafe generic tests are rejected."""
    return await api("POST", "/api/device/test", json={"identifier": identifier, "test_id": test_id})


@mcp.tool()
async def get_test_pack(identifier: str) -> dict[str, Any]:
    """Read the versioned, target-specific test pack including risk and current availability."""
    return await api("GET", "/api/device/test-pack", params={"identifier": identifier})


@mcp.tool()
async def get_control_profile(identifier: str) -> dict[str, Any]:
    """Read negotiated physical-control capabilities without driving hardware."""
    return await api("GET", "/api/device/control-profile", params={"identifier": identifier})


@mcp.tool()
async def plan_control_action(identifier: str, action: str, pin: str, value: int | None = None) -> dict[str, Any]:
    """Plan a negotiated pin action for human review. MCP cannot approve or execute it."""
    return await api("POST", "/api/control/plan", json={"identifier": identifier, "action": action, "pin": pin, "value": value})


@mcp.tool()
async def list_workspace_files(identifier: str) -> dict[str, Any]:
    """List source/configuration files exposed for the selected device and local bench firmware."""
    return await api("GET", "/api/workspace", params={"identifier": identifier})


@mcp.tool()
async def read_workspace_file(identifier: str, root_id: str, path: str) -> dict[str, Any]:
    """Read one UTF-8 source/configuration file from an allowed workspace root."""
    return await api(
        "GET",
        "/api/workspace/file",
        params={"identifier": identifier, "root_id": root_id, "path": path},
    )


@mcp.tool()
async def operation_history(identifier: str | None = None) -> dict[str, Any]:
    """Read durable operation receipts, optionally restricted to one hardware identifier."""
    params = {"identifier": identifier} if identifier else None
    return await api("GET", "/api/operations/history", params=params)


@mcp.tool()
async def evidence_history(identifier: str | None = None, limit: int = 100) -> dict[str, Any]:
    """Read bounded, redacted inspection and test evidence, optionally for one device."""
    params: dict[str, Any] = {"limit": max(1, min(limit, 1000))}
    if identifier:
        params["identifier"] = identifier
    return await api("GET", "/api/history", params=params)


@mcp.tool()
async def export_evidence(identifier: str | None = None) -> dict[str, Any]:
    """Export redacted inspection, test, and operation evidence as versioned JSON."""
    params = {"identifier": identifier} if identifier else None
    return await api("GET", "/api/history/export", params=params)


@mcp.prompt()
def inspect_hardware_safely(identifier: str) -> str:
    """Evidence-first workflow for identifying a selected target without inventing topology."""
    return f"""Inspect hardware {identifier} using the bench tools.
1. Read the permission manifest and current inventory.
2. Inspect the exact identifier and separate host interface, bridge silicon, target MCU/SoC, board, components, pins, runtime, and attached peripherals.
3. Read the probe matrix. Run only tests explicitly advertised as available; never drive unknown pins.
4. State every unresolved claim and the exact definition, runtime, debug probe, or instrument needed to resolve it.
5. Do not request credentials, approval tokens, arbitrary commands, or physical mutation through MCP."""


@mcp.prompt()
def review_circuit_design(identifier: str, goal: str) -> str:
    """Review a prototype graph against observed hardware and electrical safety evidence."""
    return f"""Review the prototype for {identifier} against this goal: {goal}
Read inspection evidence, the prototype graph, control profile, and probe matrix first. Distinguish physical, simulated, hybrid, and user-defined nodes. Check voltage, direction, ground, current-limiting, bus addressing, and unmodeled components. Treat a drawn wire as design intent, never proof of physical wiring. Propose tests or an operation plan only when the adapter advertises the capability; MCP cannot approve or execute mutations."""


@mcp.resource("bench://hardware")
async def hardware_resource() -> str:
    """Current host-visible hardware inventory as JSON."""
    import json

    return json.dumps(await list_hardware(), indent=2)


@mcp.resource("bench://evidence")
async def evidence_resource() -> str:
    """Recent redacted bench evidence as JSON."""
    import json

    return json.dumps(await evidence_history(limit=100), indent=2)


@mcp.resource("bench://events")
async def events_resource() -> str:
    """Current bounded host-device event snapshot for polling MCP clients."""
    import json

    status = await bench_status()
    return json.dumps({
        "schema_version": "1.0",
        "device_state": status.get("device_state", {}),
        "event_source": status.get("device_events", {}),
        "operations": status.get("operations", {}),
    }, indent=2)


@mcp.resource("bench://capabilities")
async def capabilities_resource() -> str:
    """Versioned MCP scopes, contracts, and non-bypassable safety boundaries."""
    import json

    return json.dumps(await get_mcp_permissions(), indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
