# Built-in MCP

The bench includes a local stdio MCP server in `ai-api/mcp_server.py`. It uses the same validated
HTTP API as the React application, so UI users and agents share hardware identities, evidence,
prototype graphs, capability checks, operation plans, and audit receipts.

`get_api_contract` publishes API/schema versions, compatibility rules, the protected-mutation boundary,
and the explicit statement that the current local service is not a hosted multi-user control plane.

## Safety boundary

- Read tools expose inventory, inspection, live status, prototype graphs, workspaces, and receipts.
- `run_supported_test` can only invoke a test already advertised by the selected adapter.
- `plan_device_operation` creates a reviewable plan but cannot approve or execute it.
- Flashing, GPIO drive, file writes, and other physical mutations remain behind the bench's explicit
  approval token and hardware fingerprint checks. MCP has no approval/execute tool.

## Launch

Start the React/API bench first, then run `./start-mcp.ps1` on Windows or `./start-mcp.sh` on Linux.
Configure an MCP client with that script as a stdio command. Override `IOT_BENCH_API` only when the
local API uses a non-default address.

## Agent prompts and resources

- `inspect_hardware_safely` enforces layered identity, available-test checks, and explicit unknowns.
- `review_circuit_design` reviews physical/simulated/hybrid graphs without treating drawn wires as proof.
- `bench://capabilities` publishes the versioned scopes and non-bypassable safety boundary.
- `bench://hardware`, `bench://evidence`, and `bench://events` remain bounded read resources.
