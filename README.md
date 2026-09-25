# IoT Hardware Connectivity Bench

This folder is an isolated, reusable, cross-vendor hardware discovery and acceptance-test system.
Passive USB, serial, host-network, and local-service discovery work without assuming a board model.
Evidence providers identify likely boards and components; explicit device adapters add verified
telemetry and control without sending arbitrary bytes to unknown hardware.

Windows hardware discovery lists both serial ports and USB-network devices. The first Linux board
adapter recognizes the LicheeRV Nano + PicoClaw USB identity (`359F:2120`), prefers its NCM link,
checks SSH and the PicoClaw web service, and reads basic device/camera telemetry over SSH. Other
serial boards still appear and can be classified from USB/provider evidence even when no compatible
runtime protocol is available. CircuitPython boards can additionally expose mounted-volume metadata,
runtime telemetry, board pin names, and a controlled multi-sample I2C scan through a runtime adapter.
The adapter pauses and soft-reloads the existing program but never writes the board filesystem.

## What it proves

- Passive raw USB VID/PID, class, descriptor, bus, and address inventory
- Host network-interface inventory and bounded local mDNS service discovery
- Private local-network device discovery with clickable HTTP services and an explicit `/24` deep mode
- Installed versus planned tool capabilities with explicit safety levels
- Windows USB serial/JTAG detection and framed telemetry
- ESP32-S3 camera initialization and live JPEG delivery
- Exact authenticated Seeed XIAO ESP32-S3 Sense identity and 14-pad header mapping
- BLE advertising, service UUID visibility, and host-measured RSSI
- Wi-Fi access-point operation, optional router connection, IP address, and RSSI
- Browser delivery through a FastAPI hardware bridge
- Separate broadcast, incoming-client, and outgoing/read state for BLE and Wi-Fi
- Saved USB, BLE, and Wi-Fi profiles without host-side password storage
- A collapsible event console and allowlisted read-only diagnostics for recognized Linux targets
- A buildable, opt-in Nano 33 BLE Sense diagnostic sketch with individual sensor commands
- A CircuitPython adapter that inventories `CIRCUITPY`, source imports, libraries, runtime pins,
  heap/CPU telemetry, and stable I2C responses without replacing the installed program
- A machine-readable `/api/contract` with versioned evidence, prototype, and test-pack schemas,
  compatibility policy, and explicit local-control/MCP/hosted-release boundaries
- The complete installed `@wokwi/elements` visual set: 50 package parts plus the exact XIAO Sense
  visual, with package terminal parity and unresolved electrical semantics kept visibly unknown

The camera travels over USB to the local dashboard so it works on this workstation without a Wi-Fi
adapter. The firmware also exposes a direct Wi-Fi camera API:

| Endpoint | Purpose |
| --- | --- |
| `http://192.168.91.1/status` | JSON device telemetry |
| `http://192.168.91.1/capture.jpg` | Single JPEG frame |
| `http://192.168.91.1/stream` | MJPEG stream |

The board can advertise a direct Wi-Fi network named `XIAO-ESP32S3-SENSE-<chip suffix>`. A fresh firmware
install keeps that access point off until an 8-63 character password is configured over the local USB
control link. There is no fixed credential in source control and no username or user account. The dashboard can change the shared BLE/Wi-Fi
name without changing an existing password, or replace the direct Wi-Fi password.
The dashboard can securely send router credentials over the local USB link; credentials are stored in
the ESP32's preferences and are never written to the repository or API logs.

The XIAO ESP32-S3 supports 2.4 GHz Wi-Fi only. It cannot discover or join 5 GHz networks. The
external U.FL antenna is shared by Wi-Fi and BLE and must be attached for reliable RF testing.

For phone-side BLE validation, use a BLE scanner such as nRF Connect for Mobile and scan for
`XIAO-ESP32S3-SENSE-<chip suffix>`. Connect to the advertised GATT service and read the status
characteristic. A phone's general Bluetooth settings may omit custom BLE peripherals even while
they are advertising correctly.

## Layout

```text
IoT-Hardware-Connect-Bench/
|-- firmware/    PlatformIO Arduino diagnostic firmware
|   `-- nano33ble-sense-diagnostics/  Opt-in sensor acceptance image (never auto-flashed)
|-- ai-api/      FastAPI USB/BLE bridge and tests
|-- web/         Dependency-free browser dashboard
|-- react-app/   Vite + React stateful client using the same FastAPI contract
|-- CONNECTION_MANIFEST.md  Connection libraries, protocols, and verification state
|-- start.ps1    Windows command surface
`-- start.sh     Bash command surface
```

The production vision, researched architecture, dependency-ordered delivery plan, implementation
backlog, and recurring QA gates are indexed in [`docs/README.md`](docs/README.md). The existing
[`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) remains the live record of verified behavior and open gaps.

## Windows commands

```powershell
.\start.ps1 setup
.\start.ps1 test
.\start.ps1 firmware-build
.\start.ps1 firmware-flash -Port COM6
.\start.ps1 sensor-firmware-build # Build only; never uploads automatically
.\start.ps1 react
.\start.ps1 react -Port COM6 # Optional preferred serial port
.\start.ps1 html             # Legacy standalone client
.\start.ps1 both             # React plus legacy standalone client
.\start.ps1 status
.\start.ps1 stop
```

Git Bash exposes the same modes. Running `./start.sh` without an option opens an interactive menu and
does not start anything until `1`, `2`, or `3` is selected:

```bash
./start.sh 1       # React plus API/WebSocket
./start.sh 2       # Legacy HTML plus API/WebSocket
./start.sh 3       # Both clients with one API/WebSocket backend
./start.sh status
./start.sh stop
```

Open `http://127.0.0.1:5173` for the React client. Port `8765` is API-only by default; the legacy
HTML source remains in `web/` but is not served. The React dev server proxies the API and WebSockets
to port `8765`.

## Evidence and safety model

Every component/capability is labeled as `verified`, `detected`, `declared`, `expected`, or
`unavailable`. USB descriptors and metadata catalogs cannot prove that a sensor is populated or
working. Verification requires a compatible runtime, authenticated Linux inspection, debug probe,
or an explicitly approved diagnostic firmware upload.

The Nano diagnostic image is built with:

```powershell
.\.tool-venv\Scripts\platformio.exe run -d .\firmware\nano33ble-sense-diagnostics
```

It emits `BENCH_READY` before the host will send a named `TEST <sensor>` command. Building does not
modify the board. Uploading replaces the existing sketch and is intentionally not automatic.

The explicit upload command is:

```powershell
.\.tool-venv\Scripts\platformio.exe run -d .\firmware\nano33ble-sense-diagnostics --target upload --upload-port COM10
```

Once installed, the bench verifies the serial handshake and enables live tests for each onboard
sensor plus the exposed external I2C bus.

External terminals have physical limits the UI now states directly. I2C can enumerate addresses
only when firmware, Linux, or a debug adapter exposes the controller. SPI has no general enumeration
protocol; UART requires voltage/baud/protocol knowledge; GPIO and analog pads cannot identify what is
wired to them. Unknown pins are never driven by a discovery scan.

The Feather M0 Express adapter currently verifies its CircuitPython runtime and 21 runtime-exposed
pin names. Its board profile documents eight additional power/debug/control terminals. I2C discovery
uses three samples: only addresses present in every sample appear as attached peripherals, while
transient responses are retained as noise evidence rather than promoted to sensor identities.

Tools are also classified by maximum operational risk: `passive`, `read-only`, `disruptive`, or
`destructive`. Unknown serial devices are never opened automatically. Flash, erase, GPIO, bus-scan,
and brute-force operations remain disabled until a target adapter defines a safe command.

## Test-only protocol

USB messages use a 13-byte little-endian header followed by the payload:

```text
IOTB | type:u8 | length:u32 | sequence:u32 | payload
```

Packet type `1` is UTF-8 JSON telemetry and type `2` is a JPEG frame. Host commands are newline
terminated: `STREAM ON`, `STREAM OFF`, `STATUS`, `BLE ON`, `BLE OFF`, `WIFI AP ON`,
`WIFI AP OFF`, `WIFI SCAN`, `WIFI<TAB>ssid<TAB>password`,
`WIFI ONCE<TAB>ssid<TAB>password`, `NAME<TAB>name`, and
`DEVICE<TAB>name<TAB>new-direct-wifi-password`.

The dashboard stores the selected serial port, operation receipts, and non-secret connection profile metadata in
`ai-api/data/iot.db`. The database is local and ignored by Git. Router passwords are never
stored by the host; the firmware writes them directly to the ESP32 preferences over USB.

The BLE test service is `8f7a0001-6e7d-4a44-9f9d-10a1b2c3d401`; its read/notify status
characteristic is `8f7a0002-6e7d-4a44-9f9d-10a1b2c3d401`. These UUIDs must not be copied into the
mobile app as the production contract.

Factory recovery images and other private hardware material remain outside the tracked bench.

## Firmware workspace and operation safety

The React client includes a target-aware **Firmware & files** step. It can read and edit UTF-8
source/configuration files only inside the repository's `firmware/` folder or an explicitly detected
mounted device filesystem. Updates use content hashes to reject stale edits. PlatformIO builds run
locally; uploads, target resets, flash backups, and file writes require a short-lived approval bound
to the selected device. Every planned, approved, completed, or failed operation is stored as an audit
receipt. No flash operation runs during setup, test, discovery, or the `all` command.

Local builds expose bounded real process output through the live status WebSocket and can be cancelled
from the running operation button. Cancellation terminates the child process and records a `cancelled`
receipt instead of presenting a generic failure.

The repository contains optimized ESP32-S3 camera firmware source, but the historical workspace did
not retain a flash receipt proving when or whether that exact revision was uploaded. The new audit
trail records that evidence for future uploads rather than inferring it from source files.
