# Product Task Backlog

Status: initial execution backlog  
Date: 2026-09-24

## How to use this backlog

- Priority: `P0` release blocking, `P1` milestone blocking, `P2` planned, `P3` research/later.
- A task is complete only when its acceptance condition and the applicable gates in
  `QA_GAP_GATES.md` have evidence.
- Dependencies use task IDs. `-` means the task can begin from the current baseline.
- Mark completion with `[x]` and append a test/receipt/report link or path.
- Hardware support without a real fixture remains experimental even if unit tests pass.

## Immediate execution order

Start with `GOV-001`, `QA-001`, `CORE-001`, `UX-001`, `EVD-001`, and `SDK-001`. Those tasks stabilize
the product contract before broad vendor, simulation, or hosted work.

## Governance and baseline

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | GOV-001 | P0 | - | Ratify product vision, architecture, and scope boundaries | Maintainer decision recorded; contradictions resolved across docs |
| [ ] | GOV-002 | P0 | GOV-001 | Choose source and contribution license | License, notices, contributor terms, and dependency policy committed |
| [ ] | GOV-003 | P0 | GOV-002 | Complete dependency and asset license inventory | Every runtime/tool/definition/asset has source, version, license, redistribution decision |
| [ ] | GOV-004 | P1 | GOV-001 | Add governance, code of conduct, support, security, and contribution docs | Public contributor can find ownership, review, disclosure, and support paths |
| [ ] | GOV-005 | P1 | GOV-004 | Add architecture decision record template and index | Material decisions are numbered, reviewable, and linked from architecture |
| [ ] | GOV-006 | P1 | GOV-001 | Define supported, experimental, and planned labels | UI, API, matrix, and docs use the same definitions |
| [ ] | GOV-007 | P1 | GOV-003 | Generate SBOM and third-party notices | CI artifact is reproducible and reviewed for omissions |

## QA, CI, and release evidence

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | QA-001 | P0 | - | Capture current baseline and pre-gap report | Commands, versions, API snapshot, UI flows, fixtures, and gaps are timestamped |
| [ ] | QA-002 | P0 | QA-001 | Create CI matrix for Python, TypeScript, schemas, and browser tests | Required checks run on supported host/tool versions |
| [ ] | QA-003 | P0 | QA-001 | Create fixture-matrix schema and lab report format | Real runs can be compared by device, wiring, firmware, host, and tool version |
| [ ] | QA-004 | P1 | QA-002 | Add adapter/provider/test-pack contract-test harness | Invalid and reference plugins produce deterministic results |
| [ ] | QA-005 | P1 | QA-002 | Add accessibility and responsive browser gates | Keyboard, focus, names, contrast, zoom, and target viewports are automated/manual gated |
| [ ] | QA-006 | P1 | QA-001 | Establish performance budgets from measurements | Budgets and capture commands are recorded, not guessed |
| [ ] | QA-007 | P1 | QA-002 | Add reconnect, contention, cancellation, and fault-injection suite | Port loss, device removal, busy target, timeout, and process crash paths pass |
| [ ] | QA-008 | P1 | QA-002 | Add database migration/backup/corruption tests | Upgrade, backup, restore, and integrity failure behavior pass |
| [ ] | QA-009 | P1 | QA-003 | Automate hardware-lab result ingestion | Receipts update matrix without converting mocks to verified claims |
| [ ] | QA-010 | P0 | all phase tasks | Run separate final code, UX, safety, security, hardware, performance, and gap reviews | Phase report records pass/conditional/fail for every gate |

## Core runtime and data safety

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | CORE-001 | P0 | QA-001 | Version API, event, database, and definition schemas | Compatibility policy and schema fixtures pass |
| [ ] | CORE-002 | P0 | CORE-001 | Add structured application errors and remediation codes | UI/CLI/API show stable codes and actionable messages |
| [ ] | CORE-003 | P0 | CORE-001 | Implement cancellable subprocess/job supervisor | Process trees stop, locks/handles release, and receipts end consistently |
| [ ] | CORE-004 | P0 | CORE-003 | Unify all active work under operation plans and approvals | Legacy tests/probes cannot bypass target-bound policy |
| [ ] | CORE-005 | P0 | CORE-004 | Add idempotency, target generation checks, and exclusive locks | Stale/replayed/cross-target commands are rejected in tests |
| [ ] | CORE-006 | P0 | CORE-001 | Move credentials to OS secret storage abstraction | Database/log/API scans find no stored secrets |
| [ ] | CORE-007 | P1 | CORE-001 | Add retention, export, backup, and delete policies | User can inspect and control local evidence/artifact retention |
| [ ] | CORE-008 | P1 | CORE-001 | Add resumable ordered event stream | Reconnect recovers bounded missed events without duplicates |
| [ ] | CORE-009 | P1 | CORE-008 | Instrument health and diagnostics bundle | Support bundle is bounded, redacted, and useful offline |

## Host inventory and UX

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | UX-001 | P0 | QA-001 | Implement four device-class sections | Circuit, bridge, unresolved, and passive items are separate and explainable |
| [ ] | UX-002 | P0 | UX-001 | Add stable physical-device correlation and history | Reconnect/COM changes preserve unit identity without merging different units |
| [ ] | UX-003 | P0 | UX-002 | Add event-driven attach/remove refresh per OS | UI updates promptly and marks stale state without duplicate rows |
| [ ] | UX-004 | P1 | UX-001 | Add search, filters, sorting, density, and passive collapse | Large inventories remain scan-friendly and keyboard usable |
| [ ] | UX-005 | P0 | CORE-002 | Standardize loading, progress, cancel, success, failure, retry, and notifications | Every action has immediate and terminal feedback |
| [ ] | UX-006 | P1 | UX-005 | Standardize tooltips and unavailable remediation | Every disabled/unfamiliar control explains prerequisites |
| [ ] | UX-007 | P1 | QA-005 | Correct step connector geometry and responsive navigation | Lines connect only outer faces at all required viewports |
| [ ] | UX-008 | P1 | QA-005 | Audit table spacing, wrapping, links, cards, and empty states | No overlap/cramping; service URLs are explicit and reachable |
| [ ] | UX-009 | P1 | CORE-008 | Add collapsible target-labeled event/terminal drawer | Streams show source, state, timestamps, and bounded history |
| [ ] | UX-010 | P0 | all React feature tasks | Retire React parity gaps while preserving HTML validation client | Required workflows pass both clients or documented recovery-only boundary |

## Evidence graph and definitions

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | EVD-001 | P0 | CORE-001 | Define normalized evidence/circuit graph schema | Identity, components, pins, buses, claims, evidence, tests, operations round-trip |
| [ ] | EVD-002 | P0 | EVD-001 | Implement claim lifecycle and contradiction engine | Status, confidence, expiry, resolution, and history tests pass |
| [ ] | EVD-003 | P0 | EVD-001 | Migrate existing device records and profiles | ESP/Feather/Nano/Lichee fixtures retain semantics and history |
| [ ] | EVD-004 | P1 | EVD-001 | Add raw evidence/artifact store with hashes and retention | Claims link to immutable bounded evidence |
| [ ] | DEF-001 | P0 | EVD-001,GOV-003 | Implement definition provider and cache contract | Fetch/parse/version/license/checksum failures are deterministic |
| [ ] | DEF-002 | P0 | DEF-001 | Ingest CMSIS packs and SVD | Representative vendors normalize peripherals/registers with source links |
| [ ] | DEF-003 | P0 | DEF-001 | Ingest Zephyr DTS and bindings | Representative boards normalize topology and semantic properties |
| [ ] | DEF-004 | P1 | DEF-001 | Ingest live Linux device tree and sysfs | Reachable SBC graph shows kernel-visible components and drivers |
| [ ] | DEF-005 | P1 | DEF-001 | Normalize Arduino/PlatformIO/CircuitPython definitions | Existing board data enters one schema without duplicate identities |
| [ ] | DEF-006 | P1 | DEF-001 | Add signed custom definition bundles | User definitions validate, version, import/export, and remain declared |
| [ ] | DEF-007 | P2 | DEF-001 | Implement cached vendor/catalog/document clients | Rate limits, citations, expiry, API-key errors, and offline behavior pass |
| [ ] | DEF-008 | P1 | DEF-002,DEF-003 | Add conservative definition matcher | Weak matches remain candidates; exact matches create expected claims only |

## Adapter SDK and vendor coverage

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | SDK-001 | P0 | CORE-001,EVD-001 | Define adapter manifest and typed lifecycle | Current adapters can implement contract without UI/database dependency |
| [ ] | SDK-002 | P0 | SDK-001,CORE-003 | Add isolated tool runner, budgets, locks, and health | Adapter crash/timeout cannot break inventory or another target |
| [ ] | SDK-003 | P0 | SDK-001,QA-004 | Migrate current adapters | Existing verified behavior and tests pass through SDK |
| [ ] | SDK-004 | P1 | SDK-001,QA-004 | Publish adapter template and contributor guide | Sample adapter passes conformance without core edits |
| [ ] | ADP-001 | P0 | SDK-003 | Harden USB-UART/debug bridge layer separation | Bridge never inherits downstream board claims without target response |
| [ ] | ADP-002 | P0 | ADP-001 | Complete ESP8266/ESP32 family adapters | ROM/read-only identity, flash metadata, pins, radio, tests pass on fixtures |
| [ ] | ADP-003 | P1 | SDK-003 | Complete SAMD/AVR and CircuitPython adapters | Identity/runtime/pins/buses/tests pass across fixture variants |
| [ ] | ADP-004 | P1 | SDK-003 | Complete Nordic adapter | Exact family, pins, BLE, sensors/test-pack exposure pass on fixtures |
| [ ] | ADP-005 | P1 | SDK-003 | Add RP2040/RP2350 and rpiboot adapters | Normal/boot modes, flash identity, pins, and recovery pass |
| [ ] | ADP-006 | P1 | SDK-003 | Add STM32 plus DFU/SWD adapters | Read-only identity and protected programming/recovery pass |
| [ ] | ADP-007 | P1 | SDK-003,DEF-004 | Add Raspberry Pi and generic Linux SBC adapters | OS/device-tree/services/media/bus evidence pass |
| [ ] | ADP-008 | P2 | ADP-007 | Add NVIDIA Jetson adapter | SoC/OS/CUDA/media/camera/health claims pass on real fixture |
| [ ] | ADP-009 | P2 | SDK-003 | Add Hailo PCIe/M.2 adapter | PCIe identity, runtime/firmware, topology, health, basic inference pass |
| [ ] | ADP-010 | P2 | SDK-003 | Add HackRF/SoapySDR adapter | Identity, firmware, bounded receive test pass; transmit remains gated |
| [ ] | ADP-011 | P2 | SDK-003 | Add Beken/LibreTiny adapter | Supported boot/runtime handshake and recovery pass; no CP210x guessing |
| [ ] | ADP-012 | P2 | ADP-007 | Add Rockchip and Allwinner Linux/boot adapters | Supported SoC/board/runtime evidence passes fixture tests |

## Pins, buses, components, and tests

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | PIN-001 | P0 | EVD-001,DEF-005 | Build normalized pin/function/constraint service | Aliases, mux, voltage, direction, reserved/boot/debug state retain provenance |
| [ ] | PIN-002 | P0 | PIN-001 | Build pins and buses UI | Physical and logical views are searchable, responsive, and evidence-labeled |
| [ ] | PIN-003 | P1 | PIN-001 | Add bus/attachment graph for common buses | Controllers and attachments model addresses/chip selects and evidence |
| [ ] | PIN-004 | P1 | PIN-003 | Add stable multi-sample I2C inventory and signatures | Noise is retained; addresses and exact parts are not conflated |
| [ ] | TST-001 | P0 | SDK-001,EVD-001 | Define test-pack schema and runner | Prerequisite/stimulus/measurement/criteria/cleanup/timeout contract passes |
| [ ] | TST-002 | P0 | TST-001,CORE-004 | Generate tests from capabilities and components | UI contains no board-name-specific test branching |
| [ ] | TST-003 | P1 | TST-001 | Add common motion/environment/light/proximity/audio packs | Supported fixture results include live values and tolerances |
| [ ] | TST-004 | P1 | TST-001 | Add camera/display/storage packs | Frames/patterns/read-write checks distinguish detect from verify |
| [ ] | TST-005 | P1 | TST-001 | Add GPIO/PWM/ADC/UART/SPI/CAN packs | Packs require documented firmware or protected fixtures |
| [ ] | TST-006 | P2 | TST-001 | Add accelerator/SDR and performance packs | Results include environment and do not overstate generic health |
| [ ] | TST-007 | P0 | TST-002,UX-005 | Add live measurements, result history, comparison, and export | Users can see what happened, raw evidence, criteria, and repeatability |

## Communications

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | COM-001 | P0 | CORE-001 | Define session/protocol/credential/event model | Direction, endpoints, state, counters, and secret references round-trip |
| [ ] | COM-002 | P0 | COM-001 | Create dedicated React communications step | Controls are target-specific; radio selection leaves device page |
| [ ] | COM-003 | P0 | COM-001 | Implement BLE central scan/GATT sessions | Discover/read/write/notify use scoped approval and live evidence |
| [ ] | COM-004 | P1 | COM-001 | Implement supported BLE peripheral/broadcast sessions | OS/device limitations are explicit and tested |
| [ ] | COM-005 | P0 | COM-001,CORE-006 | Implement Wi-Fi scan/association/AP/state sessions | Secrets stay out of persistence/logs; Wi-Fi-only/both distinctions pass |
| [ ] | COM-006 | P1 | COM-001 | Harden mDNS/SSDP/private-network discovery and service links | Scans are bounded/cancelable; URLs validate and open correctly |
| [ ] | COM-007 | P1 | COM-001 | Add MQTT Paho client and optional Mosquitto fixture | MQTT 5 publish/subscribe/reconnect/TLS test receipts pass |
| [ ] | COM-008 | P2 | COM-001 | Add CoAP client/server tests | Supported Windows/Linux/macOS operations and security options documented |
| [ ] | COM-009 | P1 | COM-001 | Add HTTP/WebSocket/SSH/RTSP/serial session adapters | Each protocol has allowlist, auth, timeout, stream, and cleanup tests |
| [ ] | COM-010 | P2 | COM-001 | Add device-to-device session orchestration | Multi-target locks, routing, traffic, teardown, and receipts pass |

## Protected fixtures and measurement

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | FIX-001 | P0 | PIN-001 | Specify protected fixture electrical and protocol requirements | Voltage/current/isolation/level/connector/emergency-stop design reviewed |
| [ ] | FIX-002 | P1 | FIX-001,SDK-001 | Implement fixture adapter, identity, self-test, and calibration | Stale/failed calibration blocks active work |
| [ ] | FIX-003 | P1 | FIX-002 | Implement wiring profile and preflight | Wrong voltage/pin direction/missing ground cases block stimulus |
| [ ] | FIX-004 | P1 | FIX-002 | Integrate logic capture and sigrok decoders | Captures link to graph pins/buses/tests with tool versions |
| [ ] | FIX-005 | P1 | FIX-003 | Validate I2C/SPI/UART/GPIO/ADC/PWM/CAN reference circuits | Repeatable real-fixture matrix passes with safe cleanup |
| [ ] | FIX-006 | P2 | FIX-002 | Integrate OpenOCD/pyOCD/probe-rs debug fixtures | Read-only identify plus approved write/recovery paths pass |
| [ ] | FIX-007 | P2 | FIX-006 | Evaluate JTAG boundary scan | Supported BSDL/chain fixture proves net tests; unsupported targets stay unavailable |

## Firmware, files, and recovery

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | FW-001 | P0 | CORE-004 | Unify build/edit/backup/flash/reset under operation service | All actions stream, cancel, lock, audit, and enforce target binding |
| [ ] | FW-002 | P0 | FW-001 | Add React file tree, Monaco editor/diff, and conflict handling | Desktop edit flow passes; mobile has intentional read-only fallback |
| [ ] | FW-003 | P1 | FW-001,UX-009 | Add transport-bound xterm terminal | Serial/log/named command sessions cannot become ambient shell |
| [ ] | FW-004 | P1 | FW-001 | Add PlatformIO/Arduino/Zephyr/CMake/CircuitPython build adapters | Toolchains are pinned, observable, cancelable, and artifact-hashed |
| [ ] | FW-005 | P0 | FW-001 | Implement backup-first flash plan and verify/reconnect | Interrupted, wrong-target, layout mismatch, and verify failure paths pass |
| [ ] | FW-006 | P1 | FW-005 | Add SD imaging and supported boot/recovery workflows | Device/media identity, image hash, capacity, verify, and recovery pass |
| [ ] | FW-007 | P0 | FW-005 | Publish and test recovery playbook per write-enabled adapter | Golden fixture recovers from deliberate interruption |
| [ ] | FW-008 | P1 | FW-001 | Add artifact/workspace provenance and source revision | Receipt reconstructs inputs, tools, output, target, and approval |

## Firmware intelligence

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | FINT-001 | P1 | EVD-001,FW-001 | Define firmware artifact, acquisition, region, layer, and software-graph schemas | Hashes, ranges, assumptions, sources, evidence, and analysis status round-trip |
| [ ] | FINT-002 | P1 | FINT-001,SEC-002 | Build hostile-input isolated analysis worker | CPU/RAM/disk/time/network limits, cancellation, cleanup, and escape tests pass |
| [ ] | FINT-003 | P1 | FINT-001 | Add safe vendor/user image import | Immutable original, hash, format, authorization, and duplicate handling pass |
| [ ] | FINT-004 | P2 | FINT-001,FW-005 | Add target-specific authorized acquisition plans | Supported boot/debug/filesystem/flash reads produce immutable receipts and respect protection |
| [ ] | FINT-005 | P1 | FINT-002,FINT-003 | Integrate Binwalk v3 and format-specific carving | Known images produce deterministic regions; bombs/traversal/malformed images fail safely |
| [ ] | FINT-006 | P1 | FINT-005 | Detect architecture, endianness, base/load address, entry points, and layers | Candidates show evidence/confidence and require confirmation when ambiguous |
| [ ] | FINT-007 | P1 | FINT-002,FINT-006 | Integrate Ghidra headless minimal analysis | Functions/strings/references/sections normalize with tool/script versions and timeout |
| [ ] | FINT-008 | P1 | FINT-007,DEF-002 | Correlate constant/register accesses with CMSIS-SVD | Known fixture addresses map correctly; ambiguous aliases remain candidates |
| [ ] | FINT-009 | P2 | FINT-007,DEF-003 | Correlate device paths/drivers/services with device-tree/hardware nodes | Links retain analysis evidence and never verify physical population |
| [ ] | FINT-010 | P2 | FINT-007 | Evaluate radare2 versus Rizin secondary engine | Decision record measures coverage, automation, packaging, license, and cost |
| [ ] | FINT-011 | P3 | FINT-002,FINT-005 | Add optional isolated EMBA Linux profile | Resource-heavy scan is separate, cancelable, offline by default, and normalized |
| [ ] | FINT-012 | P1 | FINT-001,FINT-009 | Build layered firmware/software-graph UI | Users inspect layers, findings, assumptions, hardware links, raw evidence, and gaps |
| [ ] | FINT-013 | P2 | FINT-007 | Add firmware comparison and regression analysis | Two hashes show changed regions/functions/config/packages with reproducible evidence |
| [ ] | FINT-014 | P3 | FINT-007 | Add expert SLEIGH processor-definition workflow | Signed reviewed specs pass reference instruction/decompiler tests before use |

## Circuit Studio, simulation, and EDA

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | STU-001 | P1 | EVD-001,PIN-001 | Finalize versioned circuit graph schema | Board/part/pin/net/power/constraint/model/evidence graph round-trips |
| [ ] | STU-002 | P1 | STU-001 | Build React Flow canvas and revision history | Drag/wire/keyboard/undo/redo/save/reopen pass at performance budget |
| [ ] | STU-003 | P1 | STU-001 | Implement electrical/logical constraint engine | Voltage, contention, address, reserved pin, current, and ground rules pass |
| [ ] | STU-004 | P2 | STU-001,GOV-003 | Build sanitized Fritzing part/SVG importer | Connectors/geometry/license/source validate; malicious SVG tests pass |
| [ ] | STU-005 | P2 | STU-002,STU-003 | Add compatible-pin and part suggestions | Suggestions explain constraints and never auto-wire without user action |
| [ ] | SIM-001 | P1 | STU-001 | Define simulator adapter and result schema | Coverage, conversion diagnostics, stimuli, traces, determinism pass |
| [ ] | SIM-002 | P2 | SIM-001 | Integrate CircuitJS for supported subsets | Unsupported graph items are reported before run |
| [ ] | SIM-003 | P2 | SIM-001 | Integrate ngspice netlist/model execution | Model/convergence/output errors are actionable and reproducible |
| [ ] | SIM-004 | P2 | SIM-001 | Integrate Renode platform/peripheral tests | Supported firmware executes with Robot test evidence and graph mapping |
| [ ] | SIM-005 | P3 | SIM-001 | Spike DigitalJS, SimulIDE, QEMU, and Wokwi interoperability | Decision record states measured benefit, gaps, license, maintenance, fate |
| [ ] | HIL-001 | P2 | FIX-005,SIM-001 | Specify hybrid event/time/ownership protocol | Sequences, clocks, backpressure, disconnect, safe state, traces are tested |
| [ ] | HIL-002 | P2 | HIL-001 | Implement one real-controller/virtual-peripheral bridge | End-to-end deterministic example passes and labels hybrid evidence |
| [ ] | HIL-003 | P3 | HIL-001 | Implement one virtual-controller/real-fixture bridge | Physical protection and disconnect fail-safe pass |
| [ ] | EDA-001 | P2 | STU-001 | Implement KiCad import with loss report | Symbols/pins/nets/BOM/source import and unsupported fields report pass |
| [ ] | EDA-002 | P3 | EDA-001 | Implement KiCad IPC/export workflow | Round trip is version-aware and never silently loses constraints |
| [ ] | EDA-003 | P3 | STU-004 | Implement Fritzing sketch interchange | Licensed supported subset round-trips connectors and wires |

## Visual identification and providers

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | VIS-001 | P2 | EVD-001 | Add top/bottom photo capture, upload, hash, and board association | Images are consented, bounded, sanitized, and traceable |
| [ ] | VIS-002 | P2 | VIS-001 | Add OCR for markings and pin legends | Candidates retain regions, text alternatives, confidence, and raw evidence |
| [ ] | VIS-003 | P2 | VIS-002,DEF-007 | Match visual candidates to catalogs/documents | Results cite sources and remain inferred until confirmed |
| [ ] | VIS-004 | P2 | VIS-003 | Add user confirmation and contradiction workflow | Confirmation becomes declared evidence without overwriting live conflicts |
| [ ] | VIS-005 | P3 | VIS-002,STU-001 | Infer component placement and graph candidates | User reviews every proposed node/edge before graph merge |

## Observability

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | OBS-001 | P1 | CORE-001 | Define structured event/log/metric/trace conventions | IDs correlate host scan through operation/test receipt |
| [ ] | OBS-002 | P1 | OBS-001 | Instrument critical flows with OpenTelemetry | Trace/metric/log tests pass with bounded cardinality |
| [ ] | OBS-003 | P0 | OBS-002,CORE-006 | Implement redaction and telemetry allowlist | Secret/raw payload adversarial tests pass |
| [ ] | OBS-004 | P2 | OBS-002 | Add optional Collector + Prometheus/Grafana profile | Profile starts separately and is not required for local product |
| [ ] | OBS-005 | P3 | OBS-002 | Add optional SigNoz profile | Documented resource cost and diagnostic value justify inclusion |

## Public API, MCP, and IDE

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | API-001 | P0 | CORE-001 | Publish `/api/v1` resource and operation contracts | OpenAPI, errors, pagination, idempotency, scopes, events, examples pass |
| [ ] | API-002 | P1 | API-001 | Generate typed Python/TypeScript clients | Clients pass compatibility suite against supported server versions |
| [ ] | API-003 | P1 | API-001 | Add signed webhooks/subscriptions | Retry, ordering, replay, redaction, and signature verification pass |
| [ ] | PLG-001 | P1 | SDK-004,GOV-003 | Define signed extension packages and trust policy | Install/update/remove/isolation/permission/revocation tests pass |
| [ ] | MCP-000 | P0 | API-001 | Bundle MCP server with local product lifecycle | Explicit enable/disable, health, stdio/loopback default, logs, version, and uninstall pass |
| [ ] | MCP-001 | P1 | MCP-000 | Implement read-only MCP resources | Devices/evidence/definitions/results expose redacted scoped context |
| [ ] | MCP-002 | P1 | MCP-001,CORE-004 | Add safe inspect/test/plan tools | Tools call application services and cannot bypass policy |
| [ ] | MCP-003 | P0 | MCP-002 | Implement MCP authorization and security suite | Audience/scopes/discovery/injection/confused-deputy tests pass |
| [ ] | MCP-004 | P2 | MCP-003 | Add approved write-operation execution | Human target-bound approval remains external and auditable |
| [ ] | IDE-001 | P2 | API-002 | Build VS Code device tree/log/test prototype | Uses public client only; no duplicate hardware logic |
| [ ] | IDE-002 | P2 | IDE-001,FW-004 | Add project association and build/flash planning | Workspace-target links and plans remain explicit and reversible |
| [ ] | MOB-001 | P2 | API-002,QA-005 | Make the responsive client installable as a local/PWA companion | Install/offline shell/updates/responsive status and remote-local connection UX pass |
| [ ] | MOB-002 | P3 | MOB-001,COM-003 | Evaluate native mobile shell for direct BLE and device permissions | Decision record compares platform APIs, security, packaging, maintenance, and browser limits |

## Packaging, security, and launch

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | SEC-001 | P0 | GOV-001 | Maintain product, electrical, plugin, and MCP threat models | Reviewed threats map to controls/tests/owners |
| [ ] | SEC-002 | P0 | CORE-003 | Harden paths, archives, XML/SVG/images, tools, and device output | Adversarial corpus cannot escape, execute, exfiltrate, or poison UI/agents |
| [ ] | SEC-003 | P0 | API-001 | Enforce localhost default and authenticated TLS remote mode | Network tests prove no unintended listener or unauthenticated control |
| [ ] | SEC-004 | P0 | GOV-007 | Add dependency/secret/static/dynamic scans and release provenance | CI gates releases and artifacts verify signatures/provenance |
| [ ] | PKG-001 | P0 | CORE-009,GOV-003 | Build signed local package/installer per supported OS | Clean install/offline launch/update/rollback/uninstall pass |
| [ ] | PKG-002 | P1 | PKG-001 | Add safe toolchain/bootstrap manager | Pinned tools install/update/remove with checksum/license/offline state |
| [ ] | PKG-003 | P1 | PKG-001,QA-008 | Add application/data backup, restore, repair, and migration UI | User can recover without manual database surgery |
| [ ] | DOC-001 | P0 | all release tasks | Publish concise user/admin/contributor/adapter/test-pack docs | Fresh users complete first scan/test; contributor completes sample adapter |
| [ ] | REL-001 | P0 | QA-010,SEC-004,PKG-003,DOC-001 | Run production release candidate gate | Every criterion in QA document passes with evidence |
| [ ] | REL-002 | P0 | REL-001 | Launch open-source release | Tagged signed release, notes, matrix, known gaps, support/security paths live |

## Optional hosted product

| Done | ID | Pri | Depends | Task | Done when |
| --- | --- | --- | --- | --- | --- |
| [ ] | PROD-001 | P3 | REL-002 | Conduct user interviews and paid-problem validation | Evidence identifies who pays, for what, and current alternative |
| [ ] | PROD-002 | P3 | PROD-001 | Model cost, support, pricing, and open-core boundary | Sustainable options include reasons to accept/reject a low-price tier |
| [ ] | CLOUD-001 | P3 | PROD-002 | Design tenant, sync, privacy, retention, deletion, and export model | Threat/privacy review and user-controlled sync contract pass |
| [ ] | CLOUD-002 | P3 | CLOUD-001 | Build encrypted device-history/team workspace pilot | Local core works unchanged when cloud is absent |
| [ ] | CLOUD-003 | P3 | CLOUD-001 | Build remote lab agent and scheduling pilot | Mutual auth, policy, audit, offline recovery, and tenancy tests pass |
| [ ] | AI-001 | P3 | VIS-003,MCP-003 | Add optional AI explanation/document/vision workflows | No core feature requires AI; outputs cite evidence and preserve uncertainty |

## Backlog completion rule

No percentage-complete claim is based on checked boxes alone. Milestone completion is calculated from
passed exit criteria and attached evidence, with unsupported hardware and conditional gates reported
separately.
