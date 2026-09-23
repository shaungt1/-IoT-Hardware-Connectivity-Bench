# IoT Hardware Connectivity Bench

Version 1.0.01 provides a minimal local-first foundation for the bench:

- inventories connected serial devices, cameras, storage devices, and network interfaces
- exposes that inventory through a local MCP server for VS Code and agent workflows
- serves a lightweight web UI and JSON API for human inspection of attached hardware

## Quick start

```bash
python -m pip install -r requirements.txt
python -m iot_hardware_connectivity_bench inventory --pretty
python -m iot_hardware_connectivity_bench web
python -m iot_hardware_connectivity_bench mcp
```

## Available commands

- `python -m iot_hardware_connectivity_bench inventory --pretty` prints the current inventory snapshot
- `python -m iot_hardware_connectivity_bench inventory --kind serial` filters the snapshot to a device class
- `python -m iot_hardware_connectivity_bench web` runs the local web UI on `http://127.0.0.1:8765`
- `python -m iot_hardware_connectivity_bench mcp` runs the MCP server over stdio

## Tests

```bash
make test
```
