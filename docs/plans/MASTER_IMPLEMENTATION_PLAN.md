# Master Implementation Plan

Status: execution plan  
Date: 2026-09-24

## Outcome

Deliver a production-ready, cross-platform local application that inventories host hardware,
separates circuit targets from passive peripherals, builds a provenance-rich model of a selected
device, safely verifies its capabilities, supports controlled firmware work, and exposes the same
capabilities to browser, CLI, public API, VS Code, and MCP clients. Then extend that verified model
into circuit design, simulation, and hardware-in-the-loop workflows.

The phases are dependency ordered. Work inside a phase may run in parallel, but no phase is complete
until its QA gate and updated gap analysis pass.

## Delivery milestones

| Milestone | Included phases | Release meaning |
| --- | --- | --- |
| M0 - Baseline controlled | 0 | Current behavior is reproducible and measured |
| M1 - Trustworthy discovery | 1-3 | Devices are classified, identified, and modeled with provenance |
| M2 - Useful test bench | 4-6 | Common families, communications, sensors, and fixtures are testable |
| M3 - Safe engineering tool | 7-8 | Firmware operations and authorized intelligence are dependable |
| M4 - Virtual workbench | 9-11 | Graph, visual studio, simulation, and EDA exchange are usable |
| M5 - Extensible product | 12-13 | Built-in MCP/API/SDK, packaging, security, and public release pass |
| M6 - Optional service | 14 | Team/cloud and paid features are validated separately from local core |

## Phase 0 - Baseline, governance, and reproducibility

**Goal:** freeze a truthful baseline before expanding the product.

Deliverables:

- Confirm clean-machine setup on Windows, Linux, and macOS with pinned/checksummed tools.
- Record current API schemas, database migrations, UI routes, test fixtures, and hardware evidence.
- Establish semantic versioning, changelog, architecture decisions, contribution rules, code of
  conduct, security policy, support matrix, and definition of done.
- Complete the dependency/license/SBOM inventory and choose the source license before public release.
- Add CI for lint, type, unit, contract, schema, packaging, security, and browser tests without
  pretending mocked tests are hardware verification.
- Establish supported and experimental feature labels.

Exit criteria:

- A new contributor can launch both clients from `QUICKSTART.md` on a clean supported host.
- Existing automated checks pass and current fixture evidence is timestamped in the gap analysis.
- Database upgrade/downgrade policy, backup, and corruption recovery are tested.
- Public repository contains no secrets, private firmware, generated environments, or licensed assets
  without redistribution permission.

## Phase 1 - Host inventory and device-classification experience

**Goal:** make attachment and selection reliable, calm, and understandable.

Deliverables:

- Event-driven device arrival/removal plus manual refresh on all supported operating systems.
- Correlate USB, serial, network, storage, media, PCIe, debug, BLE, and mounted-volume interfaces into
  stable physical devices without relying on COM number.
- Render separate circuit target, transport bridge, unresolved candidate, and passive peripheral
  sections; passive products remain searchable and collapsible.
- Add filters, sorting, accessible tables, evidence tooltips, stale/offline states, load progress,
  notifications, retry paths, and device-history summaries.
- Preserve selection safely through reconnect and reject operations on stale interface generations.

Exit criteria:

- Fixture attach/remove/reconnect tests pass without duplicate or cross-wired identities.
- Every visible item explains classification and interface provenance.
- Desktop and mobile browser flows pass keyboard, focus, contrast, overflow, and loading-state review.
- The passive table never hides inspectable circuit evidence and circuit tables never fill with generic
  HID/storage noise.

## Phase 2 - Evidence graph and hardware-description ingestion

**Goal:** create the vendor-neutral data foundation for deep inspection.

Deliverables:

- Migrate identity, component, pin, bus, claim, evidence, definition, test, and operation entities to
  the normalized graph schema with versioned JSON contracts.
- Add claim expiry, contradiction resolution, source citations, tool versions, hashes, and raw-artifact
  retention policies.
- Implement cached parsers for CMSIS packs/SVD, Zephyr DTS/bindings, Linux device trees, Arduino,
  PlatformIO, CircuitPython, vendor manifests, and signed custom definitions.
- Create matching rules that attach definitions only after a processor/module/board candidate crosses
  a documented threshold; keep expected and verified state separate.
- Expose physical, logical, electrical, firmware, network, and runtime projections.

Exit criteria:

- Golden fixtures round-trip without losing identity layers, pins, functions, buses, constraints,
  provenance, or contradictions.
- Representative Arm SVDs and Zephyr/Linux boards parse deterministically.
- Malformed, hostile, oversized, and license-restricted bundles fail safely.
- Existing ESP8266, Feather, Nano, and Lichee evidence migrates without semantic regression.

## Phase 3 - Adapter SDK and cross-vendor identity

**Goal:** make new hardware support modular and reviewable.

Deliverables:

- Publish adapter manifest, lifecycle, typed result, capability, test, operation, fixture, timeout,
  cancellation, logging, and contract-test interfaces.
- Move existing adapters behind the SDK with no behavior loss.
- Add isolated tool runners, target locks, budgets, structured output, and adapter health reporting.
- Implement read-only identification adapters in fixture-backed order: common bridges and debug probes;
  ESP32/ESP8266; SAMD/AVR; Nordic; RP2040/RP2350; STM32; Raspberry Pi/rpiboot; Linux SBCs; NVIDIA
  Jetson; Hailo PCIe/M.2; HackRF/SDR; Beken/LibreTiny; Rockchip; Allwinner.
- Add contributor adapter template, simulator fixture, conformance suite, and review checklist.

Exit criteria:

- An external contributor can add a simulated adapter without changing core services or UI.
- Every shipped adapter passes contract tests and at least one real-fixture acceptance run.
- Unknown UART, SPI, and GPIO targets receive no arbitrary stimulus.
- Bridge identity never masquerades as the downstream processor or board.

## Phase 4 - Pins, buses, attached components, and test packs

**Goal:** turn identification into useful verification.

Deliverables:

- Pin view with physical positions, aliases, mux functions, voltage, direction, current limits, reserved
  and boot/debug warnings, source, and verification state.
- Bus instances for I2C, SPI, UART, SDIO, CAN, I2S, USB, PCIe, CSI, DSI, ADC, PWM, GPIO, and debug.
- Stable I2C address inventory with candidate identification and part-specific signature checks.
- Versioned test-pack SDK and packs for common IMUs, environmental/light/proximity sensors,
  microphones/audio, displays, cameras, storage, radios, LEDs/buttons, GPIO loopback, and accelerators.
- Test results with live measurements, charts where useful, terminal/events, raw evidence, criteria,
  cleanup, repeatability, and unavailable remediation.

Exit criteria:

- Tests appear from capabilities/evidence, not hardcoded board names in UI.
- Every test declares risk, prerequisites, stimulus, measurements, pass criteria, cleanup, and timeout.
- Disconnect, busy port, bad firmware, noisy bus, partial response, and cancellation paths are tested.
- Expected onboard parts and newly detected attachments remain visibly distinct.

## Phase 5 - Communications workspace

**Goal:** discover and validate how hardware communicates locally and with other devices.

Deliverables:

- Dedicated communications step for BLE, Wi-Fi, Ethernet/USB networking, serial, MQTT, CoAP, HTTP,
  WebSocket, SSH, RTSP, mDNS/DNS-SD, SSDP, and vendor protocols.
- BLE central scan/GATT explorer and supported peripheral/broadcast controls with clear direction.
- Wi-Fi scan, association, hosted AP, IP/services, traffic, and disconnect controls through OS and
  device adapters; secrets remain in OS keychain or device-bound secure flow.
- Clickable validated service URLs, device-to-device session definitions, traffic counters, captures,
  and test receipts.
- Optional loopback-only Mosquitto fixture plus Paho MQTT and aiocoap test clients.

Exit criteria:

- Radio and network controls exist in React with HTML parity where applicable.
- UI never implies BLE on a Wi-Fi-only target or vice versa.
- Network discovery is private-subnet bounded, rate-limited, cancelable, and consented.
- Credentials do not appear in API responses, database rows, logs, telemetry, screenshots, or exports.

## Phase 6 - Protected fixtures and hardware-in-the-loop foundations

**Goal:** inspect and test attached circuits that target firmware cannot expose.

Deliverables:

- Reference protected fixture for target voltage, current limiting, level shifting, isolation, and
  I2C/SPI/UART/GPIO/ADC/PWM/CAN capture or stimulus.
- Fixture identity, self-test, calibration, wiring profile, voltage check, and emergency stop.
- Logic-analyzer capture and sigrok protocol decoding linked to pins, buses, and tests.
- Optional SWD/JTAG/CMSIS-DAP/J-Link/ST-Link workflows and boundary scan where supported.
- Hardware-in-the-loop event envelope specifying virtual time, wall time, sequence, source, target,
  backpressure, and trace correlation.

Exit criteria:

- Active pin work cannot start without a compatible fixture, wiring profile, and voltage validation.
- Deliberate miswire/overvoltage simulation blocks operations before stimulus.
- Fixture calibration and self-test receipts are current and traceable.
- I2C/SPI/UART/GPIO examples pass repeatably on real reference circuits.

## Phase 7 - Firmware, files, terminal, flashing, and recovery

**Goal:** make supported code and programming workflows dependable enough for daily engineering use.

Deliverables:

- React file tree, Monaco editor/diff, diagnostics, target configuration, serial/log terminal, search,
  format, and source-control awareness.
- Build adapters for PlatformIO, Arduino CLI, Zephyr/west, CMake/vendor SDKs, CircuitPython, and Linux
  targets where supported.
- Unified operation flow for build, backup, edit, flash, SD image, verify, reset, reconnect, restore,
  and recovery with streamed progress and cancellation.
- Artifact hashes, source revision, toolchain versions, target fingerprint, partition/layout checks,
  protected regions, and immutable receipts.
- Recovery playbooks and fixtures for every write-capable shipped adapter.

Exit criteria:

- No build or inspection path can flash as a side effect.
- Interrupted flash and application restart recover to a known state or actionable recovery screen.
- Golden-image backup/restore tests pass for each write-enabled family.
- Arbitrary host shell access remains unavailable through browser, API, or MCP.

## Phase 8 - Firmware intelligence and software graph

**Goal:** map authorized firmware into understandable software layers and correlate code behavior with
the verified hardware model.

Deliverables:

- Import vendor/user firmware files and add target-specific authorized acquisition plans for supported
  bootloaders, debug probes, filesystems, update packages, and external flash programmers.
- Hash every source image and preserve acquisition method, target, ranges, protection state, tool,
  operator authorization, and immutable read receipt.
- Carve containers, partitions, bootloaders, kernels/RTOS images, filesystems, device trees, libraries,
  applications, configuration, and unknown regions with Binwalk plus format-specific parsers.
- Detect architecture, endianness, load/base address candidates, entry points, symbols, strings,
  functions, call/reference edges, packages, services, device paths, and security properties.
- Run Ghidra headless in an isolated bounded worker and normalize its output into a software graph;
  evaluate radare2 or Rizin as a lighter secondary engine rather than shipping redundant defaults.
- Correlate constant/register accesses against CMSIS-SVD and code/device paths against device-tree and
  hardware graph nodes, retaining ambiguity and source analysis confidence.
- Offer optional isolated EMBA analysis for Linux firmware and defer Avatar2/SLEIGH authoring to
  explicit expert/research workflows.
- Add a layered firmware UI for boot ROM reference, bootloaders, HAL/BSP/drivers, runtime,
  middleware, applications, configuration/data, evidence, and hardware links.

Exit criteria:

- A known MCU image and a known Linux firmware package produce repeatable software graphs with hashes,
  tool versions, time/resource limits, and explicit unknown regions.
- SVD correlation maps known fixture register accesses without claiming unused/populated hardware.
- Malicious archives, filesystems, binaries, analyzer scripts, and tool output remain sandboxed.
- Read protection, encryption, secure boot, licensing, and authorization boundaries are visible and no
  bypass workflow is supplied.
- Static-analysis findings are labeled analysis/inference and cannot become physical test passes.

## Phase 9 - Circuit graph and interactive studio

**Goal:** turn the verified device model into a rapid-prototyping workspace.

Deliverables:

- Versioned circuit graph schema for boards, components, pins, nets, buses, power domains, constraints,
  evidence, visuals, code, tests, and simulator models.
- React Flow canvas with board/pin layouts, searchable part library, drag/drop, wire creation, zoom,
  keyboard operations, undo/redo, save/revisions, and conflict display.
- Import Fritzing definitions/SVGs only after license, connector, geometry, and sanitization checks.
- Compatible-pin suggestions based on voltage, direction, bus, address, reserved pins, and current.
- Explicit real, simulated, and hybrid modes plus model coverage and evidence overlays.

Exit criteria:

- A Feather/ESP-class board and sensor can be wired, validated, saved, reopened, and exported without
  losing pin or source semantics.
- Invalid voltage, output contention, address collision, reserved pin, and missing ground are blocked
  or prominently warned.
- A 1,000-node graph meets interaction/performance and accessibility budgets.
- Simulation results never appear as real-hardware verification.

## Phase 10 - Simulation engines and digital twins

**Goal:** execute useful subsets of the circuit graph before physical wiring.

Deliverables:

- Simulator adapter contract with model coverage, conversion diagnostics, input stimuli, outputs,
  traces, determinism controls, and versioned result evidence.
- CircuitJS integration for supported browser circuits and ngspice for supported analog netlists.
- Renode platform/peripheral generation or adapters for supported MCU/SoC firmware tests.
- Time-boxed DigitalJS, SimulIDE, QEMU, and Wokwi interoperability spikes based on concrete gaps.
- Hybrid bridges for selected real-controller/virtual-peripheral and virtual-controller/real-fixture
  cases using the Phase 6 event envelope.

Exit criteria:

- A supported graph runs reproducibly in each adopted engine with explicit unsupported elements.
- Real, simulated, and hybrid test receipts cannot be confused in storage, UI, API, or export.
- Deterministic test replays match recorded inputs within documented tolerances.
- Hybrid disconnect and simulator failure leave physical pins in a safe state.

## Phase 11 - EDA, visual identification, and documentation enrichment

**Goal:** connect the bench to engineering source material and unsupported custom hardware.

Deliverables:

- KiCad import/export through supported files and IPC API for symbols, footprints, schematics,
  connectivity, BOMs, models, and annotations.
- Fritzing sketch/part import/export where licenses and fidelity allow.
- Photo capture/upload, top/bottom association, OCR of markings/pin labels, component candidates,
  placement, image hashing, citations, and user confirmation.
- Datasheet/document provider cache with source links, version, extracted facts, and licensing.
- Definition authoring workflow for custom boards, including validation and signed bundle export.

Exit criteria:

- Round trips report every unsupported or lossy field before export.
- Visual candidates remain inferred until user confirmation or live evidence.
- Malicious SVG, archive, document, and image inputs pass sandbox/security tests.
- A documented custom board can be imported, inspected, tested through a fixture, and shared as a
  versioned definition bundle.

## Phase 12 - Public API, plugin SDK, built-in MCP, and IDE integration

**Goal:** make the system safely extensible by software and agents.

Deliverables:

- Stable `/api/v1`, event streams, webhooks, generated clients, examples, scopes, idempotency,
  pagination, deprecation policy, and compatibility tests.
- Signed adapter, definition, provider, test-pack, and simulator package formats with isolated workers.
- Bundle a separately enabled, loopback/stdio, read-only-by-default MCP server with the local product.
- Expose read-only MCP resources first, then safe tests and operation planning; destructive execution requires
  the same target-bound approval as the UI.
- MCP authorization, permission-aware discovery, audit, rate limits, prompt-injection defenses, and
  redacted outputs.
- VS Code extension using the public API for device tree, logs, tests, firmware project association,
  build/flash plans, and receipts.
- Installable responsive/PWA companion using the public API; evaluate a native mobile shell only for
  capabilities such as direct phone BLE that the supported browsers cannot expose consistently.

Exit criteria:

- No integration can bypass policy by using an alternate surface.
- API and MCP contract suites pass against current and previous supported client versions.
- Security review covers confused-deputy, token audience, local-server install, plugin supply chain,
  prompt injection, and malicious device output.
- A third party can build a read-only integration from public docs alone.

## Phase 13 - Production hardening and open-source launch

**Goal:** release a supportable system others can install and contribute to.

Deliverables:

- Signed installers/packages for supported operating systems, safe updates, rollback, diagnostics
  export, crash recovery, uninstall, and data backup/restore.
- Full threat model, electrical safety review, SBOM, provenance, vulnerability handling, release keys,
  secret scanning, dependency policy, and external security review.
- Performance, long-run reconnect, concurrency, disk-retention, network-loss, corruption, and upgrade
  testing against a published hardware matrix.
- Contributor docs, adapter tutorials, definition/test-pack authoring, issue templates, roadmap,
  governance, maintainer/reviewer rules, and release process.
- Production documentation and sample projects no longer than necessary for task completion.

Exit criteria:

- All release gates in `QA_GAP_GATES.md` pass with attached evidence.
- Critical/high security findings and data-loss bugs are closed.
- Hardware-matrix claims link to recent real-fixture results.
- Fresh-machine install, first scan, first inspection, first test, update, rollback, and uninstall pass.
- Public release contains no hidden dependency on AI, paid APIs, Docker, or private files.

## Phase 14 - Optional hosted product and commercialization

**Goal:** add paid value without weakening or withholding the local core.

Candidate services:

- Encrypted device-history sync and team workspaces.
- Remote lab agents, reservations, fixture scheduling, and shared result review.
- Managed definition/provider mirrors and signed test-pack distribution.
- Collaboration, organization policy, audit retention, and support.
- Optional AI explanation, document matching, visual assistance, and agent workflows.

Gates before implementation:

- Interview active users and identify a repeated paid problem.
- Validate willingness to pay and hosting/support cost; do not assume a five-dollar tier is viable.
- Define privacy, tenancy, deletion, export, regional, billing, abuse, and support requirements.
- Keep device control local by default and make cloud synchronization explicit and reversible.

## Cross-phase rules

- Update `GAP_ANALYSIS.md` before and after every phase gate.
- Run implementation review, UX review, safety/security review, automated tests, real-fixture tests,
  browser verification, performance checks, and documentation review as separate activities.
- A mocked test proves software behavior, not electrical or radio behavior.
- Unsupported is an acceptable result; fabricated certainty is not.
- New tools enter through the technology decision record and license review.
- New write operations require backup, recovery, target binding, approval, cancellation, and audit.
- New UI surfaces must work at desktop and narrow mobile widths without overlapping controls.
