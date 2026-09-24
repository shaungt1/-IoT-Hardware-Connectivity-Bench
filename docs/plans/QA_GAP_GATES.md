# QA, Review, and Gap Gates

Status: required delivery process  
Date: 2026-09-24

Quality activities are separate gates. Passing unit tests does not replace code review, UX review,
security review, electrical-safety review, hardware verification, or gap analysis.

## Required iteration loop

Every feature and phase follows this loop:

1. **Pre-gap analysis** - record current behavior, missing evidence, affected devices, risks, and
   measurable acceptance criteria before design or code changes.
2. **Design review** - review boundaries, schema/API changes, failure paths, migration, platform impact,
   safety class, observability, accessibility, and rollback.
3. **Implementation** - keep changes scoped; add instrumentation, fixtures, tests, and documentation
   with the behavior.
4. **Code review** - inspect correctness, concurrency, ownership, cleanup, error handling, security,
   dependency choices, performance, and maintainability.
5. **Automated verification** - run static, unit, integration, contract, migration, API, browser,
   accessibility, security, and packaging suites appropriate to the change.
6. **Real-fixture verification** - exercise every hardware claim on identified fixtures and capture
   tool versions, timestamps, inputs, raw evidence, and results.
7. **UX review** - verify primary workflows, loading/error/empty/stale/offline states, tooltips,
   progressive disclosure, keyboard navigation, responsive layout, and recovery paths.
8. **Safety and security review** - test target binding, approval, voltage/fixture constraints,
   cancellation, timeouts, redaction, malicious input, privilege, and audit completeness.
9. **Post-gap analysis** - compare acceptance criteria to evidence, record residual gaps and deferred
   risks, and update the supported hardware matrix.
10. **Release review** - only eligible changes enter a release candidate; failed gates return to step 1.

## Evidence required for completion

Every completed backlog item links or names:

- test command and result;
- affected schema/API version;
- browser or CLI flow exercised;
- fixture model, stable ID, wiring/profile, and firmware version when hardware is involved;
- screenshots only as supporting UX evidence, never as the sole functional proof;
- structured logs or operation/test receipt IDs;
- security/safety review result for active operations;
- documentation changed; and
- residual risk or `none identified`.

## Test pyramid

| Layer | Purpose | Required examples |
| --- | --- | --- |
| Static | Catch structural errors | formatting, lint, typing, schema validation, dependency policy |
| Unit | Validate pure logic | matching, classification, parsers, graph rules, risk policy, redaction |
| Contract | Stabilize extension surfaces | adapters, test packs, providers, simulator adapters, API, MCP |
| Integration | Validate service boundaries | SQLite migrations, tool runners, operations, events, credentials |
| Simulated hardware | Exercise failures cheaply | timeouts, malformed frames, disconnects, noisy buses, bad boot modes |
| Real hardware | Prove physical behavior | identification, sensors, radio, camera, display, flash, recovery |
| Browser E2E | Prove user workflows | host scan through receipt on Chromium, Firefox, and WebKit where viable |
| Accessibility | Prove inclusive interaction | keyboard, focus, names, contrast, reduced motion, zoom, screen reader |
| Performance | Enforce budgets | inventory latency, event rate, graph size, memory, reconnect, stream FPS |
| Soak/fault | Prove resilience | repeated reconnect, port contention, network loss, process crash, disk full |
| Security | Prove control boundaries | auth, CSRF/CORS, path/archive, injection, secrets, plugin/device hostility |
| Packaging | Prove delivery | clean install, update, rollback, offline launch, uninstall, retained data |

## Hardware truth rules

- USB VID/PID proves an interface identity, not necessarily the downstream board.
- A boot-ROM or debug ID can verify a processor but not every populated carrier component.
- A definition proves what a model is designed to contain; it creates `expected` claims.
- An I2C response proves an address response. Part identity needs a discriminating signature or
  confirmed definition.
- SPI, UART, GPIO, ADC, PWM, and SDIO need known topology, cooperative firmware, or a protected fixture.
- A simulated pass is never a physical pass.
- A photo match is inferred until confirmed.
- A green UI badge without current raw evidence and test criteria is a defect.

## Fixture matrix

Maintain a versioned matrix containing:

- fixture ID, vendor/model/revision, processor/module, interfaces, and known components;
- cables, hubs, probes, fixture firmware, host OS, drivers, tool versions, and power conditions;
- supported identity, pin, bus, communications, test, firmware, recovery, and simulation paths;
- last successful run, known failures, quarantine status, and owner; and
- golden expected evidence and tolerances.

Minimum first-release representatives:

- unknown USB peripheral and finished HID/media/storage devices;
- CP210x/CH34x/FTDI bridge with no target response;
- ESP8266 and ESP32 family targets;
- SAMD/CircuitPython Feather-class target;
- Nordic Nano BLE Sense-class target and onboard sensors;
- RP2040/RP2350 target;
- STM32 target with SWD;
- Linux Raspberry Pi and RISC-V SBC;
- NVIDIA Jetson or supported equivalent Linux accelerator board;
- Hailo PCIe/M.2 accelerator where hardware is available;
- HackRF or supported SDR;
- I2C/SPI/UART/GPIO protected fixture with known attachments; and
- one documented custom board.

Unavailable physical fixtures keep the relevant adapter experimental. A mock does not promote it.

## UX gate checklist

- Primary task is reachable without understanding internal tool names.
- Passive peripherals and circuit targets are visually separated.
- Step connector lines touch only the outer faces and remain centered at all supported widths.
- No nested cards, cramped tables, overlapping text, truncated buttons, or layout shift on status change.
- Every operation has immediate feedback, progress, cancellation where safe, success/failure output,
  and a durable receipt.
- Disabled actions explain exact prerequisites and link to the relevant setup.
- Evidence status, source, timestamp, and confidence are available without crowding the main view.
- URLs are validated, spaced, keyboard reachable, and open with an explicit external-link affordance.
- Camera says no camera when absent; it waits for frames only when a camera path is detected.
- Terminal is collapsible, target-labeled, stream-aware, and never appears to be an unrestricted shell.
- Tables are scannable with adequate padding and become appropriate stacked layouts on narrow screens.
- Focus returns predictably after dialogs, refreshes, step changes, and destructive confirmations.
- Reduced-motion, 200% zoom, screen-reader names, color independence, and high contrast pass.

## API and adapter gate checklist

- Schema is versioned and backward compatibility impact is documented.
- Inputs, outputs, errors, timeouts, cancellation, and partial results are typed.
- Operations are idempotent or carry idempotency keys.
- Target and interface generation are revalidated immediately before active work.
- Tool binaries and definitions have version/checksum/license metadata.
- Subprocess trees terminate on cancellation and release ports/locks.
- Adapter failure cannot crash inventory or corrupt another target.
- Secrets and raw sensitive payloads are redacted before logs/events.
- Every adapter has golden fixtures, negative fixtures, and conformance tests.
- Public, MCP, and UI behavior converge on the same application service and policy decision.

## Active-operation gate

Any operation that can reset, write, erase, flash, drive pins, change power/radio state, modify network
profiles, or alter files requires:

1. compatible identified target and interface;
2. explicit risk and affected resources;
3. validated prerequisites, voltage, wiring, boot mode, and free-space/layout where relevant;
4. backup or documented reason backup is impossible;
5. previewable plan and immutable artifact hash;
6. short-lived target-bound approval;
7. exclusive lock, timeout, cancellation strategy, and cleanup;
8. verification and reconnect criteria;
9. recovery instructions tested on the same family; and
10. durable audit receipt.

## Security gate

Before a public release candidate:

- threat model the native bridge, browser boundary, local API, remote mode, tool runners, plugins,
  definitions, archives, SVG/images, credentials, event streams, webhooks, updater, and MCP;
- run dependency, secret, static, dynamic, and container/image scans where applicable;
- validate localhost default, CORS/CSRF, authentication, TLS, token audience, permission-aware tool
  discovery, path traversal, command injection, archive bombs, XML/SVG attacks, and device-output
  injection;
- generate SBOM and build provenance; verify artifact signatures and update rollback; and
- close all critical/high findings or document a release-blocking exception approved by maintainers.

## Performance budgets

Exact thresholds are set from Phase 0 baseline measurements, then checked in CI or lab runs. At
minimum track:

- time to first host inventory and incremental refresh;
- attach-to-visible and reconnect-to-ready latency;
- inspect/test cancellation latency;
- API event throughput, dropped events, queue depth, and reconnect replay;
- CPU, memory, file handles, serial handles, database growth, and retained artifacts;
- camera frames/rate and terminal/log throughput without starving control events;
- 1,000-node graph interaction and layout time; and
- 8-hour and 24-hour soak stability for supported release profiles.

## Phase gate report

Each phase closes with one short report:

```text
Phase:
Acceptance criteria passed:
Automated test evidence:
Real-fixture evidence:
UX/accessibility review:
Security/electrical review:
Performance/soak result:
Migration/rollback result:
Open gaps and severity:
Supported/experimental matrix changes:
Release decision: pass | conditional | fail
```

`conditional` is not production complete. It may enter an experimental build only when the remaining
gap is visible to users and cannot cause unintended writes, incorrect verification, secret exposure,
or unrecoverable device state.

## Production release gate

The system is production-ready only when:

- all Phase 13 exit criteria pass;
- no critical/high defect, safety issue, security issue, or migration/data-loss risk remains;
- supported claims have current real-fixture evidence on the published matrix;
- install/update/rollback/uninstall and database backup/restore pass on every supported OS;
- public API, plugin, and MCP compatibility/security suites pass;
- accessibility and responsive-browser gates pass;
- licenses, notices, SBOM, signatures, provenance, privacy, and security reporting are complete; and
- `GAP_ANALYSIS.md` names every known material limitation without marketing inflation.
