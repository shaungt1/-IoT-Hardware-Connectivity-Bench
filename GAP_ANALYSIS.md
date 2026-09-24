# IoT Hardware Connectivity Bench Gap Analysis

Date: 2026-09-24

The production vision, phased delivery plan, executable backlog, technology decisions, and recurring
QA/release gates are indexed in [`docs/README.md`](docs/README.md). This file remains the live record
of verified implementation state and is updated at each phase gate.

## Verified now

| Area | Current evidence |
| --- | --- |
| Host discovery | Serial ports, USB network targets, raw USB identities, host interfaces, and bounded mDNS service discovery have live API endpoints. |
| Private-network discovery | Standard neighbor/service discovery and explicit deep `/24` scans are implemented with private-subnet and fixed-port limits; web services render as links. |
| Safe selection | Unknown serial devices can be selected and classified without opening the port or sending bytes. |
| Arduino identity | Local Arduino CLI can identify compatible boards such as the previously verified `2341:805A` Nano interface as `arduino:mbed:nano33ble`. |
| Exact local model | Physical-device profiles retain a user-confirmed board model separately from transient COM-port assignments. |
| Linux target adapter | LicheeRV Nano USB networking, SSH, HTTP/PicoClaw, OS telemetry, and camera configuration inspection are implemented. |
| ESP32 adapter | USB telemetry, camera, BLE, direct Wi-Fi, router connection, and traffic checks are implemented for the diagnostic firmware when that target is attached. |
| Metadata sources | Offline catalog, Arduino CLI, PlatformIO, and CircuitPython sources report ready; optional GitHub, Nexar, and DigiKey credentials are surfaced. |
| User interfaces | The HTML validation client and Vite/React client share a six-stage Host -> Device -> Pins and buses -> Tests -> Firmware and files -> Tools workflow. |
| Diagnostics console | Both clients expose bench events; recognized Linux targets also expose a named read-only command allowlist. No arbitrary shell is exposed. |
| Nano sensor test pack | A diagnostic image for the Nano 33 BLE Sense is present and its handshake, five onboard sensors, and external I2C inventory were previously exercised through the live API. The Nano was not attached during the 2026-09-24 final audit. |
| CircuitPython Feather adapter | The connected Feather M0 Express exposes CIRCUITPY metadata, imports/libraries, 29 documented pins, 21 runtime-verified pin names, heap/CPU telemetry, and three-sample I2C scanning. The existing `main.py` hash remained unchanged across probes. |
| ESP8266 target adapter | A CP210x interface remains a bridge until an explicit ROM probe answers. The probe identifies the ESP8266EX and SPI flash without writing storage, then exposes Wi-Fi-only capability, identity layers, tests, and a NodeMCU candidate pin map. |
| Peripheral visibility | The host inventory retains physical USB peripherals and classifies circuit targets, bridges, SDRs, cameras, MIDI/HID devices, storage, and display adapters separately. |
| Controlled operations | Target-bound plans, 120-second approval tokens, per-target locks, timeouts, allowlisted commands, stale-file hashes, and SQLite audit receipts protect build/edit/backup/flash workflows. |
| Firmware workspace | Both clients browse/edit allowlisted project or mounted-device text files, build PlatformIO projects, expose conditional upload actions, and retain operation output. |
| Automated checks | 31 Python tests, JavaScript syntax, React TypeScript checks, live API probes, desktop browser flows, and mobile checks cover both clients. |

## Remaining gaps

| Priority | Gap | Required implementation |
| --- | --- | --- |
| Medium | Running-operation cancellation | Timeouts and target locks are implemented. Add subprocess/job cancellation and streamed progress for long builds and flashes. |
| Medium | Unified active-test approval | Build, edit, backup, and flash use target-bound approval tokens. Legacy device test/probe actions still use their test-specific UI confirmations and should move behind the same operation-plan API. |
| High | Cross-vendor adapters | The registry and adapter contract are in place; implement active identity adapters for Nordic, SAMD/AVR, RP2040/RP2350, STM32, Raspberry Pi, Beken/LibreTiny, Hailo, NVIDIA, HackRF, Rockchip, and Allwinner. |
| High | React radio feature parity | Port the HTML BLE/Wi-Fi/camera controls into React. Host discovery, device inspection, generic tests, tools/providers, and local advertised-service scanning are implemented; radio controls remain in HTML. |
| High | External provider queries | Implement cached query clients and schemas for optional component APIs. Current provider entries report configuration/readiness only. |
| High | Terminal streaming and credentials | Read-only named commands are implemented for the recognized Lichee adapter. Move target credentials out of code and add incremental output/cancellation before broader use. |
| High | Beken BK7252 adapter | Generic CP2102 entries no longer inherit Beken claims. Add a separate Beken adapter only after a vendor-supported handshake, wiring, voltage, boot mode, and recovery path are documented. |
| Medium | Device history | Store physical-device fingerprints separately from transient COM/interface names and show reconnect history and prior results. |
| Medium | Component test packs | Add versioned test packs for common sensors, cameras, radios, storage, displays, GPIO, I2C, SPI, UART, CAN, and accelerators. |
| Medium | CircuitPython runtime coverage | Generalize mounted-volume/runtime matching beyond the verified Feather USB identity and validate raw-REPL compatibility across current CircuitPython releases and additional board families. |
| Medium | External circuit fixtures | I2C adapter enumeration is safe; address scans require explicit action. SPI, UART, GPIO/analog, and SDIO need known pin maps plus protected fixture hardware because they cannot identify arbitrary attached circuits generically. |
| Medium | Hardware CI matrix | Run repeatable acceptance tests against real fixture boards; mocked tests cannot prove radio, camera, sensor, or electrical behavior. |
| Medium | Visual identification | Implement the photo/OCR evidence workflow described in `AGENT_AI_ROADMAP.md`; visual matches remain declared until confirmed. |
| Medium | Packaging | The source can run from the dedicated repository with a local virtual environment and React bundle. Signed releases/installers and an authenticated remote-deployment policy remain future work. |

## Engineering boundary

No generic host program can truthfully discover every component on every unmodified board. A component
must be exposed by USB, network, an operating system, a debug interface, or cooperative firmware.
The bench therefore uses progressive inspection: passive host evidence first, provider enrichment
second, compatible read-only adapters third, and explicitly approved active diagnostics last.
