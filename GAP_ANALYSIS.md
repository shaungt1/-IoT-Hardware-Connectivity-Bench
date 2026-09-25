# IoT Hardware Connectivity Bench Gap Analysis

Date: 2026-09-24

The authoritative requirement trace, verified evidence, active gaps, execution order, and repeated QA
gate are in [`docs/plans/REQUIREMENT_EXECUTION_LEDGER_2026-09-24.md`](docs/plans/REQUIREMENT_EXECUTION_LEDGER_2026-09-24.md).
Read [`docs/ideas/getting_lost.md`](docs/ideas/getting_lost.md) before changing scope or declaring the
project complete. Older plans remain useful design history but cannot override live evidence in the ledger.

## Verified State

- The React workflow is Host, Selected device, Pins, Connections, Tests, Firmware, Prototype, then Tools.
- Host inventory separates circuit/controller targets from passive peripherals and retains bridge identity
  separately from target, board, component, pin, runtime, and attachment evidence.
- Selected-device inspection now reports six explicit stages (discover, identify, decompose, trace, enrich,
  verify), 13 coverage areas, unresolved evidence routes, adapter attempts, and the physical limit of USB-only
  inspection. The current XIAO graph contains 33 nodes and 52 provenance-bearing relationships.
- The attached XIAO ESP32-S3 Sense is authenticated by cooperative firmware; its 14 external pads,
  ESP32-S3R8, camera, microphone, storage, PSRAM, Wi-Fi, and BLE are represented without calling its USB
  interface the whole board.
- Camera transport uses a binary latest-frame WebSocket that skips superseded frames, and the browser
  decodes into a stable canvas. The last pre-change Chrome baseline measured 17.5 source FPS, 14.8 painted
  FPS, 4 ms host-receive-to-paint latency, and 1,802 kbps. The post-change live rerun is blocked because the
  ESP camera fixture is currently disconnected; earlier 30-minute and 5-minute soaks remain valid historical evidence.
- BLE and Wi-Fi have a dedicated Connections stage with device-side controls and computer-side scans;
  absent radio capabilities are visibly muted and disabled.
- Windows device events and a two-second presence fallback remove stale serial/USB targets, preserve
  last-known evidence behind a red disconnected state, and lock live actions. Physical unplug/replug remains to be exercised.
- Known pins can store user-confirmed component/sensor mappings as declared evidence with exact graph edges;
  the application never promotes those observations to automatic detection.
- Safe probe/test packs, durable redacted history/export, ten probe routes, controlled operations, firmware
  analysis, source editing, PlatformIO/Arduino tooling, and isolated Renode execution are active.
- CMSIS-SVD, DeviceTree, KiCad schematic, and Fritzing part/bundle parsers produce provenance-bearing
  structured evidence with hostile-input bounds.
- The Prototype stage contains all 50 installed Wokwi elements plus the exact XIAO visual, exact terminal parity, XIAO 14-pad
  geometry, canonical wires, backend validation, persistence, ngspice, Renode, and protected physical-I/O
  contracts. It does not claim unsupported electrical or physical behavior.
- Local OCR creates marking candidates and requires explicit confirmation before promotion; images are not
  persisted in evidence history.
- The built-in MCP responds through stdio with 26 tools, 2 safety prompts, and hardware, evidence, events,
  and capability resources. It cannot approve or execute physical mutations.
- 123 backend tests, React type checking, the live HackRF Phase One browser suite, MCP stdio, a prior real
  XIAO firmware compile, dependency audits, the 219-path privacy scan, and prior production bundle budget pass.
- The initial production entry is 397,078 bytes; Prototype and Monaco are lazy entries. CycloneDX SBOMs and
  a 315-component license metadata inventory are generated in CI.

## Remaining Gaps

| Priority | Gap | Honest completion gate |
| --- | --- | --- |
| High | Hardware fixture breadth | Add real Nordic, STM32, RP2040, ESP8266, SAMD, Linux SBC, NPU, SDR, debug, logic, and analog fixtures with repeatable acceptance evidence. |
| High | Non-enumerable circuitry | Require definitions, cooperative firmware, debug access, external instruments, or user confirmation; never claim USB alone reveals passive traces/components. |
| High | Hybrid physical control | Flash a compatible negotiated control runtime only with explicit approval, then prove one protected virtual-input-to-real-output circuit with ownership, timing, disconnect, and recovery evidence. |
| High | Release security | Add hosted authentication/tenant boundaries, signed releases, update/rollback, an independent threat-model review, and a clean-machine CI/install run. |
| Medium | Remaining physical reliability | Earlier camera soaks pass. The post-change camera benchmark, physical unplug/replug cancellation, radio reconnect, and port rebinding still require the ESP fixture to be connected and deliberate fixture interaction. |
| Medium | Definition/catalog scale | Add licensed vendor indexes, CMSIS packs, KiCad/LibrePCB libraries, neutral unknown-board composition, and fidelity/license reports. |
| Medium | Firmware operations | Live bounded logs, cancellation, and child-process cleanup pass; backup/restore and recovery physical fixtures plus stronger hostile-tool sandboxing remain. |
| Medium | Electrical/simulation depth | Add transient/AC models, richer sensor/instrument models, named buses/nets, undo/redo, and CircuitJS or equivalent interactive handoff. |
| Medium | Native lifecycle breadth | Add Linux udev and macOS IOKit event adapters; the portable reconciliation fallback remains functional but slower. |
| Medium | Public API maturity | Machine-readable API/schema version and compatibility contracts pass; generated clients and authenticated subscriptions/webhooks remain before a hosted or multi-user release. |

## Boundary

No host application can universally infer every unexposed chip, passive component, trace, or sensor on an
arbitrary unmodified board. The product closes this gap through layered evidence and extensible adapters,
not unsafe brute-force pin driving. Unsupported facts remain unknown and visible.
