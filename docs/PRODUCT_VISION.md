# Product Vision

## Mission

Make unfamiliar embedded hardware understandable and testable from one browser workspace. A user
should be able to attach a microcontroller, Linux board, accelerator, radio, custom circuit, or
ordinary USB peripheral; see exactly what the host can observe; select a circuit target; build an
evidence-backed model of its processors, modules, buses, pins, firmware, services, and attached
components; and run only the tests that the current connection can perform safely.

The long-term product extends that verified hardware model into firmware work, flashing and recovery,
device-to-device communications, an interactive circuit studio, simulation, and agent access through
the same policy-controlled APIs.

## Product promise

The bench answers four questions without pretending that USB descriptors are a schematic:

1. **What is connected?** Inventory every host-visible interface and separate circuit targets from
   transport bridges, unresolved devices, and finished/passive peripherals.
2. **What is it made of?** Combine live probes, board definitions, CMSIS-SVD, device trees, runtime
   inspection, vendor metadata, filesystems, debug paths, and confirmed visual evidence.
3. **Does it work?** Generate capability-specific tests with measured output, provenance, timestamps,
   risk, and repeatable pass/fail criteria.
4. **What can I do next?** Offer the valid connection, code, backup, flash, recovery, communications,
   and prototyping actions for the evidence actually present.

## Primary experience

The React application becomes the product interface. The dependency-free HTML client remains a
validation and recovery surface until React reaches full parity.

1. **Host and devices** - live host inventory with separate sections for circuit targets, debug or
   transport bridges, unresolved candidates, and passive finished products.
2. **Selected device** - layered identity, confidence, evidence, processor/module/carrier hierarchy,
   runtime, services, documentation, history, and contradictions.
3. **Pins and buses** - pin map, voltage and safety labels, alternate functions, bus controllers,
   measured or declared attachments, and controlled discovery.
4. **Communications** - BLE, Wi-Fi, Ethernet, MQTT, CoAP, HTTP, SSH, serial, radio, and device-to-device
   sessions with explicit source, destination, credentials, and traffic state.
5. **Tests** - generated test packs for every supported component and capability, live output,
   terminal/event stream, receipts, and clear unavailable reasons.
6. **Firmware and files** - source tree, Monaco editor, diff, serial terminal, builds, authorized
   acquisition, software-layer analysis, backup, flash, verification, SD imaging, and recovery behind
   target-bound approvals.
7. **Circuit studio** - evidence graph and visual board/pin model, parts catalog, nets, constraints,
   simulation, hardware-in-the-loop runs, and export to engineering tools.
8. **Tools and sources** - adapter health, metadata providers, licenses, versions, diagnostics, and
   install guidance without burying core workflows in a giant table.

Every action exposes a state: idle, waiting, running, passed, failed, canceled, blocked, or stale.
Every unfamiliar icon has a tooltip. Empty states explain what evidence or fixture is required.
The interface uses progressive disclosure so a first scan stays readable while advanced evidence is
available in accordions, drawers, or focused workspaces.

## Evidence truth model

Every claim has a value, status, confidence, provenance, collection time, target fingerprint, and
contradiction history. Status values are:

- `verified` - observed through a compatible live protocol, runtime, operating system, or debug path.
- `detected` - host or bus evidence is present but the exact part or behavior is not proven.
- `declared` - explicitly selected or entered by the user.
- `expected` - derived from a trusted definition for the identified model but not tested on this unit.
- `inferred` - a candidate from correlation, visual analysis, or weak signatures.
- `unavailable` - the current transport, fixture, permission, or firmware cannot verify it.
- `contradicted` - two sources disagree and require resolution.

The system never silently upgrades `expected` or `inferred` to `verified`.

## Physical boundary

No program can universally discover every passive component or wire through an arbitrary USB-to-UART
bridge. SPI has no universal enumeration protocol; GPIO and analog pins do not identify what is wired
to them; and undocumented firmware may expose no introspection at all. The product reaches the maximum
honest result by progressively combining:

1. passive host enumeration;
2. known bridge and boot-ROM handshakes;
3. debug access such as SWD/JTAG when a fixture is attached;
4. operating-system and runtime inspection;
5. board and silicon descriptions;
6. protected I2C/SPI/UART/GPIO/ADC fixtures;
7. cooperative diagnostic firmware;
8. confirmed visual/OCR evidence; and
9. user-provided schematics, BOMs, or board definitions.

Unknown pins are never driven during discovery. Write, erase, flash, reset, power, and high-current
operations require a target-specific procedure, voltage constraints, recovery path, and explicit
approval.

## Product principles

- **Local first:** discovery and control work without a paid cloud or AI account.
- **Evidence before confidence:** show how the system knows, not only what it thinks.
- **Cross-vendor by contract:** vendors extend adapters and definitions, not conditional UI code.
- **Read first, write deliberately:** passive and read-only work is easy; disruptive work is gated.
- **One capability model:** browser, CLI, public API, VS Code, and MCP use the same services and policy.
- **Built-in agent access:** a bundled MCP server exposes evidence and approved capabilities without
  granting agents raw shell, serial, or flash authority.
- **Useful without AI:** AI explains and accelerates; it is never required for core identification.
- **Accessible and efficient:** keyboard navigation, readable density, responsive layouts, and no
  mystery loading states.
- **Contributor friendly:** versioned schemas, fixtures, adapter templates, contract tests, and short
  setup documentation make new hardware support reviewable.

## Initial users

- Makers and developers evaluating a box of unfamiliar boards.
- Firmware engineers bringing up prototypes or validating production samples.
- Test engineers creating repeatable acceptance packs and hardware matrices.
- Educators and learners who need transparent pin, bus, and sensor explanations.
- Teams maintaining mixed Raspberry Pi, Jetson, Hailo, Arduino, Espressif, Nordic, STM, Beken,
  Rockchip, Allwinner, SDR, camera, and custom-board fleets.

## Product and open-source direction

The recommended model is an open-source, local hardware core with no paywall around discovery,
testing, adapter development, or access to a user's own devices. A paid service can later add hosted
device history, team workspaces, managed metadata mirrors, remote labs, signed test-pack distribution,
collaboration, and optional AI assistance. A low-price personal plan can be tested only after the local
release is dependable and the paid value is distinct from basic hardware ownership.

Before public launch, complete a dependency-license inventory and choose the project license. Apache
2.0 favors broad commercial contribution; AGPL or a dual license favors hosted-service reciprocity.
That is a product and legal decision, not an implementation default.

## Success measures

- Time from attachment to correctly classified interface and first actionable evidence.
- Percentage of claims with inspectable provenance.
- Supported fixture families with repeatable hardware-in-the-loop evidence.
- Test pass/fail reproducibility across Windows, Linux, and macOS.
- Zero unintended writes during inventory, inspection, or tests labeled read-only.
- Recovery success for interrupted supported flash workflows.
- New adapter time from template to contract-test pass.
- Browser task completion, accessibility, reconnect stability, and error recovery.
- Contributor setup success from a clean machine using only the public documentation.
