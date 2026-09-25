# Threat Model

## Scope and trust boundaries

The bench is a local hardware tool. The browser and built-in MCP cross into a loopback FastAPI service;
that service crosses into USB/serial, network targets, local files, external tools, emulators, and the
local evidence database. Connected hardware, imported definitions/images/firmware, tool output, and MCP
arguments are untrusted input. A hosted browser is not allowed to control hardware directly.

## Threats and controls

| Threat | Current control | Verification |
| --- | --- | --- |
| Remote or malicious-site access to local hardware | HTTP and both WebSockets require a loopback client; browser origins must also be loopback. Launchers bind `127.0.0.1`. | `test_local_security.py`; browser and MCP live gates |
| Wrong-device or stale write | Physical fingerprint, selected identifier, target lock, expiring plan/token, fresh approval, and operation receipt | operation/control suites |
| Unknown-pin damage | No automatic brute force; target-specific probe/control capability and electrical constraints required | probe-matrix and control-profile suites |
| Bridge mistaken for board | Separate interface, bridge, target, board, component, pin, runtime, and attachment evidence layers | evidence graph/policy suites |
| Secret or private evidence disclosure | Runtime data ignored; recursive redaction and retroactive scrub; tracked plus non-ignored source scan; no fixed firmware credential | storage and privacy gates |
| Archive/XML/SVG/image traversal or execution | Size/type bounds, structured parsers, path containment, SVG sanitization, no uploaded-byte execution | definition, OCR, workspace, firmware-intelligence suites |
| Toolchain dependency compromise | Pinned API/tool requirements, split environments, checksummed standalone tools, audits, SBOMs, license inventory | CI supply-chain gates |
| Unbounded child process | Allowlisted commands/arguments, resolved executables, fixed working roots, timeouts, bounded live output, process-tree cleanup, operator/device-removal cancellation | operation, emulation, simulation, diagnostic suites |
| MCP confused deputy | Loopback stdio, manifest scopes, redacted resources, no credentials/arbitrary shell/approval/physical execution | `verify_mcp.py` |
| Camera memory/backpressure exhaustion | Latest-frame bridge, one pending browser decode, bounded metrics, independent WebSocket clients, RSS/thread budget | live browser, 1,800-second multi-client soak, and measured-memory soak |

## Release-blocking residual risks

- Hosted access needs authenticated TLS, tenant isolation, a separately authenticated local hardware agent,
  rate limits, revocation, and audit export. The current API must not be internet-exposed.
- Signed installers, signed updates, rollback, clean-machine tests, and release provenance remain required.
- Hardware writes need per-family recovery fixtures and deliberate interruption tests before public enablement.
- Third-party package/art licenses need human approval; generated metadata is not legal review.
- A broader physical fixture matrix, deliberate USB removal/rebind runs, and long radio reconnect soaks are required for release evidence; the attached camera's 30-minute multi-client soak passes.
