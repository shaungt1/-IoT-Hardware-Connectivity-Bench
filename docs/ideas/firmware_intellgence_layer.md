Yes. What you want is a **firmware intelligence layer** sitting underneath the hardware graph you already built.

CMSIS-SVD and Zephyr DeviceTree help with the hardware side, but they do different things from firmware reverse engineering:

- **CMSIS-SVD** tells you what registers/peripherals *should exist* inside a known MCU.
- **Zephyr DeviceTree** tells you how the board and attached devices *should be wired/configured*.
- **Firmware analysis tools** tell you what the binary *actually contains, executes, initializes, accesses, and exposes*.

For your platform, I would add this pipeline:

```text
PHYSICAL DEVICE
      │
      ▼
Identify MCU / SoC
      │
      ▼
Acquire Firmware
      │
      ├── vendor firmware file
      ├── serial bootloader
      ├── SWD / JTAG
      ├── external SPI flash
      └── filesystem / update package
      │
      ▼
FIRMWARE CARVING
      │
      ├── bootloader
      ├── partition table
      ├── application image
      ├── RTOS/kernel
      ├── filesystem
      ├── device tree
      ├── libraries
      └── configuration/data
      │
      ▼
ARCHITECTURE ANALYSIS
      │
      ├── ARM
      ├── Xtensa
      ├── RISC-V
      ├── MIPS
      ├── AVR
      └── unknown/custom
      │
      ▼
DISASSEMBLY / DECOMPILATION
      │
      ▼
Functions / Drivers / Registers / Buses
      │
      ▼
Match against your hardware graph
```

That gives you the missing **software half of the digital twin**.

## The tools I would integrate

### **Ghidra — main reverse-engineering engine**

This would be my primary engine for your system.

Ghidra can disassemble, decompile, graph, analyze, emulate and script compiled binaries across many processor architectures. It also supports automated/headless operation, so you don't have to make somebody manually operate the Ghidra GUI. :chatgpt-content-reference{index="0"}

For example, your application could give Ghidra:

```text
firmware.bin
architecture = ARM Cortex-M4
base_address = 0x08000000
```

and get back:

```text
Functions: 1,842

reset_handler
system_init
spi_init
i2c_read
camera_start
ble_gap_init
uart_rx_handler
flash_write
```

You then place those in your graph:

```text
Firmware
   │
   ├── function: camera_start()
   │                 │
   │                 ▼
   │              I2C1
   │                 │
   │                 ▼
   │              OV5640
   │
   └── function: ble_gap_init()
                     │
                     ▼
                 BLE Controller
```

That gets extremely powerful when combined with your hardware discovery.

### Unknown Chinese/custom CPUs: **Ghidra SLEIGH**

This is especially relevant to what you asked.

Ghidra has a processor-description language called **SLEIGH**. It defines how the raw instruction bytes for a CPU translate into assembly and into Ghidra's intermediate representation. :chatgpt-content-reference{index="1"}

So if you encounter some obscure processor that Ghidra doesn't understand:

```text
Unknown MCU
AB32F103-X9
```

you can potentially add a processor specification rather than rewriting your whole reverse-engineering engine.

Ghidra itself documents extending processor support through SLEIGH. :chatgpt-content-reference{index="2"}

That's a very important capability for your application.

---

### **Binwalk — split firmware apart**

Binwalk should probably run **before Ghidra** for larger firmware packages.

It identifies and extracts embedded files and structures from firmware and can also use entropy analysis to help identify compressed or encrypted regions. The current Binwalk v3 is written in Rust and exposes integration capability for other Rust applications. :chatgpt-content-reference{index="3"}

Give it:

```text
router_firmware.bin
```

and conceptually you could end up with:

```text
Firmware Image
│
├── bootloader.bin
├── kernel
├── device-tree.dtb
├── squashfs
│   ├── /etc
│   ├── /bin
│   ├── /lib
│   └── /www
│
├── certificates
└── compressed data
```

That is exactly what you mean by mapping **firmware levels/layers**.

---

### **EMBA — automated firmware intelligence**

EMBA is especially interesting for your application because it already behaves somewhat like an analysis pipeline.

It can perform firmware extraction, static analysis, dynamic/emulated analysis, SBOM generation, and reporting. :chatgpt-content-reference{index="4"}

I would not necessarily expose its security-reporting UI.

Instead, consume its output and turn it into:

```text
Firmware Profile

OS
Linux 5.x

Architecture
ARMv7

Packages
BusyBox
OpenSSL
Dropbear
libcurl

Services
HTTP
SSH
mDNS

Filesystem
SquashFS

Interesting hardware references
/dev/i2c-0
/dev/spidev0.0
/dev/video0
/dev/ttyS0
```

That fits directly into what you've already built.

---

## Radare2 / Rizin

**radare2** gives you an extremely scriptable low-level binary analysis engine.

It can inspect, disassemble, modify, debug and emulate binaries, and it has `r2pipe` for controlling it programmatically. :chatgpt-content-reference{index="5"}

Where I would use it:

```text
Your React UI
      │
      ▼
Firmware Service
      │
      ▼
r2pipe
      │
      ▼
radare2
```

Then your backend can request:

```text
architecture
entry point
functions
symbols
strings
cross references
call graph
sections
entropy
```

and return structured JSON.

Kali's current reverse-engineering toolset includes radare2, Rizin, Cutter and Ghidra integrations. :chatgpt-content-reference{index="6"}

---

# And yes: Kali actually has a hardware-hacking toolset

There is literally a Kali metapackage called:

```bash
kali-tools-hardware
```

Kali currently lists the hardware toolset as containing tools including:

```text
binwalk
flashrom
OpenOCD
minicom
cutecom
QEMU
radare2
Rizin/Cutter
rz-ghidra
``` :chatgpt-content-reference{index="7"}


So your intuition was correct.

But I wouldn't make Kali itself a dependency.

I would treat those individual programs as **backend engines**.

---

# The hardware extraction side

Before reverse engineering firmware, sometimes you first need to obtain it.

## **OpenOCD**

This is extremely valuable for your application.

OpenOCD talks through **JTAG/SWD** to chips and supports debugging, in-system programming and boundary scan. It supports ARM and additional architectures including RISC-V, MIPS/EJTAG, ARC, OpenRISC and others. :chatgpt-content-reference{index="8"}

Conceptually:

```text
UNKNOWN BOARD

     ↓

Find test pads

TCK
TMS
TDI
TDO

     ↓

OpenOCD

     ↓

CPU detected
Debug interface detected
Memory map
Flash controller
RAM
registers
```

That gives your application another route into a device besides USB.

---

# **flashrom**

For devices containing external flash:

```text
SPI NOR
EEPROM
BIOS flash
firmware flash
```

flashrom is exactly the sort of tool you want.

Your system could identify the flash chip and, where supported and authorized, read its contents into your firmware-analysis pipeline.

So:

```text
Unknown board
      │
      ▼
SPI Flash detected
      │
      ▼
Read image
      │
      ▼
Binwalk
      │
      ▼
Firmware structure
      │
      ▼
Ghidra
```

That gives you the ability to understand devices whose firmware isn't conveniently exposed through USB.

---

# **sigrok + PulseView**

This is another one I'd strongly add.

Sometimes firmware isn't accessible, but the **signals tell you what the device is doing**.

A logic analyzer + sigrok can decode:

```text
UART
SPI
I²C
I²S
CAN
1-Wire
JTAG
and many other protocols
```

So imagine your UI:

```text
PIN 18
Unknown

PIN 19
Unknown

PIN 20
Unknown
```

You attach a logic analyzer.

Then your analyzer sees:

```text
PIN 18 → repetitive clock
PIN 19 → bidirectional data
Address 0x3C detected
```

Your graph can infer:

```text
Likely I²C

SCL → Pin 18
SDA → Pin 19

Device:
0x3C

Possible device:
SSD1306 display
Confidence: 81%
```

That's exactly the kind of deeper hardware crawling your system needs.

---

# Unknown chips: use evidence fusion

For generic chips where the markings or documentation are useless, don't depend on one tool.

Build a fingerprint.

```text
UNKNOWN CHIP
   │
   ├── package: QFN-48
   ├── voltage: 3.3 V
   ├── USB VID/PID
   ├── JTAG IDCODE
   ├── boot ROM response
   ├── UART startup strings
   ├── SPI flash contents
   ├── instruction patterns
   ├── entropy
   ├── peripheral signatures
   └── clock characteristics
```

Then compare all those observations.

Your application could say:

```text
Processor candidate

Bouffalo BL602        71%
ESP8266               16%
WinnerMicro W600       8%
Unknown                5%
```

That's a much more realistic way to attack anonymous hardware.

---

# The other project I think is very relevant to you: **Avatar²**

Avatar² is an open-source framework specifically designed around **dynamic firmware analysis of embedded devices**. :chatgpt-content-reference{index="9"}

The interesting part is its concept of multiple targets.

You can bridge:

```text
REAL HARDWARE
     +
EMULATOR
     +
DEBUGGER
```

For example:

```text
CPU execution
      ↓
QEMU

Unknown peripheral access
      ↓
Forward to

REAL BOARD
```

That's called hardware-in-the-loop style firmware analysis.

For what you're building, that's extremely interesting because eventually you could have:

```text
YOUR DIGITAL TWIN

CPU       = emulated
RAM       = emulated
GPIO      = emulated
Camera    = real
BLE       = real
Sensor    = virtual
```

That is almost exactly where your project is headed.

---

# I would model firmware as layers

Your UI should not just say:

> Firmware.bin

Instead:

```text
DEVICE SOFTWARE STACK
────────────────────────────────

L0  Boot ROM
    └─ immutable manufacturer code

L1  First-stage bootloader
    └─ ROM loader / SPL

L2  Second-stage bootloader
    └─ U-Boot / MCU bootloader

L3  Hardware abstraction
    ├─ startup code
    ├─ BSP
    ├─ HAL
    └─ device drivers

L4  Runtime
    ├─ bare metal
    ├─ FreeRTOS
    ├─ Zephyr
    └─ Linux

L5  Middleware
    ├─ TCP/IP
    ├─ BLE stack
    ├─ USB stack
    ├─ filesystem
    └─ crypto

L6  Application
    ├─ sensors
    ├─ camera control
    ├─ UI
    └─ device logic

L7  Configuration/Data
    ├─ calibration
    ├─ certificates
    ├─ partitions
    └─ persistent settings
```

Then map binaries into those layers.

For a microcontroller:

```text
flash.bin

0x00000000
    bootloader

0x00008000
    partition table

0x00010000
    application

0x00390000
    filesystem

0x003F0000
    calibration/NVS
```

Your user could literally click each layer.

---

# Then correlate the firmware with CMSIS-SVD

This is where **CMSIS-SVD becomes much more valuable**.

Suppose Ghidra finds this:

```text
write 0x40013000
```

Your SVD database says:

```text
0x40013000 = SPI1
```

Then Ghidra finds:

```text
0x40013000 + 0x00
```

SVD says:

```text
SPI1_CR1
```

Now instead of your UI showing:

```text
*(0x40013000) |= 0x40
```

you can show:

```text
Firmware Function:
camera_spi_init()

Accesses:
SPI1

Register:
SPI1_CR1

Operation:
Enable SPI peripheral
```

That's the bridge between **binary reverse engineering and understandable hardware behavior**.

I would make that a central feature.

---

# Your end-state architecture

```text
                         PHYSICAL DEVICE
                               │
               ┌───────────────┼───────────────┐
               │               │               │
              USB          SWD/JTAG          SPI Flash
               │               │               │
               └───────────────┼───────────────┘
                               ▼
                     ACQUISITION LAYER
                               │
                    OpenOCD / flashrom
                               │
                               ▼
                       FIRMWARE IMAGE
                               │
                     ┌─────────┴────────┐
                     ▼                  ▼
                  Binwalk             EMBA
                structure           profiling
                     │                  │
                     └─────────┬────────┘
                               ▼
                  Ghidra / radare2 / Rizin
                               │
                Functions / code / call graph
                               │
                               ▼
                 CMSIS-SVD CORRELATION
                               │
              registers → peripherals → pins
                               │
                               ▼
                    YOUR HARDWARE GRAPH
                               │
              ┌────────────────┼───────────────┐
              ▼                ▼               ▼
            Renode          Avatar²         ngspice
           emulate        HW-in-loop       electrical
```

### What I'd add to your project first

If you want the shortest practical path, I would add them in this order:

1. **Binwalk v3** — automatically break firmware images into their internal layers.
2. **Ghidra headless** — decompile/disassemble and generate the software graph.
3. **CMSIS-SVD correlation** — translate raw register accesses into meaningful peripherals.
4. **OpenOCD + probe-rs** — obtain/debug firmware through JTAG/SWD on supported targets.
5. **sigrok/PulseView** — infer unknown buses and devices from live electrical traffic.
6. **EMBA** — deeper automated analysis for Linux/router/camera/IoT firmware.
7. **Avatar² + Renode/QEMU** — hybrid real/virtual execution once you reach the digital-twin stage.

That would give you something very close to what you're describing: **plug in an unknown board → identify it → map its physical hardware → extract its firmware → split firmware layers → reverse engineer the binaries → correlate software accesses with actual registers/buses/pins → test it → emulate it → then build against it.**