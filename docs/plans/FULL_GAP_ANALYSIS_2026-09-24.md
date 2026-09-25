# Full Implementation Gap Analysis

> **Superseded baseline:** This file preserves the pre-implementation audit. Current status and completion
> evidence live in `REQUIREMENT_EXECUTION_LEDGER_2026-09-24.md`; where the two differ, the ledger wins.

Date: 2026-09-24  
Scope: initial requirements, all files under `docs/ideas/`, the four supplied task transcripts,
the current repository, live COM6 hardware, API responses, automated tests, and browser evidence.

## Executive result

The bench is a working local development system, not yet a universal production hardware analyzer.
Its strongest verified path is the attached Seeed Studio XIAO ESP32-S3 Sense running cooperative
diagnostic firmware. That path now covers exact board identity, layered USB/board/component evidence,
fourteen external pins, camera frames and controls, BLE/Wi-Fi state and controls, tests, source and
flash workflows, live device-change events, persistent projects, and a real wireable prototype view.

The remaining work is primarily vendor breadth, protected physical fixtures, definition ingestion,
electrical/firmware simulation, hybrid GPIO control, production security/packaging, and the deferred
agent/MCP system. USB descriptors alone cannot reveal every unexposed chip, passive component, trace,
or connected sensor on an arbitrary board; the product must continue to state evidence limits.

## Requirement trace

| Requirement | State | Current evidence | Completion gate |
| --- | --- | --- | --- |
| Separate circuit targets from passive peripherals | Implemented | Host tables and classifications distinguish controllers, bridges, SDRs, cameras, storage, HID/MIDI, and other USB devices. | Expand OS and fixture matrix. |
| Detect attached host devices and removal | Implemented on Windows | `WM_DEVICECHANGE` USB/COM listener, debounce, canonical state events, and reconciliation fallback. | udev/IOKit and removal-driven operation cancellation. |
| Layer bridge identity and board identity | Implemented for compatible runtime | CP210x remains a UART bridge; authenticated firmware can promote the target to its exact board without rewriting bridge evidence. | Apply the evidence model to every adapter. |
| Exact attached XIAO identity | Verified | Live firmware identifies XIAO ESP32-S3 Sense, ESP32-S3R8, camera, microphone, microSD, flash, PSRAM, Wi-Fi, BLE, and 14 pins. | Add signed/attested adapter protocol for release. |
| Pins, buses, aliases, and cautions | Partial | Exact XIAO pins plus normalized GPIO, ADC, I2C, SPI, UART, power, reset, enable, and boot knowledge. | Ingest CMSIS-SVD, Zephyr/Linux DeviceTree, vendor definitions, mux constraints, and provenance at scale. |
| Camera, BLE, and Wi-Fi UI | Verified for attached fixture | Binary latest-frame-only WebSocket, camera controls, radio states and controls, host/device scans, GATT and traffic checks. | WebRTC is optional; benchmark before adding it. Add more camera codecs and radio adapters. |
| Responsive live UI | Verified current slice | Desktop/mobile Playwright flow passes without page overflow. | Accessibility, long-run soak, reconnect, and multi-device tests. |
| Safe device tests | Partial | Presence, protocol, camera, BLE, Wi-Fi, sensor, network, and recognized-target tests exist. | Versioned test packs, unified approval API, cancellation, durable result schema, and hardware CI. |
| Code, build, backup, and flash | Partial | Allowlisted workspace, target-bound plans, approvals, locks, hashes, timeouts, audit receipts, PlatformIO/Arduino tooling. | Streaming cancellation, recovery packs, broader vendors, and hostile-input sandbox. |
| ORM and private persistence | Implemented baseline | SQLAlchemy 2, Alembic `0001`, WAL/busy timeout, ignored runtime DB files, no host-side wireless password storage. | Encryption policy, retention, export/delete, and multi-user schema before hosted use. |
| Prototype board and component library | Implemented baseline | React Flow, Wokwi Elements, official XIAO visual, 20 parts, 14 exact handles, wiring, validation, save/reopen. | Larger licensed definition/art library and neutral unknown-board editor. |
| Electrical simulation | Not implemented | UI explicitly reports no engine. | Versioned engine contract plus CircuitJS/ngspice translation and unsupported-element reporting. |
| Firmware emulation | Not implemented | UI explicitly reports no engine. | Renode/QEMU adapters, deterministic run control, trace schema, and verified target models. |
| Physical plus virtual HIL | Not implemented | Physical and simulated provenance exists, but virtual values do not drive hardware. | Protected fixture, capability negotiation, ownership/timing protocol, safe disconnect, and one reference circuit. |
| KiCad/Fritzing interoperability | Planned | Architecture and resource decisions exist; no active importer/exporter. | License review, isolated parsers, round-trip fixtures, and fidelity reports. |
| Firmware intelligence | Planned | Intake and architecture exist; no binary-analysis pipeline is exposed. | Isolated extraction, binwalk/Ghidra/radare2 adapters, SVD correlation, provenance, and review UX. |
| Visual/OCR board identification | Planned | Roadmap exists; no model is allowed to promote visual inference to verified identity. | Image intake, OCR/component candidates, document retrieval, confirmation workflow, privacy controls. |
| Built-in MCP and agent system | Deferred by project decision | API boundaries and roadmap exist; agent implementation is being handled separately. | Read-only loopback MCP first, scopes/receipts, prompt governance, then explicitly approved writes. |
| Public production release | Not ready | Local launch and verification work. | License, threat model, auth, signed packages, CI matrix, clean-machine install/update/rollback, support policy. |
| Production web bundle | Builds with warning | Vite production build passes; the main JavaScript asset is about 1.00 MB (273.77 kB gzip). | Route-level lazy loading and chunk budgets before hosted release. |

## Architecture conclusions

1. Keep `Host interface -> physical board -> components -> pins/buses -> runtime` as separate evidence
   layers. A CP2102 is not a NodeMCU, but it can be one verified layer of a NodeMCU inspection.
2. Use board definitions and cooperative firmware for exact topology. Use host descriptors only for
   what they actually expose. Use active probes only through target-specific safe adapters.
3. Use CMSIS-SVD for MCU register/peripheral structure and DeviceTree for board wiring; neither is a
   universal live scanner. Import them into a canonical, provenance-bearing definition model.
4. Keep simulation engines behind adapters. Wokwi Elements and Fritzing parts are visuals; React
   Flow is topology; CircuitJS/ngspice are circuit solvers; Renode/QEMU execute modeled firmware.
5. Keep device control local by default. A hosted UI, public API, or MCP must delegate privileged
   hardware work to an authenticated local agent rather than exposing serial/debug ports directly.

## Next delivery sequence

1. Move wire rules to a backend versioned validator and add current, pull-up, open-drain, address,
   strap-pin, regulator, and level-shifting rules.
2. Add CMSIS-SVD and Zephyr/Linux DeviceTree importers with schema fixtures and provenance tests.
3. Complete stable physical fingerprints, disconnect cancellation, and Linux/macOS lifecycle adapters.
4. Build one protected HIL fixture and prove virtual sensor input driving a real XIAO output safely.
5. Add CircuitJS/ngspice and Renode adapters behind explicit support reports; do not fake unsupported
   components.
6. Add exact definitions for the next fixture set: ESP8266 NodeMCU, Feather M0, Nano 33 BLE Sense,
   Raspberry Pi, Jetson, Hailo, HackRF, and selected RP2040/STM32/Nordic boards.
7. Finish security, licensing, packaging, clean-machine, and hardware-matrix release gates.
8. Land read-only built-in MCP only after the stable public API and operation receipt model are ready.

## Repeated QA gate

For every slice: inspect current evidence, update the gap record, implement one bounded capability,
run unit/type/migration tests, run live fixture tests, run desktop/mobile browser verification, inspect
screenshots and logs, repeat the gap analysis, and only then mark the slice verified.
