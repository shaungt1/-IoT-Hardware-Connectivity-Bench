# Product Architecture

Status: proposed target architecture  
Date: 2026-09-24

## Architectural decision

Build one local-first product around a native hardware service, a normalized evidence graph, a
versioned adapter SDK, and a policy-controlled operation engine. React, the validation HTML client,
CLI commands, public APIs, VS Code, and MCP are clients of the same application services. No client
may bypass safety, evidence, locking, approval, or audit rules.

## Runtime topology

```text
React / HTML / CLI / VS Code / MCP
                 |
       Public application API
                 |
  Identity | Evidence | Tests | Files | Operations | Communications
                 |
     Policy and operation engine
                 |
 Adapter registry + definition providers + tool runners
                 |
 USB | serial | network | BLE | debug | filesystem | fixtures
                 |
          Physical hardware
```

The hardware bridge runs natively on the host because Windows COM, USB, Bluetooth, debug adapters,
mounted volumes, and device arrival events should not depend on container passthrough. Optional
observability, catalog mirrors, databases, and hosted collaboration services may run in containers.

## Bounded contexts

| Context | Responsibility | Does not own |
| --- | --- | --- |
| Host inventory | Enumerate and correlate host-visible interfaces | Board-model guesses |
| Identity | Resolve bridge, processor, module, carrier, runtime, and physical unit | Test execution |
| Evidence | Claims, sources, confidence, contradictions, history | Vendor-specific probing |
| Definitions | Parse and normalize SVD, device trees, manifests, pin maps, BOMs | Live verification |
| Adapters | Detect targets and expose typed capabilities | UI rendering |
| Communications | BLE/Wi-Fi/Ethernet/protocol sessions and traffic | Application observability |
| Tests | Select packs, execute measurements, evaluate criteria | Flashing by side effect |
| Operations | Plan, approve, lock, run, cancel, audit, and recover writes | Unreviewed shell access |
| Firmware | Workspaces, builds, artifacts, backup, flash, verify, restore | Target identification |
| Firmware intelligence | Authorized acquisition, carving, software graph, binary/register analysis | Treating analysis as physical verification |
| Circuit graph | Boards, parts, pins, buses, nets, evidence, constraints | Analog solver internals |
| Providers | Vendor/component/document lookup and caching | Promoting claims to verified |
| Observability | Product logs, metrics, traces, health, diagnostics | Device protocol semantics |

## Host classification

Inventory every interface, then present four explicit groups:

1. `circuit_target` - inspectable controller, computer, accelerator, SDR, module, or custom circuit.
2. `transport_bridge` - CP210x, CH34x, FTDI, CMSIS-DAP, J-Link, ST-Link, DFU, boot-ROM endpoint.
3. `unresolved_candidate` - evidence suggests hardware work is possible but the target is unknown.
4. `passive_peripheral` - finished HID, MIDI, camera, storage, display, audio, printer, or similar
   product that remains visible but does not dominate the circuit workflow.

Classification is independent of selection and can change as evidence arrives. A bridge and its
downstream target remain distinct identity layers even when the UI presents one physical board.

## Evidence graph

Use SQLite for the local release and normalized JSON at API boundaries. Do not add a graph database
until query evidence shows SQLite is inadequate.

Core entities:

- `physical_device` - stable fingerprint and reconnect history.
- `interface` - COM, USB, PCIe, network, BLE, filesystem, media, debug, or fixture endpoint.
- `identity_layer` - bridge, processor, module, carrier, runtime, or attachment.
- `component` - MCU, memory, regulator, sensor, radio, display, camera, connector, or accelerator.
- `pin` and `pin_function` - physical location, electrical constraints, aliases, and mux functions.
- `bus` and `attachment` - controller, address/chip-select, connection, response history.
- `claim` - subject, predicate, value, unit, status, confidence, timestamp, and expiry.
- `evidence` - raw or summarized observation, collector, tool version, artifact hash, and source URL.
- `test_run` and `measurement` - inputs, environment, output, criteria, result, and evidence links.
- `operation` and `approval` - plan, risk, target binding, lock, output, artifact, and receipt.
- `definition` - provider, source version, license, checksum, parser version, and normalized output.

Contradictory claims coexist. Resolution selects a current claim but never deletes the audit trail.
Volatile evidence has an expiry and becomes `stale` when its target disconnects or validity window ends.

## Definition ingestion

The normalization pipeline is:

```text
source fetch -> checksum/license -> source parser -> normalized definition
             -> identity match -> expected claims -> live verification overlays
```

Initial source types:

- CMSIS Device Family Packs and CMSIS-SVD for Arm processor peripherals and registers.
- Zephyr and Linux device trees plus bindings for board topology and runtime nodes.
- Arduino, PlatformIO, CircuitPython, and vendor board definitions for board names and pins.
- Local signed manifests for unsupported or custom hardware.
- EDA imports and BOMs for user-provided designs.

CMSIS-SVD describes memory-mapped processor peripherals and register fields; Device Family Packs are
the normal distribution unit. It does not describe every carrier-board connection. Device tree data
describes hardware topology, while bindings give nodes semantic meaning. These sources complement
each other but remain `expected` until the selected unit provides confirming evidence. See the
[CMSIS-SVD overview](https://arm-software.github.io/CMSIS_5/SVD/html/index.html),
[Open-CMSIS-Pack device description](https://open-cmsis-pack.github.io/Open-CMSIS-Pack-Spec/main/html/pdsc_devices_pg.html),
[Zephyr bindings](https://docs.zephyrproject.org/latest/build/dts/bindings.html), and
[Linux device-tree model](https://docs.kernel.org/6.4/devicetree/usage-model.html).

## Adapter SDK

Adapters are versioned plugins registered by manifest, not UI conditionals. The minimum contract is:

```python
class HardwareAdapter(Protocol):
    manifest: AdapterManifest

    async def score(self, context: ProbeContext) -> MatchResult: ...
    async def identify(self, context: ProbeContext) -> IdentityResult: ...
    async def inspect(self, context: ProbeContext) -> EvidenceBundle: ...
    async def capabilities(self, context: ProbeContext) -> list[Capability]: ...
    async def tests(self, context: ProbeContext) -> list[TestDescriptor]: ...
    async def plan(self, request: OperationRequest) -> OperationPlan: ...
```

The manifest declares supported interface types, target families, tools, permissions, maximum risk,
timeouts, concurrency, recovery requirements, fixture requirements, and contract-test fixtures.
Adapters return typed evidence and operation plans; they do not mutate global state or render UI.

Execution rules:

- Probe budgets bound ports, baud rates, reset attempts, packets, and time.
- Read-only and write operations use separate methods and permissions.
- Each operation is bound to a stable target fingerprint and current interface generation.
- One target lock prevents simultaneous probe, test, flash, and terminal ownership conflicts.
- Adapter subprocesses have structured stdout/stderr, cancellation, timeout, and kill-tree behavior.
- Third-party adapters move to isolated worker processes before public plugin distribution.

## Test-pack SDK

Tests are data-driven packs selected from capabilities and evidence. A pack contains prerequisites,
risk, setup, stimulus, sampling, expected range or invariant, cleanup, timeout, and result formatter.
It may call adapter capabilities but may not flash firmware implicitly.

Test families include presence, serial protocol, I2C inventory, sensor sampling, GPIO loopback,
PWM/ADC, storage read/write, camera frames and rate, display pattern and confirmation, microphone and
audio, BLE advertisement/GATT, Wi-Fi association/traffic, Ethernet, MQTT, CoAP, HTTP, SSH, RTSP,
accelerator inference, SDR receive, thermal/voltage, and reboot/reconnect.

Expected sensors from a board definition produce unavailable tests until a runtime or fixture exposes
them. A successful address response verifies an address, not a unique component model.

## Communication workspace

Communication sessions are first-class resources with source interface, target, protocol, direction,
credentials reference, state, counters, events, and capture policy. Providers implement:

- BLE central scanning/GATT and supported device-peripheral control.
- Wi-Fi discovery, association, hosted AP state, IP services, and traffic checks.
- Ethernet/USB networking, mDNS/DNS-SD, SSDP, and bounded private-subnet discovery.
- MQTT client sessions through Eclipse Paho and an optional local Mosquitto broker.
- CoAP client/server sessions through aiocoap.
- HTTP/WebSocket, SSH, serial, RTSP, and vendor protocols.

MQTT is device/application messaging. OpenTelemetry is product observability. They may carry related
measurements but are not interchangeable.

## Firmware and code workspace

The browser workspace uses Monaco for desktop code editing and diff, xterm.js for a terminal surface,
and the existing allowlisted server operations for actual process and device access. Monaco is not
supported on mobile browsers, so mobile receives read-only source and operation status rather than a
broken editor. See [Monaco](https://microsoft.github.io/monaco-editor/) and
[xterm.js](https://xtermjs.org/docs/).

No browser terminal is an unrestricted host shell. Terminal sessions bind to an approved transport or
named command profile. Firmware operations follow: inspect -> backup -> build -> plan -> approve ->
flash -> verify -> reconnect -> rollback guidance. Every artifact is hashed.

## Firmware intelligence

Firmware intelligence is an optional analysis pipeline over a user-supplied, vendor-supplied, or
explicitly authorized device image:

```text
acquire -> hash/read receipt -> carve layers -> detect architecture/format
        -> static analysis -> software graph -> SVD/device-tree correlation
        -> hardware graph links -> user-reviewable findings
```

The software graph models boot ROM references, bootloaders, partitions, RTOS/kernel, filesystems,
libraries, drivers, middleware, applications, configuration, symbols, functions, call/reference
edges, strings, register accesses, device paths, services, packages, certificates, and analysis
confidence. It never stores decompiler output as source truth or reports a referenced peripheral as a
verified populated component.

Initial analyzers are Binwalk v3 for embedded file/data identification and entropy; Ghidra headless
for scripted multi-architecture analysis; and CMSIS-SVD correlation for translating memory-mapped
addresses into named peripherals/registers. Radare2 or Rizin is evaluated as a lighter JSON/scriptable
engine. EMBA is an optional isolated Linux/container profile for large Linux firmware because its own
documentation warns that developer mode may execute malicious code. Avatar2 enters only with the later
hybrid-analysis milestone.

Firmware extraction, reverse engineering, decryption, or security analysis is allowed only for
hardware/images the operator owns or is authorized to analyze. Read protection, secure boot, signed
images, encryption, and one-time-programmable regions are reported as boundaries, not bypassed.

Sources: [Binwalk v3](https://github.com/ReFirmLabs/binwalk/blob/master/README.md),
[Ghidra headless analyzer](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md),
[Ghidra SLEIGH](https://ghidra.re/ghidra_docs/languages/html/sleigh.html),
[radare2 analysis](https://book.rada.re/analysis/code_analysis.html),
[EMBA](https://github.com/e-m-b-a/emba), and
[Avatar2](https://github.com/avatartwo/avatar2).

## Circuit graph and studio

The circuit graph is the shared source of truth for device visualization, tests, simulation, and EDA
exchange. React Flow renders editable board, component, pin, bus, and net nodes but does not own the
domain model. Constraint validation runs in the backend and reports voltage, direction, bus, reserved
pin, boot-strap, current, and address conflicts.

Simulation adapters translate supported graph subsets into CircuitJS or ngspice for circuit behavior
and Renode for supported digital platform/firmware models. Results return as evidence linked to the
graph revision. Simulation is labeled separately from measurement on physical hardware.

## API boundaries

### Internal application API

Typed Python services own transactions, policy, and domain behavior. Adapters depend on SDK types and
ports, not FastAPI request objects or database tables.

### Public local API

- Versioned REST under `/api/v1` with generated OpenAPI.
- Server-sent events or WebSocket streams for inventory, operation, terminal, and measurement events.
- Idempotency keys for commands and optimistic revisions for mutable resources.
- Problem Details errors with a stable code, user message, technical detail, and remediation.
- Scoped capability tokens for disruptive operations; no ambient write authority.
- Pagination, filtering, schema version, and deprecation headers from the first public release.

### Hosted API

The optional hosted service receives only explicitly synchronized data. Device control remains local
through a mutually authenticated agent. Tenant identity, quotas, billing, retention, region, and data
deletion are hosted concerns and do not leak into the local core.

### Built-in MCP server

The local product bundles an MCP server as a separately enabled capability. It starts read-only and
loopback/stdio-only by default; remote HTTP mode requires explicit configuration and authorization.
MCP is a thin facade over the public application services. Resources expose device summaries,
evidence graphs, definitions, test results, operation receipts, and documentation. Tools expose
refresh, inspect, plan, run safe tests, build, and approved operations. Prompts can guide bring-up and
fault diagnosis. Tool calls never receive direct serial handles or shell access.

The current MCP architecture uses JSON-RPC with discoverable tools, resources, and prompts. HTTP
deployments require authorization and audience-bound tokens; local stdio deployments use environment
credentials and OS process trust. See the official [architecture](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/learn/architecture.mdx)
and [authorization specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/authorization.mdx).

## Observability

Instrument the product with OpenTelemetry traces, metrics, and correlated structured logs. The local
default writes a bounded diagnostic store and exposes health/metrics. Optional profiles export to an
OpenTelemetry Collector and then Prometheus/Grafana or SigNoz. OpenTelemetry is vendor-neutral and
does not provide its own storage/UI backend; see its [overview](https://opentelemetry.io/docs/what-is-opentelemetry/)
and [signals](https://opentelemetry.io/docs/concepts/signals/).

Device measurements remain domain records first. Selected measurements may also be exported as
metrics, but high-cardinality device IDs, raw frames, secrets, source code, and serial payloads are
excluded by default.

## Security and safety

- Bind to loopback by default; remote mode requires authentication, TLS, explicit allowed interfaces,
  and a clear UI indicator.
- Store secrets in the OS keychain or an external secret provider, never SQLite or logs.
- Enforce least privilege, target binding, expiry, and step-up approval for writes.
- Redact credentials and user data before persistence or telemetry export.
- Pin tool downloads by version and checksum; generate an SBOM and provenance for releases.
- Sign release artifacts, adapter packages, definition bundles, and test packs.
- Validate archives and paths; never let definitions or plugins escape their sandbox.
- Maintain vulnerability reporting, dependency scanning, secret scanning, and release threat models.
- Publish electrical safety limits and require protected fixtures for active pin work.

## Deployment profiles

| Profile | Components | Purpose |
| --- | --- | --- |
| Developer | Native FastAPI, Vite, SQLite, local tools | Contribution and live hardware work |
| Local release | Signed native service plus bundled React assets | Normal offline product use |
| Lab | Local agents plus authenticated team server | Shared fixtures and remote scheduling |
| Optional observability | Collector plus Grafana/Prometheus or SigNoz | Deep product diagnostics |
| Hosted product | Control plane, metadata, collaboration, billing | Optional paid services |

The local release must remain fully useful without Docker, cloud accounts, API keys, or an AI model.
