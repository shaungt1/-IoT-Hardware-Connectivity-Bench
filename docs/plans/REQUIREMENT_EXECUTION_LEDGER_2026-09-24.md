# Requirement Execution Ledger

Date: 2026-09-24
Latest verification: 2026-09-25

This is the active, evidence-based completion ledger for the entire product request. It combines the
original conversation, every supplied transcript, every file under `docs/ideas/`, the current source,
live attached hardware, and the repeated-review rule in `docs/ideas/getting_lost.md`. A row is complete
only after implementation, automated checks, live or fixture evidence where applicable, and a second
gap review. A UI label, plan, mocked response, or green health endpoint is not completion evidence.

## Product Contract

1. Discover every interface visible to the host and separate development circuits/controllers from
   ordinary peripherals, passive USB identities, storage, audio/MIDI, cameras, radios, and services.
2. Preserve distinct evidence layers: host interface, USB/serial bridge, target silicon, board model,
   onboard components, exposed pins/buses, runtime/firmware, and physically attached peripherals.
3. Never identify a CP2102/CH340/FTDI bridge as the complete board. Probe the target through a safe,
   compatible adapter and otherwise keep the board unresolved with explicit candidates.
4. Inspect any supported MCU, Linux SBC, NPU/accelerator, SDR, or custom circuit through extensible
   adapters and definition providers rather than one-off UI conditionals.
5. Map every externally exposed pin and its aliases, mux functions, direction, voltage, restrictions,
   buses, reserved uses, provenance, confidence, and live ownership when evidence supports it.
6. Discover attached sensors/components through enumerable buses and cooperative runtimes; represent
   non-enumerable GPIO/SPI/UART/passive wiring as unknown until a definition, instrument, fixture,
   firmware report, debug probe, or user-confirmed mapping supplies evidence.
7. Offer safe, target-specific probes and tests. Never brute-force unknown pins by driving them.
8. Stream camera/radio/telemetry state with low latency, measurable transport statistics, current
   device-state events, controls hidden behind intentional tools, and clean disconnect/reconnect.
9. Provide firmware/source browsing, editing, planning, backup, build, flash, recovery, binary
   intelligence, and audit receipts subject to target capability and explicit approval.
10. Provide a full-screen digital prototyping bench whose physical board comes from inspection, whose
    parts look real, whose every physical terminal is a conspicuous functional connection point, and
    whose wires are canonical electrical objects rather than decorative lines.
11. Support virtual simulation, physical binding, and hybrid circuits through the same graph. A UI
    input may affect real hardware only through a negotiated, protected adapter capability.
12. Expose stable local/public APIs and a built-in MCP server for inspection, tracing, planning,
    validation, testing, approved mutations, and event subscriptions without bypassing safety gates.
13. Keep runtime databases, credentials, network secrets, device secrets, captures, and user evidence
    out of source control. Use versioned ORM migrations and local-first security boundaries.
14. Ship a professional React experience, keep the standalone HTML implementation available but
    inactive, provide short launch documentation, and verify desktop/mobile/accessibility/performance.

## Verified Implementation Snapshot

The following slices passed their implementation and repeat-review gates through 2026-09-25:

- Backend: 123 tests pass after the latest-frame camera correction, fast presence reconciliation,
  persistent user-declared pin attachments, lifecycle cancellation, evidence-policy,
  secure SSH, physical-control, firmware-intelligence, ngspice, Renode guest execution, and local OCR additions.
  Dependency integrity passes `pip check`, the API audit has no known vulnerabilities, and Alembic reports migration `0003` at head.
- Live target camera/radios: the bridge now sends only the newest completed JPEG over its binary
  WebSocket and the browser decodes directly into a stable canvas, preventing queued-history replay.
  The last pre-change Chrome baseline delivered 17.5 source FPS and 14.8 browser-painted FPS at 4 ms
  host-receive-to-paint latency and 1,802 kbps. A new post-change camera run is blocked because the ESP
  fixture is currently disconnected. Camera controls, BLE, Wi-Fi, scans, and mobile layout passed previously; a separate
  1,800-second multi-client run delivered 19,161 source frames without passive-client backpressure. A
  second 300-second resource/radio stability run advanced 3,170 source frames while RSS rose only
  106,496 bytes with a 229,376-byte span and the reported radio state remained stable.
- Prototype: 51 packaged parts were audited (all 50 installed Wokwi elements plus the exact XIAO), with exact terminal parity for all rendered parts,
  exact 14-pad XIAO Sense mapping, real wire creation, signal propagation, persistence, and mobile layout.
- Evidence: normalized schema `1.0` graph is emitted with status and provenance on nodes and edges. The
  live HackRF One inspection produced 94 nodes, 93 edges, and all 86 documented expansion pins. The
  selected XIAO inspection now also emits a six-phase progressive discovery report and 13-area coverage
  report; its latest graph contains 33 nodes and 52 edges, with only unobserved attached peripherals unresolved.
- Definition ingestion: CMSIS-SVD, preprocessed Zephyr DeviceTree, KiCad `.kicad_sch`, and unpacked
  Fritzing `.fzp` importers have structured parsers, size bounds, provenance, limitations, and fixtures.
- Adapter SDK: CircuitPython, Espressif ROM, HackRF, CMSIS-DAP/ST-Link/J-Link/Picoprobe, USB
  bootloader/DFU/UF2, and opt-in Firmata handshake manifests are installed with explicit safety modes.
- Test/history/MCP: deterministic test-pack schema `1.0`, unavailable-test rejection, durable redacted
  inspection/test history, retention/export/delete, confirmed visual evidence without image storage, Alembic migration
  `0003`, a ten-path safe probe matrix, passive fixture discovery, and 26 MCP tools are implemented.
- Phase One interaction: native Windows device events plus two-second presence reconciliation invalidate
  stale selections; a red disconnected state locks live actions; unsupported radios remain visible but
  disabled; pin-level user observations persist as declared evidence; and the diagnostic drawer runs only
  advertised passive/read-only profiles or allowlisted Linux-board commands.
- Firmware intelligence: bounded non-executing ELF, UF2, Intel HEX, Espressif-image, and raw-binary
  analysis reports SHA-256, entropy, structure, strings, URLs, architecture evidence, and optional-engine status.
- Simulation/emulation: checksummed local ngspice and Renode runtimes are installed under ignored `.tools`;
  a graph-derived 3.3 V/220-ohm SPICE fixture solved at 3.3 V, and Renode loaded the Nano 33 BLE model,
  ran an architecture-checked ARM ELF for 50 ms, and read its `0xC0DEC0DE` RAM proof marker without changing physical hardware.
- Visual intelligence: a bounded local RapidOCR/ONNX pipeline normalizes JPEG/PNG/WebP input, rejects oversized or
  multi-frame images, returns marking candidates and boxes, and persists only explicitly confirmed text/hash evidence.
- Release evidence: the production React build passes with a 397,078-byte initial entry after lazy-loading Prototype
  and Monaco; API, isolated-tool, and React CycloneDX SBOMs contain 80, 71, and 68 components respectively,
  and the 315-component metadata inventory has no unresolved license identifiers.
- Local launch parity: PowerShell and Git Bash now require an explicit `1` (React), `2` (HTML), or
  `3` (both) choice. Every client mode includes the hardware API and WebSocket backend, no-argument
  execution waits at an interactive menu, there is no separate API startup mode, and shared
  `status`/`stop` commands cover ports 5173, 5174, and 8765.

## Active Gap Matrix

| Area | Current evidence | Gap to close | Completion evidence |
| --- | --- | --- | --- |
| Windows host inventory | Native `WM_DEVICECHANGE`, COM/USB/network/service inventory, circuit/peripheral grouping; cached PnP metadata preserves fresh libusb presence; fast serial/USB presence filtering runs on a two-second fallback and after native events | latest clean-process forced fill measured about 2.6 seconds because native PnP/network/Arduino providers each take roughly 2.3-3.1 seconds and run concurrently; warm forced refreshes measured 52-73 ms; physical attach/remove soak remains | p95 cached refresh under 250 ms passes; cold forced under 2 s and physical attach/remove browser soak remain |
| Cross-platform lifecycle | Windows native events plus two-second portable serial/USB reconciliation; disconnect invalidates inspection, locks live actions, displays a red stale-evidence state, and cancels pending/running operations | native Linux udev and macOS IOKit can further reduce portable polling latency | filter/event/cancellation tests pass; physical unplug/replug and native non-Windows event fixtures remain |
| Evidence model | Bridge/board/component/pin/runtime claims separated; normalized evidence graph schema `1.0`; calibrated source classes and promotion rules | broader live fixture corpus | promotion-policy and graph contract tests pass; live 94-node HackRF trace and UI trace pass |
| Exact XIAO fixture | Authenticated firmware reports XIAO ESP32-S3 Sense, ESP32-S3R8, 14 pads and onboard devices; the host accepts the attached legacy 0.5 protocol while source 0.6 emits neutral `IOTB` and has not been flashed | Signed protocol/firmware attestation beyond the current authenticated framing | 1,800-second multi-client soak, reconnect, 19,161 source frames, and live browser latency pass |
| ESP8266 NodeMCU | Espressif ROM adapter can distinguish an ESP8266 behind a bridge | Board variant still requires flash/firmware/definition evidence; CP2102 alone cannot prove NodeMCU | live CP2102 fixture probe plus explicit unresolved/candidate behavior |
| Adapter SDK breadth | CircuitPython, Espressif ROM, HackRF, debug-probe, bootloader, Firmata, and fingerprint-pinned Linux SSH inspection with Raspberry Pi, Jetson/Tegra, Hailo host, Lichee/Sipeed, Orange Pi, Radxa, and BeagleBoard family facts | Nordic/STM32/RP2040 family-specific debug/boot packs and broader live target corpus | secure SSH and Jetson/Raspberry Pi/Hailo classification fixtures pass; remaining family and live-target fixtures required |
| Definition ingestion | CMSIS-SVD, Zephyr DeviceTree, KiCad schematic, Fritzing part and safe `.fzpz` bundle assets, Arduino CLI and local profiles | KiCad symbol/footprint libraries, CMSIS packs, vendor-scale indexes | structured fixtures pass, including sanitized embedded SVG and ZIP traversal rejection; catalog/license fidelity reports remain |
| Pins and buses | XIAO exact map; HackRF 86-pin map; generic pin knowledge; CircuitPython I2C scan; ten-path runtime/bus/GPIO/debug/instrument coverage matrix; per-pin user evidence form | Mux constraints, current limits, pull-ups, bus membership, address conflicts, attached-device identities | matrix and declared-evidence contract tests pass; live HackRF browser rendered 86 pins and the attachment form; live I2C reference circuit remains |
| Attached components | Cooperative firmware, enumerable I2C, negotiated GPIO/ADC/PWM/SPI/UART paths, SWD/JTAG routing, external logic/analog instrument requirements, and persistent user-declared pin attachments are explicit | SPI/UART/GPIO/passive topology cannot be universally enumerated; add concrete guided instrument adapters and fixtures | declared attachments remain `declared` with provenance and exact pin graph edges; physical reference fixtures remain |
| Camera | Binary latest-frame WebSocket skips superseded frames; browser uses stable canvas decoding; hidden control drawer, source/browser FPS, receive-to-paint latency, throughput and skip metrics; earlier 30-minute multi-client and 5-minute resource-stability soaks passed | Post-change live latency/soak rerun, sensor-to-host latency measurement, additional codecs and non-XIAO adapters | unit tests prove newest-frame selection; last pre-change Chrome baseline was 17.5 source, 14.8 painted FPS, 4 ms receive-to-paint, 1,802 kbps; current ESP fixture is disconnected |
| BLE/Wi-Fi | Dedicated Connections stage with device-side broadcast/connect and computer-side nearby scans; capability-absent radios are visible, muted, and disabled | Long-run radio reconnect and negative credential/error fixtures | prior compatible-target controls/scans pass; live HackRF negative-capability browser test passes |
| Async UI | Device-state WebSocket, fast presence reconciliation, request revision guards, selected workspace and bounded non-secret identifier persistence, fresh inspection recovery, and prominent disconnected evidence state are implemented | Add deterministic rapid-selection and physical reconnect browser stress beyond the passing reload flow | selected-device reload returned to Tests with fresh inspection; stale responses are guarded; disconnect filter tests pass |
| Tests | Versioned deterministic target test packs, unavailable-test rejection, protected operations, durable redacted results, browser export/reload persistence, and a diagnostic drawer limited to advertised passive/read-only profiles | Richer signal/instrument packs and physical-fixture cancellation soak | schema/hash tests plus live HackRF presence profile and target test/history receipts |
| Firmware/files | Workspace, hashes, plan/approve/execute/cancel, live bounded process output, child-process-tree termination, isolated PlatformIO/Arduino tools, lazy Monaco, and a successful XIAO production compile | Recovery packs and backup/restore physical fixtures | 55,724 B RAM / 1,001,541 B flash compile; 1,441 ms browser editor open; nothing flashed |
| Firmware intelligence | Bounded static parser handles ELF/UF2/Intel HEX/Espressif/raw, checksums, entropy, strings, URLs, architecture evidence, and optional-engine status without executing bytes | Isolated Binwalk/Ghidra/Rizin/EMBA workers and SVD correlation | seven parser/API fixtures pass; upload explicitly reports no host execution; external-engine sandbox remains |
| Tools and sources | Registry reports availability, paths, documentation and bounded allowlisted diagnostics; passive fixture inventory separates installed debug/signal tools, connected fixtures, and unconfirmed target wiring | add concrete sigrok capture adapters after a supported analyzer is installed and physically connected | live scan found pyOCD/OpenOCD ready, zero debug probes, sigrok unavailable, zero logic analyzers, and no target access or signal drive |
| Persistence/privacy | SQLAlchemy 2, Alembic through `0003`, ignored SQLite/WAL, retroactive redaction, compacted history, retention/export/delete, normalized visual evidence without photo bytes | Encryption decision and hosted multi-user boundary | migration/history/OCR privacy tests pass; DB compacted from about 86 MB to 4.5 MB; 219 tracked/non-ignored paths pass the source privacy gate |
| Prototype visuals | Complete installed 50-part Wokwi visual set, exact XIAO photo, full-screen canvas, terminal overlays and responsive drawers | Licensed external/manufacturer catalog scale beyond installed package | all 51 catalog entries and every package terminal, XIAO visual, desktop/mobile screenshots pass |
| Prototype graph | Revision conflict control, backend net validator, direction/voltage/contention checks, persistence | Canonical named multi-wire nets/buses plus undo/redo | revision, validation, persistence, physical terminal and wiring browser tests pass |
| Prototype behavior | Virtual signal propagation plus graph-derived ngspice operating points; negotiated control profile and approved GPIO/ADC operation contract | richer sensor models, instruments, and a flashed compatible physical-control runtime | simulated SPICE reference passes; protected physical execution is implemented but current device firmware is not silently flashed |
| Electrical simulation | Local ngspice 46 adapter compiles canonical nets, positive rails, resistors, LEDs, potentiometers, and switches; unsupported models are reported | transient/AC models, richer parts, CircuitJS interactive handoff | installed engine and deterministic 3.3 V/220-ohm reference solve pass |
| Firmware emulation | Renode 1.17.0 portable installed; installed board catalog, conservative identity matching, allowlisted platform verification, architecture-checked ELF loading, bounded execution, trace, proof readback, and temporary-file deletion are exposed | QEMU/AVR8js/RP2040 alternatives and richer UART/register trace capture | Nano 33 BLE ran a Cortex-M ELF for 50 ms and matched a `0xC0DEC0DE` emulated-RAM proof marker; no physical hardware changed |
| EDA/library breadth | 20 local entries plus Wokwi exact terminal introspection, KiCad schematic, Fritzing part, and bounded `.fzpz` visual bundle import | Licensed catalog-scale ingestion/search, KiCad/LibrePCB libraries, custom composer | terminal and importer fixtures pass with sanitized embedded SVG; license catalog remains |
| Visual identification | Local RapidOCR/ONNX image intake, safe normalization, OCR boxes, role-aware marking candidates, preview/review UI, explicit confirmation, and inspection/evidence-graph promotion are implemented | datasheet/document resolver, multi-angle correlation, segmentation and benchmark photo corpus | synthetic ESP32-S3/CP2102 browser and API fixtures pass; image bytes are not persisted |
| MCP | Built-in loopback MCP has 26 read/test/plan/simulation/emulation/OCR/diagnostic/probe/instrument/contract tools, two evidence-first prompts, and hardware/evidence/event/capability resources; manifest denies credentials, arbitrary commands, approvals, and physical execution | push subscription transport beyond the pollable event resource | stdio verification, prompts, resources, API 1.0 contract, and permission manifest pass; mutation remains plan-only |
| Agent readiness | Evidence graph, test pack, prototype graph, API and MCP contracts are provider-neutral; machine-readable API/schema compatibility policy is active; AI remains on its separate branch | Prompt-folder integration when the separate AI branch is ready | API/MCP contract suite passes without merging the AI branch |
| Production/open source | Local dev and prior production builds work; Windows CI gates tests, dependency audits, production build, 500 KB startup budget, deterministic install, all-source privacy, three CycloneDX SBOMs, and license metadata inventory | source-license/maintainer decision, signed release/update/rollback, hosted auth/tenant isolation, and a real clean-run CI result | 123 tests, zero API/React advisories from the prior audit, isolated PlatformIO exceptions documented, prior 397,078-byte entry, zero unresolved license identifiers, and 219-path privacy gate pass locally |

## Execution Order

1. Fix the interactive foundation: cached host inventory, stable selected state, eight workflow stages,
   dedicated Connections view, camera metrics/control drawer, and firmware loading/open latency.
2. Finish the board/component evidence graph and import CMSIS-SVD plus DeviceTree as the first neutral
   definition sources; expose provenance in the UI.
3. Expand adapter contracts and reference fixtures: ESP8266 bridge/ROM, Firmata, CircuitPython,
   CMSIS-DAP/OpenOCD, Linux SBC, HackRF, Jetson/Hailo/Raspberry Pi discovery agents.
4. Add safe bus discovery and a protected hardware-binding protocol, then prove one hybrid circuit
   end to end before expanding physical control.
5. Add simulation adapters, firmware intelligence, EDA importers, image/OCR intake, and visual catalog
   scale with deterministic support reports.
6. Implement built-in MCP over the stable APIs, then complete security, packaging, CI, documentation,
   clean-machine installation and release gates.
7. Complete the full-screen prototype last, consuming verified board, pin, control, test, firmware,
   simulation, and catalog contracts; verify every terminal and one approved hybrid circuit end to end.

## Per-Slice Gate

For each row: capture baseline evidence, implement, run focused unit/type tests, exercise live hardware
when required, run desktop/mobile browser verification, inspect logs/screenshots/network timings, repeat
the gap review, and update this ledger with the exact evidence. Never convert an inferred or expected
claim into a verified claim merely because the UI can draw it.

## Verification Evidence

| Gate | Result |
| --- | --- |
| Backend regression | `123 passed` after latest-frame transport, fast hot-plug filtering, user-declared pin evidence, progressive discovery, graph enrichment, and adapter-failure isolation |
| Python environment | `pip check`: no broken requirements; runtime `pip-audit`: no known vulnerabilities |
| Database migration | Alembic `0003 (head)` |
| React type safety | `npm run check` passed |
| Phase One browser flow | Live HackRF inspection passed: unavailable camera/BLE/Wi-Fi states, disabled radio controls, 86 mapped pins, declared-evidence form, safe diagnostic profile, and no browser errors |
| Firmware/workspace browser flow | Local board-photo OCR, SVD evidence, safe probe coverage, adapter registry, non-executing firmware inspection, browser-driven Renode ELF execution, lazy Monaco editor, selected-device reload recovery, durable test export, corrected workflow order, and mobile layout passed; measured source open was 1,441 ms |
| Prototype browser flow | all 51 catalog entries, every package terminal, exact XIAO map, real wiring, persistence, signal behavior, and mobile layout passed |
| Live browser flow | last pre-change baseline: 17.5 source FPS, 14.8 browser FPS, 4 ms host-receive-to-paint, 1,802 kbps and 9 skipped frames; post-change latest-frame/canvas rerun is blocked because the ESP fixture is disconnected |
| Camera soak | 1,800 seconds; source advanced 19,161 frames; clients received 17,489 and 11,630 frames across reconnect; passive client did not stall delivery; 1,782 health samples passed |
| Resource/radio soak | 300 seconds; source advanced 3,170 frames; clients received 2,901 and 1,909 frames across reconnect; passive client did not stall delivery; 287 health samples passed; RSS rise 106,496 B and span 229,376 B; thread and BLE/Wi-Fi state budgets passed |
| MCP stdio | 26 tools, two safety prompts, API contract, and hardware/evidence/events/capabilities resources passed through a real stdio client |
| Probe matrix | Live API returned deep probe, I2C, GPIO, ADC, PWM, SPI, UART, SWD/JTAG, logic capture and analog measurement routes with unknown-pin driving and automatic brute force both disabled |
| Live hardware API | 13 selectable interfaces plus 17 raw USB identities; latest cold refresh about 2.6 seconds then 52-73 ms warm; selected XIAO report has 6 phases, 13 coverage areas, and a 33-node/52-edge graph; HackRF One 86-pin map; test-pack schema `1.0` |
| Electrical simulation | live `/api/prototype/simulate` solved graph-derived 3.3 V source and 220-ohm load at `n1=3.3 V`; no physical mutation |
| Firmware emulation | checksummed Renode 1.17.0 installed; Nano 33 BLE model ran a compatible ARM ELF for 50 ms and matched the expected emulated-RAM proof marker; no physical mutation |
| Visual intelligence | live RapidOCR found ESP32-S3, CP2102 and SILABS candidates locally; browser review flow passed; image bytes were neither returned nor persisted |
| Tool diagnostics | live API and browser reported ngspice 46 using an allowlisted non-mutating diagnostic contract |
| Instrument discovery | live scan distinguished pyOCD/OpenOCD availability from zero connected debug probes, absent sigrok, zero logic analyzers, and unconfirmed target wiring; no target opened or signal driven |
| Definition bundles | `.fzpz` fixtures preserve connector mappings, embed sanitized SVG views, strip script/events/external references, and reject ZIP traversal |
| Production bundle | initial entry reduced from 1,054 KB to 397,078 B; Prototype and Monaco verified as lazy dynamic entries |
| Firmware build | isolated PlatformIO 6.1.18 compiled source version 0.6.0 for XIAO ESP32-S3 Sense at 55,724 B RAM and 1,001,541 B flash; attached runtime remains 0.5.0 and nothing was flashed |
| Supply chain | API audit has no known vulnerabilities; React audit has zero vulnerabilities; PlatformIO-only exceptions are isolated and documented; CycloneDX SBOMs and 315-component license inventory parse with zero unresolved identifiers |
| CI/privacy | workflow gates regression, audits, production bundle/budget, SBOMs, and privacy; 219 tracked and non-ignored paths pass locally |
| Source-control privacy | no tracked runtime database, private key, or archive; only the intentionally blank `.env.example` matched sensitive filename rules |
