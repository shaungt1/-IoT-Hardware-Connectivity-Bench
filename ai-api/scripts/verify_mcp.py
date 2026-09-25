from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    api_root = Path(__file__).resolve().parents[1]
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(api_root / "mcp_server.py")],
        cwd=str(api_root),
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            required = {
                "list_hardware",
                "inspect_device",
                "bench_status",
                "get_api_contract",
                "list_adapter_manifests",
                "get_prototype",
                "simulate_prototype",
                "list_emulation_platforms",
                "verify_emulation_platform",
                "run_emulated_firmware",
                "analyze_board_image",
                "diagnose_bench_tool",
                "get_probe_matrix",
                "scan_bench_instruments",
                "list_device_operations",
                "plan_device_operation",
                "run_supported_test",
                "get_test_pack",
                "list_workspace_files",
                "read_workspace_file",
                "operation_history",
                "evidence_history",
                "export_evidence",
            }
            missing = required - names
            if missing:
                raise RuntimeError(f"Missing MCP tools: {sorted(missing)}")
            result = await session.call_tool("list_hardware", {"force_reconcile": False})
            if result.isError or not result.content:
                raise RuntimeError("MCP list_hardware did not return inventory")
            resources = await session.list_resources()
            if not any(str(item.uri) == "bench://hardware" for item in resources.resources):
                raise RuntimeError("bench://hardware resource is missing")
            if not any(str(item.uri) == "bench://evidence" for item in resources.resources):
                raise RuntimeError("bench://evidence resource is missing")
            if not any(str(item.uri) == "bench://events" for item in resources.resources):
                raise RuntimeError("bench://events resource is missing")
            if not any(str(item.uri) == "bench://capabilities" for item in resources.resources):
                raise RuntimeError("bench://capabilities resource is missing")
            prompts = await session.list_prompts()
            prompt_names = {prompt.name for prompt in prompts.prompts}
            required_prompts = {"inspect_hardware_safely", "review_circuit_design"}
            if required_prompts - prompt_names:
                raise RuntimeError(f"Missing MCP prompts: {sorted(required_prompts - prompt_names)}")
            permissions = await session.call_tool("get_mcp_permissions", {})
            if permissions.isError or not permissions.content:
                raise RuntimeError("MCP permission manifest did not respond")
            contract = await session.call_tool("get_api_contract", {})
            if contract.isError or not contract.content:
                raise RuntimeError("MCP API contract did not respond")
            print(f"VERIFY_OK: {len(names)} MCP tools, {len(prompt_names)} prompts, and hardware/evidence/events/capabilities resources responded through stdio.")


if __name__ == "__main__":
    asyncio.run(main())
