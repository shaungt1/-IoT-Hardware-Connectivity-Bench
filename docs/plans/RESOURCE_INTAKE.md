# Resource Intake: `docs/ideas/new_resources.md`

Status: reviewed and incorporated  
Date: 2026-09-24

The supplied note is valuable and aligns with the product direction. It correctly identifies that no
single project supplies the whole experience and that the differentiated layer is a normalized
hardware graph joining physical evidence, definitions, simulation, and interaction.

The original note remains unchanged at [`../ideas/new_resources.md`](../ideas/new_resources.md).
This document records what enters the plan and what needs qualification.

## Promoted into the architecture

| Idea from note | Disposition | Planned location |
| --- | --- | --- |
| Hardware graph is canonical | Adopt | Evidence/circuit graph in architecture and phases 2/9 |
| Physical, logical, electrical, firmware, network, runtime views | Adopt | Circuit Studio view model |
| CMSIS-SVD for MCU internals | Adopt | Hardware-description ingestion |
| Zephyr DeviceTree for board topology | Adopt | Hardware-description ingestion |
| Renode for firmware/SoC execution | Evaluate then optional integration | Simulation phase |
| Fritzing definitions and SVGs | Evaluate as import source | Definition/asset ingestion phase |
| KiCad symbols, footprints, schematics, netlists, models | Adopt later through import/API | EDA phase |
| CircuitJS and ngspice | Optional engines | Electrical simulation phase |
| React Flow/XYFlow | Adopt | Interactive circuit and evidence canvas |
| Real, simulated, and hybrid operation | Adopt as separate truth modes | Hardware-in-the-loop phase |
| Real device becomes a digital twin | Adopt with evidence labels | Device graph and history |
| Wokwi custom-chip abstraction | Study as a model/API reference | Simulator model SDK research |
| DigitalJS and SimulIDE | Evaluate, not core | Simulation research spikes |

## Important qualifications

1. Fritzing artwork and connector metadata can accelerate visuals, but source quality and license must
   be checked per library. Importing a part never verifies a component on physical hardware.
2. KiCad is an engineering interchange and authoring tool. The product should integrate through files
   and the current IPC API rather than embedding the desktop application.
3. Renode is powerful where a machine/peripheral model exists. Unsupported silicon still requires a
   new model; simulation coverage must be displayed explicitly.
4. CircuitJS/ngspice cover electrical subsets and DigitalJS covers synthesized digital logic. None is
   a universal replacement for MCU firmware, operating-system, radio, camera, or USB simulation.
5. Wokwi's custom-chip API is a useful design reference for pin and behavior models, but its beta API
   and external platform status make it an optional interoperability target, not the core dependency.
6. A digital twin is a graph revision plus provenance and live/simulated state. It must never merge
   simulated success with real-hardware verification.
7. Hybrid mode needs explicit adapters, time synchronization, backpressure, and physical protection.
   It cannot directly connect an arbitrary virtual bus to real pins without a fixture.

## New deliverables added because of the note

- A versioned device-model SDK with pins, controls, buses, state, behavior-model references, and
  visual assets.
- An asset-ingestion pipeline for Fritzing metadata/SVG with license and connector validation.
- Separate physical, logical, electrical, firmware, network, and runtime projections of one graph.
- A simulator adapter contract rather than simulator-specific UI code.
- A three-mode execution selector: real, simulated, hybrid.
- A hardware-in-the-loop bridge specification with deterministic event envelopes.
- A model-coverage panel listing which components are simulated, stubbed, proxied, or unsupported.
- Round-trip tests that detect lost pins, nets, constraints, evidence, and source attribution.

## Research evidence

- Fritzing's official format documents `.fzp` metadata, up to four SVG views, connectors, terminal
  points, and internal buses: [part file format](https://github.com/fritzing/fritzing-app/wiki/2.1-part-file-format).
- Renode documents writing peripheral models and Robot Framework test automation:
  [peripherals](https://renode.readthedocs.io/en/latest/advanced/writing-peripherals.html) and
  [testing](https://renode.readthedocs.io/en/latest/introduction/testing.html).
- Wokwi documents beta custom sensor/display/memory models compiled to WebAssembly and JSON pin
  definitions: [Chips API](https://docs.wokwi.com/chips-api/getting-started) and
  [chip JSON](https://docs.wokwi.com/chips-api/chip-json).
- DigitalJS describes itself as a JavaScript simulator for circuits synthesized by tools such as
  Yosys: [DigitalJS](https://github.com/tilk/digitaljs).
- SimulIDE describes real-time analog, digital, and microcontroller simulation for learning and
  experimentation: [SimulIDE](https://simulide.com/p/).

## Conclusion

The note strengthens phases for definition ingestion, the hardware graph, Circuit Studio, simulation,
and hardware-in-the-loop. It does not change the near-term priority: make discovery, identity,
evidence, adapters, tests, communications, and safe operations production-grade before presenting a
simulation environment as a complete digital twin.
