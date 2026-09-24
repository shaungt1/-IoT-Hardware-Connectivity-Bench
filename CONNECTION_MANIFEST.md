# IoT Hardware Connectivity Bench Tool Manifest

This manifest records the adapters, discovery providers, and target-changing tools used by the
standalone bench. Detection is evidence-based: a COM port alone does not prove a board model,
sensor, camera, wireless radio, or operating system.

## Safety levels

| Level | Meaning |
| --- | --- |
| Passive | Non-mutating inventory; may read OS or USB descriptors but never claims or alters a target interface. |
| Read-only | May open a transport or send a non-mutating identity/status query. |
| Disruptive | May claim an interface, reset a connection, or pause a target. |
| Destructive | Can erase or flash target data and requires explicit user confirmation. |

## Active discovery stack

| Provider | Locked version | Safety | Purpose |
| --- | --- | --- | --- |
| PyUSB | `1.3.1` | Passive | Raw USB VID/PID, class, bus, address, and safe descriptor inventory |
| libusb-package | `1.0.30.0` | Passive | Bundled Windows libusb backend for PyUSB |
| psutil | `7.2.2` | Passive | Host network-interface state, addresses, link speed, and MTU |
| Zeroconf | `0.151.3` | Passive | Bounded, user-triggered HTTP/SSH/RTSP/MQTT service discovery |
| pySerial | `3.5` | Read-only by default | COM inventory and supported serial adapters |
| Bleak | `1.1.1` | Read-only | BLE advertisement scan and supported GATT verification |
| Paramiko | `3.5.1` | Read-only | Linux-board telemetry over an explicitly recognized USB network link |
| PlatformIO Core | `6.1.18` | Destructive when flashing | Existing ESP32 build and firmware upload workflow |
| Arduino CLI | `1.5.1` | Passive for board list; destructive for upload | Arduino USB identity, FQBN, core, build, and upload metadata |
| esptool | `5.4.0` | Destructive when flashing | Espressif identity, image, and flash operations |
| mpremote | `1.29.0` | Disruptive | MicroPython transport, filesystem, and runtime operations |
| pyOCD | `0.45.1` | Disruptive/destructive | CMSIS-DAP discovery, debug, memory, and flash operations |
| ltchiptool | `4.14.4` | Destructive when flashing | Beken and LibreTiny family detection and firmware operations |
| OpenOCD | PlatformIO-managed | Disruptive/destructive | SWD/JTAG identity, debug, and target operations through a compatible probe |
| BOSSA | PlatformIO-managed | Destructive when flashing | SAMD bootloader upload operations |
| dfu-util | PlatformIO-managed | Destructive when flashing | USB DFU identity and upload operations |
| FastAPI | `0.118.0` | N/A | Bench HTTP, WebSocket, and browser APIs |
| React + Vite | `19.1.1` + `7.1.7` | N/A | Stateful six-stage client sharing the FastAPI contract |

The live `/api/tools` registry reports installed and planned command-line tools at runtime rather
than preserving a stale count. Registered target families include Espressif, Nordic, SAMD/AVR, RP2040/RP2350,
STM32, Raspberry Pi, Beken/LibreTiny, Hailo, Rockchip, Allwinner, Linux I2C/USB, camera/media, and
signal analysis. Missing tools are not silently installed or invoked.

## Current verified hardware

| Identity | Transport | Verified state |
| --- | --- | --- |
| CP210x `10C4:EA60` -> ESP8266EX | COM11 USB serial | Bridge identity, ROM handshake, ESP8266EX, Wi-Fi capability, MAC, and 4 MB SPI flash verified without writing flash |
| Adafruit Feather M0 Express `239A:8023` | COM12 USB serial + `F:\` CIRCUITPY | ATSAMD21G18 identity, mounted storage, code/import/library inventory, 29 documented pins, runtime telemetry, and controlled I2C scan verified |
| Great Scott Gadgets HackRF One `1D50:6018` | COM5 USB serial | USB identity and device class verified; `hackrf_info` remains unavailable |
| Windows Bluetooth virtual COM ports | COM3 and COM4 | Listed as unresolved host serial interfaces, never promoted to microcontroller boards |
| Host USB peripherals | Passive USB identity | AudioBox, Corsair controller, Logitech keyboard/receiver/camera, Bluetooth radio, Insignia display adapter, Shure MV7, and mass-storage devices are separated from circuit targets |

The Lichee/PicoClaw adapter remains implemented, but no Lichee interface was present during the
2026-09-24 final audit. Addresses and availability are always treated as runtime facts.

## Bench API

| Endpoint | Safety | Result |
| --- | --- | --- |
| `GET /api/hardware` | Passive | Supported serial and USB-network hardware adapters |
| `GET /api/inventory/usb` | Passive | Raw normalized USB inventory |
| `GET /api/inventory/host` | Passive | Host network interfaces and addresses |
| `GET /api/tools` | Passive | Installed/planned tool registry with risk labels |
| `GET /api/metadata/providers` | Passive | Offline, local, and optional online metadata-provider readiness |
| `GET /api/arduino/boards` | Passive | Arduino CLI board matches and FQBN data |
| `POST /api/discovery/services` | Passive | Bounded local mDNS service scan |
| `POST /api/discovery/network` | Read-only | Private local neighbor inventory plus fixed-port service checks; deep mode is explicitly requested and capped to `/24` |
| `POST /api/hardware/select` | Passive/read-only | Selects and inventories generic devices; only opens transports for compatible adapters |
| `POST /api/device/inspect` | Passive/read-only | Normalized identity, evidence, components, capabilities, services, tests, and resources |
| `POST /api/device/model` | Local persistence | Saves an evidence-supported exact model selection without promoting components to verified |
| `POST /api/device/test` | Risk varies by definition | Runs only currently enabled tests; unsupported active probes remain locked |
| `POST /api/device/command` | Read-only | Named allowlisted diagnostics for a recognized authenticated operating-system adapter; never arbitrary shell text |
| `GET /api/device/operations` | Passive | Target-aware build, backup, and flash readiness with explicit limitations |
| `POST /api/operations/plan` | Passive | Creates a device-bound operation preview without executing it |
| `POST /api/operations/{id}/approve` | Local state | Issues a short-lived token bound to that plan and target |
| `POST /api/operations/{id}/execute` | Risk varies | Executes only the exact approved allowlisted operation with timeout and target lock |
| `GET /api/workspace` / `file` | Read-only | Lists and reads allowlisted UTF-8 project or mounted-device files |
| `POST /api/workspace/write-plan` | Local write after approval | Plans a hash-checked source/configuration file update |

## Adapter boundary

- Generic enumeration works for USB devices, COM ports, and USB network interfaces.
- Detailed capabilities require positive evidence from USB descriptors, a known adapter, firmware
  telemetry, a debug probe, a mounted filesystem, or an operating-system service.
- Missing storage or firmware cannot be inferred reliably from a disappearing COM port alone. The
  UI reports the observed state and keeps unsupported capabilities unknown.
- I2C/SPI/GPIO discovery belongs on the target board or a dedicated debug/test adapter; it is not
  possible through an arbitrary USB cable unless the target exposes a cooperating protocol.
- A CP2102 USB identity proves the USB-to-UART bridge only. The processor behind it remains unknown
  until cooperative firmware or a target-specific, electrically safe boot-ROM handshake responds.
- Flash, erase, reset, and debug operations remain separate from passive discovery and must require
  an explicit target selection and confirmation.

## Persistence and secrets

- `ai-api/data/iot.db` stores selected profiles and non-secret settings and is ignored by Git.
- Router passwords pass over the local USB adapter and are stored only in supported target NVS.
- Private credentials, backups, and hardware recovery images stay outside the tracked bench.
