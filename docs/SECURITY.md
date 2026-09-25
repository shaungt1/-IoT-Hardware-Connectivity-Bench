# Security

## Runtime boundary

The FastAPI application binds to loopback by default. Its Python environment is `.venv`; firmware,
debug, and flashing CLIs run from the separate `.tool-venv`. Runtime databases, captures, credentials,
private keys, logs, build output, and both environments are ignored by Git.

Device mutation is never inferred from a wire or a scan. Disruptive and destructive operations require
a target-bound plan and explicit approval. The built-in MCP can create a plan but cannot approve or
execute it.

Local firmware/tool processes expose bounded live output, run in a separate process group, and can be
cancelled by the operator or target removal. Cancellation terminates the process tree and records an
audit receipt.

The API also enforces this boundary internally: HTTP clients must be loopback, browser origins must be
loopback when present, and both WebSocket transports reject remote clients/origins before accepting.
See `THREAT_MODEL.md` for the threat-to-control matrix and release-blocking residual risks.

## Dependency gates

CI audits the API environment with no vulnerability exceptions and audits React production
dependencies at high severity or above. The isolated hardware-tool environment has a narrow upstream
exception for PlatformIO Core 6.1.18:

- `PYSEC-2026-2132` affects Click, which PlatformIO pins below the fixed release.
- `PYSEC-2026-1941`, `PYSEC-2026-1942`, `PYSEC-2026-161`, `PYSEC-2026-2281`,
  `PYSEC-2026-2280`, `PYSEC-2026-249`, and `PYSEC-2026-248` affect Starlette versions that
  PlatformIO pins below the fixed releases.

The bench invokes only PlatformIO's local `run`/`upload` CLI. It does not start PlatformIO Home, its web
server, or a remotely reachable tool service. The exception applies only inside `.tool-venv`; the bench
API uses patched FastAPI/Starlette releases in `.venv`. CI names every accepted advisory explicitly, so
an additional toolchain vulnerability fails the audit. Remove these exceptions when PlatformIO releases
a compatible dependency set.

Every CI run also creates separate CycloneDX SBOMs for the API, React production dependencies, and the
isolated hardware-tool environment. The reports are uploaded as a workflow artifact and are not committed
because they include build-specific dependency metadata. Generate the same reports locally with
`.\scripts\generate-sbom.ps1`.

The same command writes `artifacts/dependency-inventory.json`, separating API, hardware-tool, and React
production packages and flagging undeclared or strong-copyleft metadata for human review. This inventory
is evidence for a release review, not legal approval.

## Reporting

Do not include Wi-Fi names or passwords, device serial numbers, MAC addresses, IP addresses, captures,
firmware dumps, private source, or database files in a report. Provide the affected version, a minimal
reproduction using synthetic identifiers, impact, and a suggested remediation through the repository's
private security-reporting channel once it is configured.
