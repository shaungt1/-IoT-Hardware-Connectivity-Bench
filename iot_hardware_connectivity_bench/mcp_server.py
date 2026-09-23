from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.mcpserver import MCPServer

from . import __version__
from .inventory import collect_inventory, filter_devices


def create_server() -> MCPServer:
    server = MCPServer(
        name="iot-hardware-connectivity-bench",
        title="IoT Hardware Connectivity Bench",
        version=__version__,
        instructions=(
            "Use these tools to inspect locally connected serial devices, cameras, "
            "storage devices and network interfaces before sending test commands."
        ),
    )

    @server.tool(description="Return a full snapshot of the connected hardware inventory.")
    def get_inventory() -> dict[str, Any]:
        return collect_inventory()

    @server.tool(description="List detected devices. Optionally filter by kind or text query.")
    def list_devices(kind: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
        inventory = collect_inventory()
        return filter_devices(inventory, kind=kind, query=query)

    @server.tool(description="Find one detected device by identifier or summary text.")
    def inspect_device(identifier: str) -> dict[str, Any]:
        inventory = collect_inventory()
        matches = filter_devices(inventory, query=identifier)
        if not matches:
            return {
                "found": False,
                "identifier": identifier,
                "message": "No matching device was detected.",
            }
        return {"found": True, "device": matches[0]}

    return server


async def run_mcp_server() -> None:
    await create_server().run_stdio_async()


def main() -> None:
    asyncio.run(run_mcp_server())

