Yes. I understand exactly what you're describing, and the key is that this is **two separate systems joined by one shared hardware graph**.

**Part 1 is identification and tracing.** You plug something into the computer. The system progressively determines what the host can see, what controller/SoC/bridge is present, what runtime exists, what pins/buses/connectors exist, what onboard devices are expected or actually detected, and—where the hardware exposes enough evidence—what is attached to those buses and pins.

**Part 2 is projection and prototyping.** We take that hardware graph and automatically turn it into an interactive 2D prototype. Nothing needs to be redrawn from scratch. The board you just discovered appears with its ports and pins already mapped. Then you can add an ESP, LiDAR, resistor, capacitor, camera, M.2 device, LED strip, sensor, another controller, etc., wire them together, simulate them, and optionally bind those same virtual connections back to real physical hardware.

That exact combination—**automatic physical discovery → complete hardware graph → automatically generated interactive breadboard → simulation → live physical control**—I do not know of a single open-source product that already does the whole thing.

There are, however, several projects that already solve large chunks of it. We can combine them instead of rebuilding those chunks.

# Part 1 — Identification and tracing

This part should not be thought of as simply “scan the COM port.” COM/USB is just the first doorway.

The discovery engine should progressively dig deeper depending on what access the target gives us.

For a simple serial controller, we might begin with USB VID/PID, interface type, USB bridge identity, serial descriptors and boot messages. Then, if the processor supports a known ROM protocol, we can interrogate that. An ESP, for example, exposes substantially more information through its ROM loader than a generic serial bridge does.

When debug access exists, **probe-rs** and **OpenOCD** become extremely useful. probe-rs can interact with ARM, RISC-V and some Xtensa targets through SWD/JTAG, inspect memory, flash devices, reset/halt cores, and work through several common probes. :chatgpt-content-reference{index="0"} OpenOCD has extremely broad support for JTAG/SWD adapters and targets including ARM, ESP32, RISC-V, RP2040, Nordic and STM32 families. :chatgpt-content-reference{index="1"}

For a Linux-capable device such as a Raspberry Pi, Rockchip board, Jetson or Lichee board, we can go significantly further because the operating system can expose the hardware tree itself. **DeviceTree** is especially useful here because its purpose is literally to describe hardware hierarchically. Zephyr's DeviceTree system describes available hardware and its initial configuration; its bindings add semantic information about buses, properties, GPIOs, SPI devices, sensors and other peripherals. :chatgpt-content-reference{index="2"}

This means the identification side should ingest things such as:

USB/PnP evidence, serial/ROM probes, SWD/JTAG, operating-system information, DeviceTree, CMSIS-SVD/CMSIS-Pack, PlatformIO board definitions, vendor SDKs, Arduino board data, firmware/configuration files and known board databases.

That data becomes one **Hardware Evidence Graph**.

Conceptually:

```text
Physical Device
      │
      ├── USB interface
      │     └── CP2102 bridge
      │
      ├── Processor
      │     └── ESP32-S3
      │
      ├── Memory
      │     ├── SPI flash
      │     └── PSRAM
      │
      ├── I2C0
      │     ├── SDA → GPIO5
      │     └── SCL → GPIO6
      │
      ├── Camera interface
      │     └── OV5640
      │
      └── Header A
            ├── GPIO7
            ├── GPIO8
            └── 3V3
```

Every relationship also has evidence:

```text
verified
detected
declared
expected
inferred
unknown
```

That matters because there is a physical limitation we cannot software our way around.

A COM port cannot universally reveal every resistor, capacitor, PCB trace or passive component sitting behind the processor.

I²C is relatively discoverable because devices have addresses and commonly have identifiable registers.

SPI has **no universal enumeration mechanism**.

A resistor connected to a GPIO has no identity packet that says “I am 4.7 kΩ.”

Therefore, for the deepest trace we progressively add other evidence sources:

```text
device firmware/runtime
debug access
bus probing
known board definitions
logic analyzer
electrical test fixture
schematic/BOM
board image/OCR
user confirmation
```

That isn't a weakness in your concept. It is simply how the system knows when it has reached the physical limit of what can be determined automatically.

For signal tracing, **sigrok/libsigrokdecode** is particularly useful. It gives us an open ecosystem of protocol decoders that can interpret captured traffic instead of us implementing every UART/I²C/SPI decoder ourselves. :chatgpt-content-reference{index="3"}

So Part 1 becomes much more than device identification.

It becomes:

**Discover → Identify → Decompose → Trace → Verify → Build Hardware Graph**

---

# Part 2 — Automatically turn that graph into the prototype

This is where I think we have some very useful existing technology.

The closest projects are:

| Technology | What I would borrow |
|---|---|
| **Wokwi Boards** | Realistic board SVG + exact pin coordinates. A custom board uses `board.svg` and `board.json`, and Wokwi can connect external parts to those pins and simulate the board. :chatgpt-content-reference{index="4"} |
| **Wokwi Elements** | Browser-native visual electronic components. MIT licensed. They intentionally contain presentation only, which is actually useful because we can provide our own runtime underneath. :chatgpt-content-reference{index="5"} |
| **Fritzing Parts** | Huge breadboard-style asset source. Each part combines `.fzp` metadata with SVG graphics, including breadboard graphics. :chatgpt-content-reference{index="6"} |
| **tscircuit / Circuit JSON** | Very interesting as the underlying structured circuit representation. It is React/TypeScript native, MIT licensed, has components, pins, traces, browser viewers, routing, checking and a registry. :chatgpt-content-reference{index="7"} |
| **CircuitJS** | Browser-native electrical simulation for ordinary circuitry. :chatgpt-content-reference{index="8"} |
| **PICSimLab** | Development-board emulation plus attachable LEDs, displays, switches, shields and other simulated peripherals. :chatgpt-content-reference{index="9"} |
| **SimulIDE** | Simple real-time circuitry + PIC/AVR/Arduino simulation. Useful architectural source, although not the final web UI. :chatgpt-content-reference{index="10"} |
| **Renode** | Deeper firmware/processor/peripheral emulation where we need a real CPU executing firmware rather than a simple behavioral model. |
| **ngspice** | Serious voltage/current/transistor/capacitor/analog simulation underneath the visual layer. |

The one I would now investigate particularly hard is **tscircuit**.

It didn't exist in this mature form when a lot of traditional EDA approaches were designed. It calls itself essentially “React for Electronics.” Its core converts TypeScript/React circuits into an open **Circuit JSON** representation, and its ecosystem already contains separate schematic viewers, PCB viewers, auto-layout, routing, connectivity tools and validity/design-rule checks. :chatgpt-content-reference{index="11"}

Circuit JSON itself is described as a low-level open representation of electronic circuits, and the ecosystem already includes conversion to KiCad and connectivity/routing tooling. :chatgpt-content-reference{index="12"}

That could potentially save us from inventing a large portion of our internal circuit schema.

I would **not** replace your discovery graph with Circuit JSON. They describe different things.

I'd do:

```text
Hardware Evidence Graph
        │
        │ discovered physical truth
        ▼
Projection / Translation Layer
        │
        ▼
Prototype Circuit Graph / Circuit JSON
        │
        ├── visual renderer
        ├── simulation
        ├── circuit rules
        └── live hardware bindings
```

That distinction is powerful.

The Hardware Graph says:

> This ESP32-S3 really exists on COM7 and GPIO5 is physically exposed.

The Prototype Graph says:

> GPIO5 is connected to this virtual 4.7 kΩ resistor and the SDA pin of this sensor.

---

# What automatically happens when you open Prototype

Suppose Part 1 discovers:

```text
Raspberry Pi Zero
    40-pin header

ESP32
    GPIO header

BME280
    I2C device

Camera
    CSI

LED
```

The prototype service receives the Hardware Graph.

It searches the visual component resolver.

For the Pi:

```text
Wokwi board?
    ↓
Fritzing part?
    ↓
other imported component library?
```

If one exists, use it.

If not, create the simplified generated version we discussed.

Something like:

```text
┌───────────────────────────────┐
│ Raspberry Pi Zero             │
│                               │
│ BCM2710                       │
│ Wi-Fi                         │
│ CSI                           │
│ USB                           │
│                               │
● 3V3                        5V ●
● GPIO2                    GPIO3 ●
● GPIO4                      GND ●
● GPIO17                  GPIO27 ●
...
└───────────────────────────────┘
```

Every pin is still a real port.

The ESP appears alongside it.

The detected wire relationships are rendered automatically.

The sensor appears.

The camera appears.

The user didn't draw any of it.

That is the critical difference between your tool and ordinary CAD.

**CAD starts with an empty page.**

**Your Prototype Bench starts with reality.**

---

# Then the user extends reality

After the physical topology is projected, you can drag something new from the library.

Perhaps:

```text
VL53L1X LiDAR
```

Drop it onto the canvas.

Its record already knows:

```text
VCC
GND
SDA
SCL
XSHUT
GPIO1
```

You drag SDA to the Pi or ESP.

The underlying connection becomes:

```text
connect(
    esp32.GPIO5,
    lidar.SDA
)
```

The visible line is simply the rendering.

Then the rules engine evaluates it.

It knows:

- voltage
- direction
- bus compatibility
- pull-up requirements
- current limits
- addresses
- pin capabilities.

If it needs pull-ups:

> I²C SDA/SCL have no pull-up path.

Then you can add the resistors.

Click the resistor:

```text
Resistance        4.7 kΩ
Tolerance         5%
Power             0.25 W
Package           generic
```

and change it.

That parameter immediately feeds the simulation model.

---

# The two views you described make complete sense

I would absolutely have:

**Physical View**

The pretty breadboard-style version.

```text
[Pi-looking SVG]──wires──[ESP-looking SVG]
        │
      sensor
```

and:

**Logical / Information View**

```text
┌ ESP32-S3 ─────────────────────────┐
│ MCU        ESP32-S3               │
│ Flash      8 MB                   │
│ PSRAM      8 MB                   │
│ Wi-Fi      Present                │
│ BLE        Present                │
│ Camera     OV5640                  │
│                                   │
│ GPIO / Interfaces                 │
│ ● 3V3                             │
│ ● GND                             │
│ ● GPIO5 / SDA                     │
│ ● GPIO6 / SCL                     │
│ ● GPIO7                           │
└───────────────────────────────────┘
```

Same device.

Same pin IDs.

Same wires.

Same physical bindings.

Only the renderer changed.

---

# Wokwi is probably the closest finished experience

From a user-experience standpoint, **Wokwi is probably closest to Part 2**.

It already lets somebody put boards and peripherals on a browser canvas, wire pins, execute firmware and simulate devices. Its custom-board format even lets a user load a directory containing a board SVG and JSON definition, then attach components to the board pins and run simulation. :chatgpt-content-reference{index="13"}

But there are two major differences.

Wokwi does **not** begin by discovering an arbitrary real board attached to your computer and constructing the project from observed hardware.

And the complete Wokwi hosted simulator is not simply an open-source package that we can fork and turn into your application.

So we borrow the open pieces and concepts rather than trying to turn Wokwi itself into the product.

---

# Fritzing is probably the closest visual library

Fritzing solves another large part of the problem extremely well.

Its breadboard view is the kind of visual presentation you're describing, and its part format already separates metadata from SVG representations. Some components—resistors, pin headers, generic DIPs—are even generated dynamically rather than requiring an individual static asset. :chatgpt-content-reference{index="14"}

That last part is especially relevant.

It means your generic fallback component system can follow the same philosophy:

```text
Resistor
Capacitor
LED
DIP
Header
Connector
Generic MCU
Generic module
```

generated parametrically.

You do not need five thousand resistor SVG files.

---

# PICSimLab is worth studying carefully too

PICSimLab is interesting because its goal is literally to emulate development boards and attach “spare parts” to them. Its supported simulation engines include several MCU backends, and its simulated peripherals include basic LEDs/buttons and more complex things such as displays and Ethernet hardware. :chatgpt-content-reference{index="15"}

It's desktop-oriented rather than your desired React web architecture, but its **runtime model** is valuable to study.

Wokwi gives us inspiration for the browser.

PICSimLab gives us inspiration for the virtual hardware laboratory.

---

# tscircuit may save us a surprising amount of work

This is probably the biggest addition to the previous architecture discussion.

tscircuit already has:

```text
components
ports
pins
traces
Circuit JSON
connectivity maps
design checks
schematic routing
auto-layout
React rendering
browser evaluation
component registry
KiCad conversion
```

Its core is React-based and emits Circuit JSON. :chatgpt-content-reference{index="16"}

It even has a dedicated project for converting KiCad designs **into** Circuit JSON and supports component ports/pins, wires, traces, junctions and net mappings. :chatgpt-content-reference{index="17"}

So I wouldn't blindly build our entire circuit data model before evaluating whether **Circuit JSON can be our Prototype Graph interchange format**.

Your additional hardware-specific fields could live beside it:

```text
physicalDeviceId
evidenceStatus
runtimeBinding
hardwareCapability
simulationBinding
physicalPinId
liveState
```

That may be much smarter than inventing the whole netlist/circuit representation ourselves.

---

# What I would actually combine for your system

So if this were my build, I would now define it as:

```text
PART 1 — PHYSICAL DISCOVERY
────────────────────────────────────────

USB / COM / network
       ↓
PyUSB / libusb / pySerial
       ↓
ROM / runtime / OS probes
       ↓
OpenOCD / probe-rs / vendor tools
       ↓
DeviceTree / SVD / PlatformIO / SDK metadata
       ↓
I2C / targeted SPI / UART probes
       ↓
sigrok / logic analysis when needed
       ↓
visual / schematic / BOM evidence when needed
       ↓
HARDWARE EVIDENCE GRAPH


                 ↓ translation ↓


PART 2 — PROTOTYPE
────────────────────────────────────────

Prototype Graph / Circuit JSON
       ↓
Wokwi + Fritzing asset resolver
       ↓
Generated fallback boards
       ↓
React Flow workbench
       ↓
Physical view / Logical view
       ↓
CircuitJS / ngspice
       ↓
MCU emulation where supported
       ↓
Live Hardware Binding
       ↓
REAL USB-CONNECTED DEVICE
```

And the clever part is that the flow works both ways.

A physical device can create the prototype:

```text
REAL → GRAPH → PROTOTYPE
```

but a change to the prototype can also control supported physical hardware:

```text
PROTOTYPE → API → DEVICE
```

That is the differentiator.

You're not trying to make another KiCad.

You're building a **hardware discovery, digital-twin and rapid-prototyping bench** where the starting point can either be an empty canvas **or an actual piece of hardware sitting on the desk**.

That is a much more specific product than the existing tools, and I don't see one open-source system that already combines those two halves exactly the way you're describing.

----discusion only!!!! 

Yes. The way you're describing it now makes the architecture much clearer.

You really have **two systems that meet in the middle**:

**Part 1:** discover and trace the real thing sitting on your desk as deeply as the hardware allows.

**Part 2:** take that discovered hardware map, project it into the browser automatically, and let you extend, simulate, manipulate, and optionally control the real hardware from that same representation.

That is the model I would build around.

## PICSimLab is interesting because it already proves part of this concept

PICSimLab is much closer to your idea than a traditional CAD application. It emulates actual development boards, runs firmware through several processor emulators, and then has a concept called **Spare Parts** where you attach simulated components to the board's pins. Those parts include things like LEDs, buttons, displays, accelerometers, pressure sensors, SD cards, Ethernet hardware, UART interfaces, ultrasonic sensors, etc. :chatgpt-content-reference{index="0"}

So conceptually PICSimLab already does:

```text
virtual microcontroller board
        +
attach components to pins
        +
run firmware
        +
observe signals
```

It even has a remote-control interface, pin-state commands, configuration files for its attached parts, aliases for pin names, and newer support for remotely adding/configuring spare parts. :chatgpt-content-reference{index="1"}

That is extremely relevant to us.

I would **not replace your web application with PICSimLab**, though. Its UI and architecture are desktop-oriented, and your discovery side is fundamentally different. But I would absolutely study its component/runtime design and possibly use it as an optional simulator backend for supported boards.

Its current documentation is version 0.9.3, dated September 19, 2026. :chatgpt-content-reference{index="2"}

One thing we'd need to watch is licensing: PICSimLab is GPL-licensed. We can study it freely; directly incorporating its code into our product requires treating the GPL implications seriously. :chatgpt-content-reference{index="3"}

---

# The real-world discovery side

This is where your project becomes different from PICSimLab, Wokwi, Fritzing, etc.

We don't begin by saying:

> Pick an ESP32 from the library.

We begin:

> Plug something in. Tell me what this thing actually is.

Then we progressively work down through it.

For example:

```text
USB device
↓
CP2102 USB/UART bridge
↓
ESP32-S3
↓
firmware/runtime
↓
GPIO/I2C/SPI/UART controllers
↓
I2C bus
↓
0x23 responding
↓
BH1750 candidate
↓
read identification/configuration registers
↓
BH1750 verified
```

That part is very achievable.

Where it gets harder is what you said next:

> Send something through GPIO7 and figure out whether there's an LED, resistor, capacitor, whatever on the other end.

There **are ways to go substantially deeper**, but we need to separate digital discovery from electrical characterization.

### Digital components can often identify themselves

I²C is great for this because devices respond to addresses and often contain identifiable registers.

USB devices enumerate.

1-Wire devices can identify themselves.

A Linux device can expose enormous amounts through DeviceTree, sysfs, drivers, etc.

UART sometimes exposes useful protocols.

SPI gets harder because SPI itself doesn't contain a universal “who are you?” enumeration system.

GPIO gets much harder still.

### Passive components don't announce themselves

A 220 Ω resistor doesn't have a protocol.

Neither does an ordinary capacitor.

So a normal USB/COM connection cannot simply ask:

> Is there a resistor connected to GPIO7?

However, if we can **measure electrically**, the problem changes.

A safe measurement system can apply a small known, current-limited stimulus and observe the response.

Then:

- a resistor produces a roughly linear voltage/current relationship;
- a diode or LED produces a diode-like nonlinear relationship;
- a capacitor produces a charge/discharge curve;
- an open circuit behaves differently again;
- a short has another characteristic.

That doesn't magically tell us the manufacturer's exact component, but it can tell us:

> This behaves like approximately a 220 Ω resistive load.

or:

> This behaves like a diode/LED junction.

That is where I think your project could eventually have a **hardware probe accessory**.

Not something necessary for the first release, but a little measurement board containing ADC/current sensing, protected analog inputs, multiplexing and current-limited stimulus circuitry.

Then the Bench can say:

> GPIO7 appears electrically connected to a diode-like load through approximately 200–250 Ω resistance.

That's dramatically more useful than pretending software can identify things it physically cannot measure.

---

# When we can't identify it, your user-assist idea is exactly right

Suppose we know:

```text
GPIO7
    ↓
something
```

but cannot classify it.

The browser should make that obvious:

> **Unresolved attachment on GPIO7**

Then click it.

A small panel opens:

**What is connected here?**

Search:

`LED`

Select:

`LED → Red → 2.0 V nominal`

Then maybe another unresolved inline component:

`Resistor`

Set:

`220 Ω`

Now the graph becomes:

```text
ESP32.GPIO7
     │
   220 Ω
     │
 Red LED
     │
    GND
```

From that point onward, those become normal prototype components.

And importantly, the system remembers:

> user-declared

rather than claiming:

> electrically verified.

Later, if we physically measure it, we can upgrade that evidence.

That matches the evidence model you've already built into the application.

---

# Then the prototype becomes incredibly simple

This is where I would simplify everything rather than turning it into KiCad.

The workbench is just:

```text
Component library       Big interactive grid       Inspector
```

You drop things.

Every thing has connection points.

You draw lines.

That's it.

The complexity lives underneath, not in the user experience.

A Raspberry Pi might be a realistic Wokwi/Fritzing board.

An obscure controller might simply be:

```text
┌──────────────────────┐
│ Custom Controller    │
│                      │
│ MCU: RV1106          │
│                      │
● 3V3               5V ●
● SDA              SCL ●
● TX                RX ●
● GPIO1          GPIO2 ●
└──────────────────────┘
```

That is completely acceptable.

We don't need beautiful artwork for every board.

What matters is that every circle is a **real port object**.

---

# Components should have real behavior

This is one part of your current prototype that absolutely needs replacing.

An “analog sensor” slider doesn't mean anything.

Instead, components should represent actual concepts.

For example:

**Light Sensor**

```text
Ambient illumination
[---------|---------]
             420 lux
```

**PIR motion sensor**

```text
Motion:
[ OFF ][ ON ]
```

**Potentiometer**

```text
Resistance:
0 Ω ─────●───── 10 kΩ
```

**Bluetooth input**

```text
Connected: Yes
Signal value: 62%
[────────●────]
```

**PWM Control**

```text
Frequency: 1 kHz
Duty: 42%
[──────●──────]
```

Those controls change component state.

Then state propagates through the circuit model.

---

# And this is where Live versus Simulated becomes powerful

Take your exact LED example.

You have physically:

```text
ESP GPIO7
   ↓
220 Ω
   ↓
LED
   ↓
GND
```

We map that into the prototype.

The visual version shows the same thing.

Then we create:

```text
PWM Control
     ↓
ESP GPIO7
     ↓
220 Ω
     ↓
LED
```

Now the slider can operate in two different ways.

### Simulated mode

You move:

```text
PWM = 25%
```

The simulator calculates the circuit and the virtual LED becomes dim.

Move it to:

```text
PWM = 90%
```

The virtual LED becomes bright.

No physical hardware changes.

### Live mode

The exact same slider changes:

```text
physical ESP GPIO7 PWM duty
```

through your FastAPI hardware adapter.

The actual LED on your desk changes brightness.

Meanwhile the browser receives the updated state through WebSocket and reflects it visually.

That's the experience you're describing.

And we don't need the resistor itself to “do” anything digitally. The resistor becomes part of the electrical model; the PWM-controlled GPIO is what changes.

---

# Then Hybrid mode becomes even more interesting

Suppose the ESP and LED are physically real but the light sensor hasn't arrived yet.

You can do:

```text
SIMULATED LIGHT SENSOR
        ↓
REAL ESP32
        ↓
REAL LED
```

The web slider represents virtual lux.

You move:

```text
200 lux → 10 lux
```

The simulator/runtime tells the real ESP:

> sensor condition changed

and the real firmware responds.

Then the physical LED turns on.

That is a real hardware-in-the-loop prototype.

And that's where this starts becoming a seriously useful tool rather than simply a circuit drawing application.

---

# What I would borrow versus what I would build

I'd keep this pretty restrained.

| Piece | Use |
|---|---|
| **React Flow** | Canvas movement and wiring infrastructure. |
| **Wokwi Boards** | Existing MCU/development-board artwork and pin coordinates. |
| **Fritzing Parts** | Huge breadboard/component asset library and connector mappings. Fritzing `.fzp` metadata already maps connectors and even internal buses to SVG elements, which is almost exactly the importer we need. :chatgpt-content-reference{index="4"} |
| **PICSimLab** | Reference/runtime backend for board + peripheral simulation. |
| **CircuitJS** | Quick interactive electrical simulation. |
| **ngspice** | Serious electrical calculation later. |
| **Renode / AVR8js / rp2040js** | Firmware execution when we want an actual virtual processor. |
| **Your FastAPI service** | Real hardware connection and live commands. |

Everything else is really glue.

And the main glue we own is the important intellectual part:

```text
Hardware Graph
Component Schema
Port Schema
Net/Connection Graph
Component Resolver
Simulation Binding
Physical Binding
```

---

# Fritzing's format is particularly useful here

One thing worth emphasizing from my research: Fritzing's part format already explicitly defines the connection point in the SVG.

A Fritzing component has `.fzp` metadata pointing to its breadboard SVG, and each connector references an SVG element ID. That SVG element gives us the connector's physical position, and Fritzing can also store internal buses between connectors. :chatgpt-content-reference{index="5"}

So importing a Fritzing part can effectively give us:

```text
picture
+
pins
+
pin locations
+
connector identities
+
some internal connectivity
```

That's substantially better than importing a PNG and trying to figure out where the holes are.

And Fritzing sketch files also explicitly describe which part connectors are connected to which other part connectors. :chatgpt-content-reference{index="6"}

There's a lot we can reuse conceptually from that format.

---

# The first real version I would build

I wouldn't start with every simulator and every device.

I'd prove the entire idea with one path:

```text
Connected ESP32
     ↓
discover its pins
     ↓
project ESP onto prototype
     ↓
recognize / declare
220 Ω + LED on GPIO7
     ↓
automatically draw existing circuit
     ↓
add virtual PWM slider
     ↓
simulate LED brightness
     ↓
switch to Live
     ↓
slider controls real GPIO PWM
     ↓
real LED changes brightness
```

Once that works, everything else becomes expansion:

camera, motors, LiDAR, BLE, Wi-Fi, displays, other MCUs, simulated sensors, fault injection, etc.

And I think **PICSimLab is worth keeping nearby during that implementation**, not because we should turn your app into PICSimLab, but because they've already solved a lot of the ugly questions around “virtual board + attachable peripherals + pin state + emulator backend + remote control.” We can learn a lot from that model while keeping your discovery-first/browser-first architecture.
----