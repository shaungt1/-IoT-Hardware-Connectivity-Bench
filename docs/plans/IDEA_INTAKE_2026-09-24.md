# Idea Intake: Device State, Pin Knowledge, Firmware Access, NPU Catalog, and Prototype Studio

Status: accepted into product plan  
Date: 2026-09-24

## Scope reviewed

This intake incorporates these user-authored idea records:

- `docs/ideas/async_state_ui_issues/async_state_ui_connection.md`
- `docs/ideas/document_pin_modes_and_interfaces.md`
- `docs/ideas/low_level_source_code_editing.md`
- `docs/ideas/npu_device_chip_list_2026.md`
- `docs/ideas/rapid_iot_prototype_tool.md`

`docs/ideas/agentic_ai_integration.md` is intentionally excluded. It belongs to a separate active
workstream and was not used to change this plan.

## Accepted product decisions

### One device lifecycle across every view

Create one connection-state manager with stable physical identity and the states `discovering`,
`connected`, `selected`, `probing`, `ready`, `busy`, `disconnected`, `reconnecting`, and `error`.
Attach/remove events update Host, Device, Pins, Tests, Firmware, Prototype, Tools, and the terminal.
An unplugged selected target keeps its last-known workspace and prototype topology, visibly becomes
disconnected, releases handles, cancels unsafe I/O, and disables live actions. It is not silently
replaced by another COM port.

### One normalized pin and interface knowledge service

Pin names are normalized without losing vendor aliases. Generic explanations for GPIO, ADC, DAC,
PWM, I2C/I3C, SPI/QSPI/OSPI, UART and differential serial families, CAN/LIN, USB, debug, audio,
storage, display/camera, Ethernet/PCIe, clocks, boot/control, power, and ground remain separate from
board-specific mux, voltage, reserved-pin, boot, conflict, and evidence records. Unknown functions
remain importable and reviewable rather than being discarded.

### Board and silicon are different catalog entities

The edge-AI catalog uses a normalized hierarchy:

`manufacturer -> device/board/module -> SoC -> CPU -> accelerator -> memory -> media -> I/O -> SDK/OS`

Multiple boards reference one canonical silicon record. Accelerator kind is explicit: dedicated NPU,
BPU/TPU/DRP-AI, GPU/tensor, DSP, or MCU vector/SIMD. Initial families include Sipeed, Milk-V,
Luckfox, Orange Pi, Banana Pi, Radxa, D-Robotics, BeagleBoard, Raspberry Pi plus Hailo, NVIDIA
Jetson, Google Coral, and hybrid MPU/MCU devices. Catalog claims are expected metadata until live
evidence verifies the installed hardware and runtime.

### Firmware access is assessed before editing

Every target receives an access report covering source availability, readable/writable firmware,
bootloader, debug interface, protection, recovery path, and allowed optimization mode. The browser is
the control plane; native adapters perform pinned builds, backups, flashes, resets, and verification.
Original C/C++ is not claimed to be recoverable from a binary. Binary analysis and decompiler output
remain derived artifacts. Automatic binary patching is not part of the first production milestone.

### Prototype is a structured hybrid hardware graph

Prototype begins with the already inspected physical device. Boards, parts, pins, nets, buses, power
domains, state sources, evidence, constraints, visuals, and simulator/control bindings live in one
versioned graph. A wire is a typed relationship, not artwork. Every component and reading is labeled
`physical`, `simulated`, `hybrid`, `disconnected`, or `user-defined`.

The target experience supports both directions:

1. Virtual sensor or controller state can drive a real output through an explicitly supported,
   protected hardware-control adapter.
2. A real sensor or instrument can drive a virtual circuit or controller model.

This requires a hardware-in-the-loop event protocol with clock ownership, ordering, backpressure,
safe disconnect behavior, capability negotiation, and recorded evidence. USB enumeration alone never
enables arbitrary GPIO or bus writes.

### Reuse engines behind adapters

- React Flow: graph canvas and interaction.
- Wokwi/Fritzing/manufacturer libraries: licensed visual parts and connector geometry.
- CircuitJS and ngspice: supported electrical subsets.
- Renode and selected browser CPU emulators: optional firmware/processor subsets.
- Firmata, Linux GPIO, runtime RPC, and vendor/debug tools: live-control implementations.
- sigrok: logic capture and protocol decoding.
- KiCad: professional EDA handoff, not a feature to recreate.

Every integration needs a license decision, version pin, sandbox boundary, conversion-loss report, and
an unsupported-model path.

## First implementation receipt

The initial foundation landed with this intake:

- A versioned prototype project model and SQLite persistence API.
- A dedicated React Prototype stage powered by React Flow.
- The inspected device is seeded as the authoritative physical controller.
- Users can add simulated analog sensors and LEDs, connect structured pin endpoints, adjust a virtual
  sensor value, inspect provenance, save, and reopen the graph.
- Disconnected physical targets remain visible and are not represented as live.
- A normalized common pin-knowledge module now annotates known aliases and supplies contextual safety
  text in pin tooltips.
- Graph validation rejects duplicate identities, dangling nodes, and unknown pin endpoints.

This is a foundation, not completion of Studio or hardware-in-the-loop control. Electrical validation,
undo/redo, catalog import, live adapter bindings, simulation engines, instruments, event-driven OS
hot-plug, and production revision history remain in the backlog.

## Non-negotiable truth and safety boundaries

- A USB bridge identifies the bridge, not automatically the board behind it.
- Passive components and most arbitrary GPIO/SPI wiring cannot identify themselves.
- Definitions, photos, firmware references, and catalogs can create candidates, not verified hardware.
- No unknown pin is driven, bus is swept, firmware is written, or protection is bypassed to improve
  discovery coverage.
- Physical writes require exact target binding, compatible adapter capability, voltage/current
  constraints, explicit approval, locking, audit evidence, cleanup, and a recovery path.
