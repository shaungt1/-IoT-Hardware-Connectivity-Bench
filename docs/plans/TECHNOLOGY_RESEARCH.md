# Technology Research and Disposition

Status: proposed dependency decisions  
Date: 2026-09-24

This is a decision record, not an install list. Every dependency must pass license, maintenance,
security, platform, packaging, and measured-value review before it enters the default installation.
Tools with restrictive or unclear redistribution terms should be invoked as optional external tools
instead of vendored into the product.

## Decision scale

- **Adopt** - fits the architecture and should enter the planned core.
- **Integrate optionally** - useful behind an adapter or deployment profile, not a default dependency.
- **Evaluate** - prove with a time-boxed spike and fixtures before commitment.
- **Defer** - valid later, but not on the path to the first production release.
- **Avoid** - poor fit or maintenance risk.

## Hardware descriptions and metadata

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| CMSIS Device Family Packs | Adopt | Package index for Arm devices, algorithms, and SVD files | Vendor pack licenses vary; cache checksums and terms |
| CMSIS-SVD | Adopt | Normalize MCU peripheral/register maps after exact MCU identity | Silicon internals, not full carrier-board topology |
| `cmsis-svd` Python parser | Adopt | Parse SVD to typed objects/JSON | Pin version and add malformed-file tests |
| Zephyr devicetree + bindings | Adopt | Board topology, buses, aliases, chosen nodes, connected parts | Bindings are needed to interpret properties correctly |
| Linux live device tree/sysfs | Adopt | Verify runtime SoC/platform devices on reachable Linux targets | Shows kernel-visible/configured hardware, not every passive part |
| Arduino CLI definitions | Keep/adopt | Board identity, cores, programmers, pin variants | Family match may not prove an exact clone |
| PlatformIO boards/platforms | Keep/adopt | Cross-vendor board metadata and build environments | Normalize without coupling domain code to PlatformIO |
| CircuitPython board/runtime data | Keep/adopt | Mounted board ID, pins, libraries, runtime buses | Requires a compatible runtime/filesystem |
| Vendor APIs and catalogs | Integrate optionally | Documents, part metadata, lifecycle, packages, specifications | Cache, rate-limit, cite, and never turn catalog matches into verification |
| User manifests/BOM/schematic | Adopt | Custom boards and unsupported vendors | Signed/versioned; user declaration remains distinct from measurement |

Sources: [CMSIS-SVD](https://arm-software.github.io/CMSIS_5/SVD/html/index.html),
[Open-CMSIS-Pack device descriptions](https://open-cmsis-pack.github.io/Open-CMSIS-Pack-Spec/main/html/pdsc_devices_pg.html),
[Zephyr bindings](https://docs.zephyrproject.org/latest/build/dts/bindings.html),
[Linux device tree](https://docs.kernel.org/6.4/devicetree/usage-model.html), and
[`cmsis-svd`](https://pypi.org/project/cmsis-svd/).

## Discovery, debug, buses, and programming

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| PyUSB/libusb + OS PnP APIs | Keep/adopt | USB/interface inventory and descriptors | Descriptors identify the interface, not necessarily target behind a bridge |
| pySerial | Keep/adopt | Serial ownership, framed runtimes, approved boot protocols | Never spray arbitrary bytes or baud rates at unknown devices |
| OpenOCD | Integrate optionally | JTAG/SWD identity, debug, flash, boundary scan where supported | Requires a compatible probe, wiring, target config, and voltage safety |
| pyOCD | Integrate optionally | CMSIS-DAP Arm discovery/debug and Python integration | Supported targets/probes only |
| probe-rs | Integrate optionally | Modern Rust-backed Arm/RISC-V probe path | Confirm supported chips and redistribution for each release |
| Vendor ROM tools | Adopt through adapters | Espressif, RP, Nordic, STM, AVR/SAMD, DFU and other identity/programming | Each protocol needs its own adapter and recovery process |
| sigrok/libsigrokdecode | Integrate optionally | Logic capture and UART/I2C/SPI/protocol decoding | Captures signals; it cannot guarantee a part identity by itself |
| USB I2C/SPI/UART/GPIO fixture | Adopt | Safe discovery and tests for boards without cooperative firmware | Protected hardware and explicit wiring/voltage profile required |
| Boundary scan | Evaluate | Net/interconnect tests for JTAG-capable designs | Needs BSDL, accessible chain, and board knowledge |
| Chip-off/general brute force | Avoid | Not a normal product feature | Unsafe, often destructive, legally sensitive, and not universal |

OpenOCD explicitly distinguishes JTAG boundary-scan capability from SWD debug-only behavior and notes
that target families layer different protocols over transports. That supports adapter-specific
probing rather than a universal brute-force button. See [OpenOCD transport documentation](https://openocd.org/doc/html/Debug-Adapter-Configuration.html)
and [transport architecture](https://openocd.org/doc/doxygen/html/transport_8c.html).

## Communications and device signals

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| Bleak/native BLE APIs | Keep/adopt | Host BLE central scan, GATT inspection, reads/writes, notifications | Peripheral-mode support is OS/hardware specific |
| Host Wi-Fi APIs | Adopt by OS adapter | Scan, association, profile, AP and state | Never expose saved passwords in API responses/logs |
| Zeroconf/mDNS and SSDP | Keep/extend | Discover advertised services | Discovery must stay bounded to approved networks |
| Eclipse Paho | Adopt | MQTT 3.1/3.1.1/5 client sessions and test packs | A client is not a broker |
| Eclipse Mosquitto | Integrate optionally | Local MQTT broker and interoperability fixture | Loopback by default; auth/TLS for network listeners |
| aiocoap | Adopt optionally | CoAP client/server inspection and tests | Platform feature coverage varies; enable security extras deliberately |
| HTTP/WebSocket/SSH/RTSP | Keep/extend | Service inspection, streaming, and target control | Use protocol-specific credentials and allowlists |
| SoapySDR/vendor RF tools | Evaluate | Generic SDR inventory and bounded receive tests | RF transmission requires regional/safety policy |

Paho provides MQTT clients for publish/subscribe, while Mosquitto supplies a broker and command-line
tools. aiocoap supplies asynchronous CoAP clients and servers. Sources:
[Paho Python](https://eclipse.dev/paho/clients/python/docs/),
[Mosquitto](https://www.mosquitto.org/documentation/), and
[aiocoap](https://aiocoap.readthedocs.io/en/latest/).

## Browser application and circuit studio

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| React + existing Vite client | Adopt | Production browser application | HTML client remains validation/recovery until parity |
| shadcn/Radix patterns | Adopt selectively | Accessible tabs, dialogs, accordions, tooltips, menus | Preserve existing visual system; avoid component churn |
| React Flow | Adopt | Circuit/evidence graph editor and interaction layer | Domain graph and validation remain backend-owned |
| ELK.js or Dagre | Evaluate | Automatic layout for imported topology | Layout is presentation, not electrical routing |
| Monaco Editor | Adopt for desktop | Source/config editor, language services, diff | Officially unsupported on mobile browsers |
| xterm.js | Adopt | Terminal rendering, serial/log/command sessions | Backend remains allowlisted; never expose ambient shell |
| Fritzing part definitions | Evaluate then import | Breadboard/schematic/PCB SVGs, connector positions, buses, and metadata | Validate source license per library; visual assets are not physical evidence |
| XFlow | Avoid | Former graph application framework | Project states it is no longer actively maintained and recommends X6 |

React Flow provides custom React nodes and interaction primitives suitable for the studio and has
examples for validation and persistence. XFlow's repository explicitly reports inactive maintenance.
See [React Flow](https://reactflow.dev/), [React Flow examples](https://reactflow.dev/examples),
[Monaco](https://microsoft.github.io/monaco-editor/), [xterm.js](https://xtermjs.org/), and
[XFlow](https://github.com/antvis/XFlow). Fritzing parts combine `.fzp` metadata with per-view SVGs,
connectors, and internal buses, which makes them useful import candidates for visual placement after
license and quality review; see the official [part format](https://github.com/fritzing/fritzing-app/wiki/2.1-part-file-format).

## Simulation and EDA interoperability

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| CircuitJS | Integrate optionally | Embeddable browser simulation for supported simple circuits | Not a general MCU/firmware simulator |
| ngspice | Integrate optionally | Analog/mixed-signal simulation from generated netlists | Models and convergence require engineering inputs |
| Renode | Evaluate, then integrate | Repeatable digital platform/firmware simulation and tests | Only supported or modeled peripherals exist |
| DigitalJS | Evaluate | Inspectable browser digital-logic/Verilog teaching view | Focused on synthesized digital logic, not complete IoT boards |
| SimulIDE | Reference/evaluate interchange | Desktop MCU plus simple analog/digital simulation | Do not make its desktop UI a required runtime dependency |
| Wokwi custom-chip model | Study, optional export | Reference for pin/property definitions and WASM behavior models | Chips API is beta and Wokwi is not the open core execution layer |
| KiCad IPC API and files | Adopt later | Import/export schematics, connectivity, symbols, BOMs | Version compatibility and user-installed KiCad required |
| Fritzing | Defer/import-export | Beginner breadboard/schematic/PCB interchange | Not the internal source of truth or simulation engine |
| QEMU | Evaluate per platform | Linux/firmware emulation for supported machines | Hardware accuracy varies by modeled platform |

CircuitJS supports browser embedding; Renode supports custom peripheral models and automated tests;
KiCad's current IPC API is the intended external-application path, with headless and schematic support
expanding by KiCad version. Sources: [CircuitJS](https://github.com/sharpie7/circuitjs1),
[Renode peripheral models](https://renode.readthedocs.io/en/latest/advanced/writing-peripherals.html),
[Renode tests](https://renode.readthedocs.io/en/latest/introduction/testing.html),
[KiCad IPC API](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/),
[KiCad schematic API](https://docs.kicad.org/kicad-python/schematic.html),
[ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-41-manual.pdf), and
[Fritzing](https://fritzing.org/about/context),
[DigitalJS](https://github.com/tilk/digitaljs),
[SimulIDE](https://simulide.com/p/), and
[Wokwi custom chips](https://docs.wokwi.com/chips-api/getting-started).

The studio must support three explicit execution modes over one graph revision:

- `real` - tests and measurements come only from connected physical hardware.
- `simulated` - outputs come only from named simulator models and are labeled simulation evidence.
- `hybrid` - a declared bridge maps real interfaces to virtual peripherals or virtual controllers to
  real fixtures, with clocking, latency, ownership, and voltage boundaries recorded.

Hybrid mode is a later hardware-in-the-loop milestone, not a shortcut around adapter verification.

## Product observability

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| OpenTelemetry SDK | Adopt | Correlated product traces, metrics, and logs | Instrumentation standard, not storage or dashboard |
| OpenTelemetry Collector | Integrate optionally | Process/redact/export telemetry | Optional for normal local use |
| Prometheus | Integrate optionally | Scrape/store operational metrics | Not raw device-event or frame storage |
| Grafana | Integrate optionally | Advanced lab dashboards | Embedded product UI remains the normal workflow |
| SigNoz | Optional deployment profile | Self-hosted OpenTelemetry observability stack | Heavier than needed for a single local bench |

OpenTelemetry defines signals and export but intentionally leaves storage and visualization to other
tools. Grafana queries data sources such as Prometheus, while SigNoz is an OpenTelemetry-powered
observability backend. Sources: [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/),
[Collector architecture](https://opentelemetry.io/docs/specs/otel/overview/),
[Prometheus with Grafana](https://prometheus.io/docs/visualization/grafana/),
[Grafana data sources](https://grafana.com/docs/grafana/latest/datasources/), and
[SigNoz](https://signoz.io/docs/what-is-signoz/).

## APIs, agents, and integration

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| FastAPI/OpenAPI | Keep/adopt | Versioned local and hosted REST contract | Domain services must not depend on HTTP objects |
| WebSocket/SSE | Keep/extend | Inventory, operation, terminal, and measurement streams | Resume/backpressure/cancellation required |
| MCP Python or TypeScript SDK | Adopt after API stabilization | Agent resources, prompts, and policy-bound tools | Never grant direct shell, serial, or flash authority |
| VS Code extension API | Defer to v1 follow-up | Device tree, tests, logs, project association | Reuse public API; no separate hardware logic |
| Webhooks/event subscriptions | Adopt for public API | Integrations and automation | Signed delivery, retries, idempotency, redaction |

MCP provides tools, resources, prompts, discovery, and transport/authorization conventions. It should
be a facade over existing capabilities, not a second control plane. See the official
[MCP architecture](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/learn/architecture.mdx)
and [authorization requirements](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/authorization.mdx).

## Firmware intelligence and binary analysis

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| Binwalk v3 | Adopt in isolated worker | Identify/extract embedded files/data and entropy regions | Signatures are candidates; extraction inputs are hostile |
| Ghidra headless | Adopt optionally as primary deep analyzer | Scripted architecture, functions, references, decompilation, software graph | Heavy Java runtime; output is analysis, not recovered source truth |
| Ghidra SLEIGH | Evaluate for new architectures | Add instruction/p-code descriptions for unsupported processors | Creating a correct processor model is expert work, not auto-detection |
| radare2 or Rizin | Evaluate one | Lighter scriptable/JSON analysis and cross-check engine | Avoid shipping two overlapping engines without measured benefit |
| EMBA | Optional isolated profile | Linux firmware extraction, SBOM, static/dynamic security analysis | High resource use; Linux/container/VM; never developer mode on untrusted data |
| flashrom | Optional acquisition adapter | Authorized read/verify of supported external flash through known programmer | Read/write safety varies by chip/system; writes use operation gate |
| Avatar2 | Defer to HIL research | Orchestrate emulator, debugger, and physical target memory forwarding | Complex research workflow, not first-release identification |
| Kali metapackages | Avoid as dependency | Research reference only | Integrate reviewed individual tools, not an operating-system tool bundle |

The first useful pipeline is Binwalk -> Ghidra headless -> SVD correlation -> software graph. Firmware
acquisition is a separate controlled operation: vendor image/file import is safest; debug/bootloader
or external-flash reads require target-specific adapters, authorization, backup handling, and read
protection compliance.

Ghidra's headless analyzer supports scripted batch import/analysis, while SLEIGH describes instruction
encodings and p-code semantics. Binwalk v3 identifies and optionally extracts embedded files/data.
EMBA covers broad firmware extraction/security analysis but recommends its default container mode and
warns that developer mode can execute malicious code. Avatar2 explicitly orchestrates emulators and
physical targets, fitting the later hybrid phase. Sources:
[Ghidra headless](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md),
[SLEIGH](https://ghidra.re/ghidra_docs/languages/html/sleigh.html),
[Binwalk v3](https://github.com/ReFirmLabs/binwalk/blob/master/README.md),
[radare2/r2pipe](https://book.rada.re/scripting/r2pipe.html),
[EMBA features](https://github.com/e-m-b-a/emba/wiki/Feature-overview),
[EMBA isolation warning](https://github.com/e-m-b-a/emba/wiki/Installation), and
[Avatar2 architecture](https://github.com/avatartwo/avatar2/blob/main/handbook/0x01_intro.md).

## Packaging and deployment

| Technology | Decision | Product role | Important boundary |
| --- | --- | --- | --- |
| Native Python service + bundled React | Adopt for first release | Reliable access to host hardware | Signed installer and controlled tool bootstrap required |
| Tauri desktop shell | Evaluate after local release | Desktop lifecycle, tray, updater, deep links | Do not duplicate the native bridge or rush packaging |
| Docker Compose | Optional | Observability, catalogs, hosted dependencies | Not the default Windows hardware-access path |
| SQLite | Keep for local | Evidence, history, receipts, definitions | Add migrations, backup, retention, integrity checks |
| PostgreSQL | Hosted only | Multi-user/tenant persistence | Do not burden offline users with it |

## Research spikes required before adoption

1. Parse representative STM32, Nordic, Microchip, and NXP packs into the normalized graph.
2. Parse three Zephyr boards and compare declared topology with live Linux/CircuitPython evidence.
3. Validate OpenOCD, pyOCD, and probe-rs through real CMSIS-DAP/J-Link/ST-Link fixtures.
4. Prove React Flow performance with a 1,000-node evidence/circuit graph and keyboard accessibility.
5. Round-trip a small supported graph through CircuitJS/ngspice and KiCad without claim loss.
6. Simulate one supported firmware target in Renode and link results to the same test-pack schema.
7. Instrument one full inspect/test/flash flow with OpenTelemetry and verify secret redaction.
8. Implement a read-only MCP prototype and run authorization and prompt-injection threat tests.

## Explicit non-decisions

- No graph database until real queries and scale justify it.
- No Kubernetes requirement for local or small-team deployment.
- No arbitrary serial brute forcing, unknown-pin driving, or automated flashing.
- No AI requirement for discovery, test execution, or device control.
- No paid plan design before a stable open local release and user research.
