from __future__ import annotations

import argparse
import json

from .inventory import collect_inventory, filter_devices
from .mcp_server import main as run_mcp_main
from .web import run_web_server


def main() -> None:
    parser = argparse.ArgumentParser(description="IoT Hardware Connectivity Bench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="Print the current hardware inventory as JSON")
    inventory_parser.add_argument("--kind", help="Only include devices of this kind")
    inventory_parser.add_argument("--query", help="Filter devices by identifier or summary text")
    inventory_parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON output")

    web_parser = subparsers.add_parser("web", help="Run the local web UI")
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--port", default=8765, type=int)

    subparsers.add_parser("mcp", help="Run the MCP server over stdio")

    args = parser.parse_args()
    if args.command == "inventory":
        inventory = collect_inventory()
        if args.kind or args.query:
            inventory = {
                **inventory,
                "device_count": len(filter_devices(inventory, kind=args.kind, query=args.query)),
                "devices": filter_devices(inventory, kind=args.kind, query=args.query),
            }
        indent = 2 if args.pretty else None
        print(json.dumps(inventory, indent=indent))
        return

    if args.command == "web":
        run_web_server(host=args.host, port=args.port)
        return

    run_mcp_main()


if __name__ == "__main__":
    main()

