# Agent AI Roadmap

## Product goal

Turn the bench into a local-first hardware evidence system: discover every host-visible interface,
identify the selected board in layers, expose safe tests for verified capabilities, and preserve a
traceable record of what was observed versus inferred. AI can assist identification, but never
promotes a guess to verified hardware without matching protocol, descriptor, debug, runtime, or
user-confirmed visual evidence.

## Identity layers

1. **Host interface** - USB, serial, PCIe, network, storage, camera/media, HDMI/display, BLE, Wi-Fi.
2. **Transport bridge** - CP210x, CH34x, FTDI, CMSIS-DAP, J-Link, ST-Link, USB network gadget.
3. **Target processor** - ROM/debug/runtime handshake for Espressif, Nordic, SAMD/AVR, RP2040/2350,
   STM32, RISC-V, Raspberry Pi, NVIDIA Jetson, Hailo, Beken/LibreTiny, Rockchip, and Allwinner.
4. **Module and carrier board** - board definition, pin map, regulators, flash, radios, connectors.
5. **Runtime** - firmware, bootloader, Linux/RTOS, mounted filesystems, services, drivers.
6. **Attached circuits** - only through an exposed controller, known-safe fixture, or cooperative
   diagnostic firmware. I2C addresses are candidates; SPI/GPIO cannot be universally enumerated.

## Discovery and test providers

| Interface family | Identification tools | Safe verification target |
| --- | --- | --- |
| USB and Windows PnP | PyUSB/libusb, SetupAPI/PowerShell PnP | Descriptor, class, presence, driver |
| UART and boot ROMs | pySerial, esptool, vendor ROM protocols | Processor, revision, MAC, flash identity |
| JTAG and SWD | OpenOCD, pyOCD, probe-rs, CMSIS-DAP | Core/target ID and read-only memory map |
| Bootloaders | DFU, BOSSA, AVRDUDE, picotool, nrfutil, rpiboot | Boot mode and target identity before writes |
| Linux boards | USB networking, SSH, sysfs, device tree, udev | SoC, OS, services, I2C/SPI/media devices |
| PCIe accelerators | Windows PnP, lspci, nvidia-smi, HailoRT | Vendor/device ID, firmware, health, topology |
| I2C | Runtime adapter or protected USB fixture | Stable address scan, then part-specific signature |
| SPI, SDIO, GPIO, ADC, PWM | Board map plus firmware/debug fixture | Named, voltage-safe, allowlisted tests only |
| Cameras and audio | Media Foundation/V4L2, FFprobe | Format, frames, rate, sample stream |
| BLE and Wi-Fi | Bleak, host radio APIs, device telemetry | Advertisement, services, RSSI, association, traffic |
| SDR and RF | hackrf tools, SoapySDR, sigrok | Device identity, firmware, bounded receive test |

## Delivery phases

### 1. Evidence engine and common hardware

- Finish layered adapters and a stable physical-device fingerprint independent of COM number.
- Add read-only identification for HackRF, NVIDIA, Hailo, Raspberry Pi USB boot, Nordic, RP2040,
  STM32, SAMD/AVR, and common UART bridges.
- Keep host peripherals visible but clearly separate from inspectable circuit targets.
- Add cancellation, per-target locks, audit events, and approval tokens for disruptive operations.

### 2. Board definitions and attached circuits

- Import normalized board definitions from Arduino CLI, PlatformIO, CircuitPython, Zephyr, vendor
  device trees, and maintained local manifests.
- Add pin-map views with voltage, boot-strap, reserved, power, debug, and alternate-function data.
- Add versioned diagnostic packs for common sensors, displays, cameras, storage, radios, and motors.
- Support protected USB I2C/SPI/UART/GPIO fixtures for boards without cooperative firmware.

### 3. Visual identification agent

- Capture or upload top/bottom board photographs from the browser.
- Detect package markings, connector labels, pin legends, board revision, and component placement.
- Match OCR/vision candidates against local catalogs plus optional DigiKey, Nexar, vendor, and
  datasheet sources; retain image hashes, citations, confidence, and user confirmation.
- Merge visual declarations with protocol evidence without overwriting contradictory live evidence.

### 4. Programming and recovery

- Add explicit build, flash, verify, backup, restore, SD-card imaging, and recovery workflows.
- Require device-specific manifests, power/boot instructions, artifact hashes, and confirmation.
- Never choose a firmware image or write target from a visual guess alone.

### 5. Agent and IDE integration

- Expose the evidence graph and allowlisted actions through a local API/MCP service.
- Add a VS Code device tree, test actions, logs, and project-to-board association.
- Let agents explain results and propose commands; the same safety gates apply with or without AI.

## Non-negotiable boundary

No software can infer every passive component or wire by talking only to a USB bridge. Components
must expose evidence through a descriptor, protocol, operating system, debug path, measurable bus,
cooperative firmware, protected test fixture, or confirmed visual inspection. The bench should make
that boundary visible rather than fabricating a complete circuit inventory.
