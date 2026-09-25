# Plan Gap Review

Status: initial review complete  
Date: 2026-09-24

## Review result

The plan covers the stated end-to-end product vision and separates production-critical work from
research and optional hosted work. It does not claim that the current implementation is production
ready. The current system is a strong functional baseline; the largest remaining production gaps are
stable evidence schemas, adapter breadth with real fixtures, unified active-operation controls,
security/packaging, and repeatable cross-platform hardware evidence.

## Requirement coverage

| Requirement | Plan coverage | Backlog families | Review status |
| --- | --- | --- | --- |
| Separate passive products from working circuits | Phases 1 and 3 | `UX`, `ADP` | Covered |
| Discover all host-visible devices/interfaces | Phase 1 | `UX`, `CORE` | Covered with OS limits stated |
| Identify bridge, processor, module, carrier, runtime separately | Phases 2-3 | `EVD`, `DEF`, `SDK`, `ADP` | Covered |
| Use CMSIS-SVD and Zephyr/Linux device trees | Phase 2 | `DEF` | Covered |
| Cross-vendor MCU/SBC/accelerator/SDR support | Phase 3 | `ADP` | Covered; fixture acquisition remains work |
| Map pins, buses, major components, and attachments | Phases 2, 4, 6 | `PIN`, `DEF`, `FIX` | Covered without universal-enumeration claim |
| Detect and test onboard/added sensors | Phase 4 | `TST`, `PIN`, `FIX` | Covered; requires runtime/fixture |
| BLE, Wi-Fi, network, MQTT, CoAP, services | Phase 5 | `COM` | Covered |
| Camera, display, storage, radio, OS/service tests | Phases 4-5 | `TST`, `COM` | Covered |
| Live terminal/signals/progress/receipts | Phases 4, 7 | `UX`, `TST`, `FW` | Covered |
| Edit code, build, backup, flash, recover | Phase 7 | `FW` | Covered with write gates |
| Firmware layers, carving, decompilation, SVD correlation | Phase 8 | `FINT` | Covered from idea intake |
| Interactive rapid-prototyping canvas | Phase 9 | `STU` | Covered |
| Mixed virtual and physical hardware-in-the-loop | Phases 9-10 | `STU`, `HIL`, `FIX` | Covered with explicit adapter and fixture gates |
| Hot-plug state across every workspace | Phases 1 and 9 | `UX`, `CORE`, `STU` | Covered; OS event adapters remain work |
| Common pin/interface explanations and aliases | Phases 2 and 4 | `PIN`, `DEF` | Covered; initial knowledge foundation implemented |
| Edge-AI board, module, SoC, and accelerator catalog | Phases 2-3 | `CAT`, `DEF`, `ADP` | Covered; catalog data remains expected until verified |
| Firmware/source/binary access assessment | Phases 7-8 | `FW`, `FINT` | Covered without claiming source recovery |
| Circuit/electrical/firmware simulation | Phase 10 | `SIM`, `HIL` | Covered as engine adapters |
| KiCad/Fritzing interoperability | Phases 9 and 11 | `STU`, `EDA` | Covered with licensing/fidelity gates |
| Photos/OCR/AI identification | Phase 11 | `VIS`, `AI` | Covered; inferred until confirmed |
| Built-in MCP for agents | Phase 12 | `MCP` | Covered as bundled read-only-first capability |
| Public/internal API separation and plugin SDK | Phases 2, 3, 12 | `CORE`, `SDK`, `API`, `PLG` | Covered |
| VS Code integration | Phase 12 | `IDE` | Covered after public API |
| Mobile companion and nearby BLE | Phase 12 | `MOB`, `COM` | PWA first; native shell evaluated for direct radio access |
| Observability/Grafana/SigNoz | Cross-phase | `OBS` | Covered as optional product telemetry, not device protocol |
| Production install/security/release/open source | Phase 13 | `GOV`, `SEC`, `PKG`, `REL`, `DOC` | Covered |
| Optional low-cost paid product | Phase 14 | `PROD`, `CLOUD` | Covered behind validation gate |
| Repeated gap analysis, review, and testing | Every phase | `QA` | Covered as independent required gates |

## Gaps deliberately not hidden

1. **Fixture availability:** Jetson, Hailo, Beken, multiple STM/Nordic/RP families, debug probes, and
   protected bus fixtures must be acquired or contributed before support can be called verified.
2. **Universal passive discovery is impossible:** definitions, firmware references, photos, and weak
   bus signatures can produce candidates; direct evidence or confirmation is still required.
3. **Licensing is unresolved:** the project license and redistribution rights for vendor packs,
   Fritzing assets, simulators, analyzer bundles, firmware samples, and documentation must be decided.
4. **Remote control raises the risk substantially:** production remote mode, hosted labs, and MCP HTTP
   are gated behind authentication, TLS, audience/scopes, tenant controls, and threat review.
5. **Firmware analysis is not source recovery:** decompiler output and inferred register links require
   human review and cannot verify a populated or working physical component.
6. **Simulation coverage will be partial:** every engine models a subset. The UI and result schema must
   expose modeled, stubbed, proxied, ignored, and unsupported elements.
7. **Electrical work needs hardware protection:** software cannot make arbitrary unknown pin stimulus
   safe without voltage/current/isolation and a wiring profile.
8. **A five-dollar plan is not yet a decision:** support, hosting, payment, and managed-metadata costs
   need real user and cost evidence after open-source adoption.

## Plan-quality findings

### Resolved during review

- Added firmware intelligence as a first-class phase instead of burying it under the code editor.
- Added an isolated hostile-input boundary for firmware, archives, SVG, definitions, and plugins.
- Added explicit real, simulated, and hybrid truth modes.
- Added Fritzing asset ingestion without treating artwork as hardware evidence.
- Added a bundled MCP lifecycle task and read-only/loopback default.
- Added a structured hybrid prototype graph, live/simulated provenance, and bidirectional HIL gates.
- Added stable disconnected-workspace behavior and a common pin/interface knowledge service.
- Separated edge-AI devices/modules from canonical silicon and accelerator records.
- Kept observability separate from device messaging and measurement records.
- Kept React as the product UI and HTML as validation/recovery until parity.

### Decisions still required before public release

- Project license and contributor agreement/DCO approach.
- Supported OS/version matrix and installer technology.
- Reference protected fixture design and bill of materials.
- Initial real-hardware support matrix promised as stable versus experimental.
- Retention defaults for raw firmware, images, captures, frames, and terminal output.
- Whether hosted synchronization is ever enabled by default; recommendation is no.

## First execution slice

The first slice should not install every proposed analyzer or simulator. Execute these tasks in order:

1. `GOV-001`, `QA-001`, `CORE-001` - ratify scope and freeze measured contracts.
2. `UX-001`, `UX-002`, `UX-003` - make device separation and reconnect identity dependable.
3. `EVD-001`, `EVD-002`, `EVD-003` - establish the truth/evidence graph and migrate the baseline.
4. `SDK-001`, `SDK-002`, `SDK-003` - formalize adapters and move existing hardware behind them.
5. `CORE-003`, `CORE-004`, `CORE-005` - cancellation, approvals, generation checks, and locks.
6. `DEF-001`, `DEF-002`, `DEF-003` - land SVD and device-tree ingestion against fixtures.
7. `TST-001`, `TST-002`, `TST-007` - generate transparent tests and durable results.
8. `COM-001`, `COM-002`, `COM-003`, `COM-005` - complete React communication parity.
9. `QA-010` - run the first full independent gate and update `GAP_ANALYSIS.md`.

This slice creates a stable platform for vendor breadth, firmware intelligence, MCP, and the Circuit
Studio. Starting those larger integrations before the evidence and adapter contracts would create
one-off code and repeat the exact scalability problem the product is intended to solve.

## Ideas-folder audit

Files incorporated on 2026-09-24:

- `docs/ideas/new_resources.md` -> `RESOURCE_INTAKE.md`
- `docs/ideas/firmware_intellgence_layer.md` -> `FIRMWARE_INTELLIGENCE_INTAKE.md`
- `docs/ideas/async_state_ui_issues/async_state_ui_connection.md`
- `docs/ideas/document_pin_modes_and_interfaces.md`
- `docs/ideas/low_level_source_code_editing.md`
- `docs/ideas/npu_device_chip_list_2026.md`
- `docs/ideas/rapid_iot_prototype_tool.md`

Those five records are dispositioned in `IDEA_INTAKE_2026-09-24.md` and the task backlog. The separate
`docs/ideas/agentic_ai_integration.md` workstream was intentionally not reviewed or changed.

Future idea files should receive an intake record before their content changes the master plan or
default dependency set.
