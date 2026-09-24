# Rapid Prototyping Workbench — Full Product Vision and Architecture

What we are building is a **visual hardware rapid-prototyping workbench inside your existing application**. 

We are building something new that will allow us to not only rapidly prototype our microcontrollers and IoT devices, but to allow us to build and prototype and, you know, basically have a breadboard in our web browser that also is able to connect through our USB ports connected into the real devices, so that way I can follow the design on the web UI, connect the real pins to the real sensors and components like resistors, capacitors, and such, and then be able to facilitate running and testing them from the UI. So that way, if I want to trigger a sensor, I can say, Okay, here's the sensor, right? And then we can trigger something like a light going on, right? Or maybe if I just have a light connected to my board, let's say an LED, right, connected to my board. Let's say I add a digital sensor on the board. I find the right one, I connect it up, and then I adjust it up and down based on the light brightness because that sensor. Now, we're adjusting the sensor in the web UI, but we're using that sensor that's a digital one, and it's fulfilling the place of a real one in real life, and we can see the light going on and off on the real device, right? So if we only have the light but we don't have the sensors, then we can still test the sensors. Or if we have them all, then we can test the whole thing and we can adjust it and play with it and see how it works, right? To see if that's how we want it to work. So you got to understand this is what we are building.
Takes the data we're already tracing and already using from our device to facilitate rapid prototyping and testing so technically I could hook anything up to my board in the real world here as long as it's connected to one of the comms and I can add any sensor to it in the in the web ui and they can talk back and forth then we can actually use them and use the web ui to control that's the idea that's what we're trying to build here now we don't want to reinvent the wheel we want to be able to use as many things that exist as possible to connect with so we can bring it in and we want to make it simple as possible like anything from the ESP to the Raspies to the latest razzpies to any Arduino

Its purpose is to take any controller, development board, embedded computer, microcontroller, or other device that your scanner has already discovered and understood, place a visual representation of that device onto a 2D engineering canvas, expose the real pins and buses that your scanner identified, and let the user visually connect additional boards, sensors, displays, LEDs, resistors, capacitors, drivers, power components, and other electronics to those pins.

The user should be able to build the circuit on-screen before or while physically assembling it. The workbench should understand that a line drawn from one pin to another is not merely artwork: it represents a hardware connection with a signal type, voltage expectations, direction, protocol, bus membership, and potentially a physical device behind it. It should tell the user whether that connection makes sense, warn about dangerous or incompatible configurations, allow simulated inputs and outputs where simulation is possible, and—when the real controller is connected through USB, serial, debug hardware, network, or another supported transport—allow the on-screen prototype to interact with the actual hardware.

The objective is therefore **not to build another Fritzing, Wokwi, KiCad, SPICE, debugger, or logic analyzer**. The objective is to make your application the system that brings those capabilities together around hardware that has already been discovered by your scanner.

That distinction is the entire architecture.

---

# What the experience should feel like

Imagine that the user has completed your existing device-analysis workflow.

Your software already knows that a physical device exists. It knows its identity, processor, available buses, usable pins, reserved pins, onboard peripherals, firmware interfaces, USB/serial/debug connection, and which properties were verified versus inferred.

The user presses:

**Prototype**

The new screen opens and the selected device is already sitting in the center of the canvas.

It should look approximately like the real board—not a generic rectangle. The pins that your scanner discovered are visually positioned around the device. If the hardware profile says a connector contains power, ground, GPIO, I²C, UART, SPI, ADC, PWM, or other capabilities, those capabilities are available directly from those connection points.

The user opens a component drawer and searches for:

> ambient light sensor

Several compatible devices appear.

They drag one onto the screen.

The visual sensor contains its real pins.

They connect:

> Controller SDA → Sensor SDA  
> Controller SCL → Sensor SCL  
> 3.3 V → VCC  
> Ground → Ground

Those lines are now real objects in your project model.

The workbench understands:

> This is an I²C device connected to this particular I²C controller.

It can then check:

> Is that pin actually capable of SDA?  
> Is the voltage compatible?  
> Does the sensor require pull-ups?  
> Does another device already occupy the same address?  
> Is the selected pin reserved for boot or onboard hardware?  
> Is there enough current available?

If everything is valid, the connection becomes green or otherwise indicates success.

That is the **basic rapid-prototype experience**.

Everything else we add should strengthen that workflow rather than replace it.

---

# The prototype should work with both imaginary hardware and real hardware

This is where your product differs from a normal schematic editor.

There are really two sources of state.

One source is **simulation**.

The other source is **the actual hardware**.

The user should not have to think about these as two separate applications.

Suppose the user adds a digital light sensor to the prototype but has not physically bought or connected it yet.

The workbench can provide a control such as:

> Ambient illumination: 250 lux

Changing the value changes the simulated sensor state.

If firmware simulation is available, the virtual controller receives that reading.

If a virtual LED is connected and the program says:

> if illumination < 100 lux, turn LED on

the LED on the screen illuminates.

That is a completely virtual test.

Now suppose the sensor has actually been wired to the real controller.

The same component on the screen can instead be bound to:

> Physical I²C bus 0, address 0x23.

Instead of a slider generating the reading, the value comes from the real device.

The same graphical component now displays:

> 247 lux — LIVE

Nothing about the circuit drawing has to change.

That is the experience we want.

---

# The canvas itself should not be something we reinvent

There are existing projects we can use heavily.

The closest open pieces currently available are in the Wokwi ecosystem.

Wokwi publishes **Wokwi Elements**, an MIT-licensed collection of web components representing electronics and IoT parts, and **Wokwi Boards**, which provides board definitions containing board artwork and pin positioning information. Wokwi's public repositories also contain browser CPU emulators such as AVR8js and rp2040js. :chatgpt-content-reference{index="0"}

This is very useful because the visual problem is substantial.

You do not want your developers spending months drawing:

- development boards
- displays
- LEDs
- switches
- connectors
- sensors
- seven-segment displays
- potentiometers
- buttons
- breadboards

Wokwi has already created a visual representation layer for many of those.

However, there is an important limitation:

**the complete Wokwi simulator/editor is not simply an open-source React component that we can import and own.**

The open pieces are valuable building blocks.

So I would use the visual assets and board definitions where their licenses permit it and build the surrounding workbench around them.

---

# Fritzing gives us the second major source of existing hardware models

Fritzing is especially valuable because its parts library was built specifically around electronics.

A Fritzing part contains metadata plus SVG artwork, including connector information. The official repository contains the part definitions shipped with Fritzing, and its own documentation describes the parts as `.fzp` metadata tied to `.svg` graphics. :chatgpt-content-reference{index="1"}

That means we can write an importer once.

The importer takes:

> Fritzing part

and turns it into:

> Prototype Workbench component

We do not need to manually recreate every board.

The same strategy applies to manufacturer-maintained Fritzing libraries from companies such as Adafruit, SparkFun, Seeed, and others where licensing allows reuse.

Your component database should therefore **aggregate existing ecosystems**, not start empty.

---

# The application needs one internal hardware representation

This is one part we do need to build.

It should not be complicated for the sake of being complicated.

It exists because Wokwi calls pins one thing, Fritzing calls them another thing, your scanner has its own hardware model, KiCad has another format, and simulation engines have yet another.

We need a common language between them.

A board in your system therefore needs to mean:

> This is a component.  
> These are its connection points.  
> These are the electrical properties of those connections.  
> These are their possible functions.  
> These are the buses exposed by the component.  
> These are the physical and simulated drivers capable of controlling it.

A wire means:

> Pin A is connected electrically or logically to Pin B.

A bus means:

> These particular connections participate in the same I²C, SPI, UART, CAN, etc. relationship.

A resistor means:

> These two electrical nodes are connected through this resistance.

That common representation is what lets everything else cooperate.

Your existing scanner should populate most of this automatically for the selected device.

---

# The selected physical device should be the starting point, not another imported board

This is critical.

We should not require the user to scan a board and then separately search a component library for the same board.

Your scanner already created the authoritative device instance.

So the prototype begins with:

> **the device you already detected**

Then we attempt to find artwork for it.

The process becomes:

> scanner identifies physical board  
> → search visual libraries  
> → find matching Wokwi/Fritzing/manufacturer model  
> → map artwork pins to your discovered pins  
> → place it into Prototype

If no exact drawing exists, we can automatically generate a clean generic device representation showing the real connector and pin names.

That prevents unsupported hardware from blocking the user.

---

# The visual wiring should represent actual hardware semantics

When the user drags a wire between two pins, the system should immediately understand what kind of relationship they are creating.

For example, connecting an output GPIO to an LED is different from connecting an I²C SDA line to a sensor.

The connection engine should understand:

**Signal capability.**  
Can these pins legally perform the requested function?

**Direction.**  
Are we accidentally connecting two driven outputs together?

**Voltage.**  
Are we connecting a 5 V output directly into a 3.3 V-only input?

**Bus relationship.**  
Is this new component participating in an existing I²C/SPI/UART bus?

**Required supporting components.**  
Does the design need a resistor, pull-up, transistor, level shifter, termination resistor, flyback diode, or another component?

**Reserved hardware.**  
Is that pin already being used internally by flash, memory, camera, boot configuration, or another onboard resource?

That means the rapid prototype tool doubles as a **hardware design assistant**.

---

# Electrical simulation should be delegated to existing engines

We do not want to write an electronics simulator.

There are two serious options worth integrating.

## CircuitJS

CircuitJS is already a browser-based electronic circuit simulator and can be embedded inside another webpage. Existing CircuitJS documentation and repositories show support for embedding/loading circuits programmatically. :chatgpt-content-reference{index="2"}

CircuitJS is valuable because it immediately gives us interactive behavior for common electronics.

Resistors, capacitors, sources, diodes, transistors, logic elements, switches, scopes, and many other primitives already work.

For an early version of your Prototype tool, this is extremely attractive.

Your system draws the circuit.

Your graph translates it into a CircuitJS representation.

CircuitJS evaluates it.

We show the results back in your interface.

We are not reinventing electrical mathematics.

There is a licensing consideration because CircuitJS variants are GPL-licensed, so we need to decide whether it runs as a separate embedded service/application or whether the way we distribute the product is compatible with the license.

That is an engineering/legal integration question, not a reason to discard it.

---

# ngspice should be available when the user needs real electrical analysis

CircuitJS gives us fast interactivity.

**ngspice** gives us a mature SPICE engine.

ngspice supports being compiled as a shared library so another program can control the simulator, submit circuit descriptions, change parameters, run simulations, and retrieve results.

That means your application can generate a SPICE netlist automatically.

The user never has to see the netlist.

They simply see:

> Voltage at node: 3.27 V  
> LED current: 11.4 mA  
> Maximum current: acceptable

The workbench could therefore offer:

**Quick Simulation**

using the interactive engine, and:

**Detailed Electrical Analysis**

using ngspice.

That is much more realistic than attempting to make the React code itself calculate electronic circuits.

---

# SimulIDE is another existing system worth examining, but I would not make it the main UI

SimulIDE already combines electronic components, MCU simulation, an editor, and basic debugging. It supports PIC, AVR, and Arduino-oriented simulation. The project itself says that it is optimized for simplicity and speed rather than high-accuracy circuit analysis. :chatgpt-content-reference{index="3"}

That makes SimulIDE valuable in two ways.

First, it proves that the user experience you want is established and reasonable.

Second, its implementation can provide ideas or backend functionality.

However, it is a Qt desktop application.

Your product is already React/web-oriented.

Trying to jam its entire interface into your application would probably cost more than selectively reusing better web-oriented components.

---

# We need a live-hardware bridge between the canvas and the selected device

This is probably the most important subsystem in your version of this product.

A normal simulator has:

> UI → simulation.

You need:

> UI → simulation **or actual hardware**.

Your application already has host-level device communication.

We should formalize it behind a generic **Hardware Control API**.

The prototype should be able to say things like:

> read this pin  
> set this pin high  
> set PWM to 40%  
> read ADC channel  
> scan I²C  
> read register  
> perform SPI transfer  
> write UART bytes  
> reset device

It should not care whether those actions are implemented underneath through:

- USB
- virtual COM/serial
- WebUSB
- Web Serial
- JTAG
- SWD
- network
- BLE
- vendor debugger
- board runtime agent

The selected-device adapter already knows how that particular board can be accessed.

Prototype simply asks for capabilities.

---

# Firmata is one of the first ready-made control layers I would support

Firmata exists specifically to allow a program on a host computer to control a microcontroller.

The Firmata protocol includes concepts for:

- digital I/O
- analog I/O
- pin modes
- reporting
- I²C
- reset
- extensible command messages

That means on compatible boards we can avoid inventing the control firmware ourselves. :chatgpt-content-reference{index="4"}

There is also **Johnny-Five**, a JavaScript robotics/IoT framework that commonly works over Firmata.

Because your application is already heavily JavaScript/React-oriented, those ecosystems are worth evaluating for the physical-control portion.

They are not universal.

But where a board supports them, they could make the first version much faster.

---

# For unsupported controllers, we need adapters rather than one universal protocol

A Raspberry Pi is not controlled like an Arduino.

A Jetson is not controlled like a Cortex-M debug target.

An embedded Linux computer might expose GPIO through Linux APIs.

A microcontroller may expose a serial RPC interface.

Another device might only expose JTAG.

So our Hardware Control API should remain consistent while the implementation underneath changes.

That is how we support the generic system you are describing.

Conceptually:

> Prototype asks: `set GPIO X HIGH`

The device adapter decides:

> I can perform that through Firmata.

or:

> I can perform that through a board runtime service.

or:

> I can perform that through Linux GPIO.

or:

> This device does not support live GPIO manipulation while its current firmware is running.

That final outcome is also important.

The application must be able to say **no** when the hardware genuinely cannot do what the user is requesting.

---

# There are real limitations to live control

This needs to be explicit in the design.

Simply plugging a board into USB does **not** automatically grant control over every pin on that board.

USB only exposes whatever the board's current firmware, bootloader, debug interface, or operating system exposes.

If a device's firmware provides a serial console only, we cannot magically manipulate arbitrary GPIO through that console.

If a debugger is available, we may be able to do more.

If we install a compatible runtime agent, we can do much more.

Therefore each selected device should have a **Live Control Capability Profile**.

It might say:

> GPIO read/write: available  
> ADC read: available  
> I²C: available  
> SPI: unavailable  
> PWM: available  
> direct memory/debug: unavailable

The Prototype interface enables or disables controls accordingly.

That prevents the UI from pretending it has powers the underlying connection does not provide.

---

# Physical components cannot all be automatically detected

This is another important limitation.

I²C is relatively discoverable because devices respond at addresses.

Some devices also expose identifying registers.

So the platform may be able to determine:

> something responds at 0x29

and then probe known identification registers to determine the likely component.

UART devices may emit identifying information.

USB devices enumerate themselves.

PCIe devices enumerate themselves.

BLE devices advertise.

Network services announce themselves.

But a simple resistor cannot identify itself.

A capacitor cannot tell the microcontroller its value.

Most SPI devices cannot simply be enumerated because SPI does not have a universal device-discovery mechanism.

An analog light sensor may only output a voltage.

So the application must distinguish:

> **detected**

from:

> **inferred**

from:

> **user-added**

That is not a weakness in your software.

It is a physical limitation of electronics.

---

# We should provide virtual instruments in the prototype bench

A serious electronics bench does more than connect wires.

It lets the user inspect what is happening.

So the Prototype environment should include virtual instruments such as:

**Logic analyzer.**  
Shows digital transitions and decodes protocols.

**Oscilloscope.**  
Shows voltage versus time where an appropriate live or simulated source exists.

**Voltmeter.**  
Measures voltage between points in a simulated circuit or through supported physical measurement hardware.

**Current meter.**  
Works directly in simulation and with appropriate physical measurement devices.

**Serial terminal.**  
Connects to UART/USB serial output.

**I²C inspector.**  
Shows bus addresses and transactions.

**SPI inspector.**  
Shows SPI transfers when the signals can be observed.

**PWM inspector.**  
Shows frequency and duty cycle.

We should not write all of the protocol decoding ourselves.

---

# sigrok should provide much of the protocol-decoding capability

The sigrok ecosystem already provides a large protocol-decoder collection covering major hardware protocols and many device-specific formats. Its protocol-decoder documentation includes I²C, UART, SPI-related protocols, I²S, PWM, USB-related protocols, memory devices, sensors, and many others. :chatgpt-content-reference{index="5"}

If the user connects a supported physical logic analyzer, sigrok can help us interpret actual electrical traffic.

That produces something extremely useful.

Your application may already know:

> Pins 12 and 13 appear to be I²C.

Then a real capture confirms:

> address 0x3C is transmitting.

Now the Prototype environment can show:

> Real bus activity confirmed.

That closes the loop between hardware discovery and hardware design.

---

# Firmware simulation should be optional, not required for the first prototype release

This is where Renode belongs.

Renode is an MIT-licensed virtual-development framework that can model entire processors, SoCs, peripherals, and connections and run real embedded software binaries. It currently supports architectures including ARM, RISC-V, Xtensa, x86, MSP430X, SPARC, and POWER. :chatgpt-content-reference{index="6"}

That is enormously powerful.

But it should not block the basic workbench.

The user should be able to visually design a prototype long before Renode supports their exact processor.

When a Renode model exists, the Prototype runtime can say:

> Instead of the physical processor, run the actual firmware inside Renode.

Then simulated sensors communicate with simulated firmware.

That gives you sophisticated completely virtual testing.

But it is an enhancement to the workbench, not the workbench itself.

---

# The prototype needs a component marketplace/library architecture

We cannot ship every electronic component ever manufactured.

Instead, we should make the component catalog extensible.

A component record should reference:

- visual representation
- manufacturer
- part number
- pins
- electrical limits
- interfaces
- simulation model if available
- live-driver information if available
- documentation
- source/provenance

Then the catalog can pull from several existing sources.

The initial catalog would aggregate:

**Wokwi Elements**  
Good source for ready-made browser visuals. :chatgpt-content-reference{index="7"}

**Wokwi board definitions**  
Useful for board artwork and pin locations. :chatgpt-content-reference{index="8"}

**Fritzing Parts**  
Large source of breadboard-style component graphics and connector definitions. :chatgpt-content-reference{index="9"}

**KiCad libraries**  
Useful for professional schematic symbols, footprints, and later export.

**Manufacturer libraries**  
Adafruit, SparkFun, Seeed, Arduino, Raspberry Pi ecosystem, ST, Nordic, Espressif, TI, NXP, Microchip, etc.

**Your own discovered hardware database**  
Every successfully identified device can become another known component profile.

Eventually the user could scan a new piece of hardware and effectively expand the catalog.

---

# KiCad should be the professional destination

Your rapid-prototyping environment should remain easy.

We should not try to turn it into a full PCB-design suite.

When a user reaches the point where they need:

- schematic capture
- PCB layout
- footprints
- routing
- fabrication outputs
- production-level design

we should export to KiCad.

KiCad has a documented `.kicad_sch` schematic file format, which makes generated schematic output realistic rather than depending on UI automation. :chatgpt-content-reference{index="10"}

So the lifecycle becomes:

> discover hardware  
> → prototype visually  
> → validate  
> → test live  
> → prove behavior  
> → export schematic  
> → continue in KiCad

That is exactly where your tool should end and professional EDA should begin.

---

# The complete user-facing design

I would structure the Prototype screen around four permanent areas.

## Component Library

The left side answers:

> What can I add?

It contains searchable categories such as:

- controller boards
- embedded computers
- sensors
- displays
- LEDs
- buttons
- relays
- motors
- drivers
- resistors
- capacitors
- transistors
- MOSFETs
- voltage regulators
- power supplies
- connectors
- test instruments

The user should be able to search by ordinary language or specific part number.

---

## Workbench

The center of the screen is the visual circuit.

This is where devices are placed and connected.

It should support:

- drag
- drop
- zoom
- pan
- snap
- wire routing
- pin highlighting
- bus highlighting
- component selection
- connection deletion
- copy/paste
- undo/redo
- grouping
- annotations

The board imported from the selected device appears here automatically.

---

## Inspector

The right side explains whatever is selected.

Select a pin and it should show:

> pin identity  
> supported functions  
> current mode  
> voltage  
> live state  
> connected component  
> warnings

Select a sensor and it should show:

> device identity  
> interface  
> address  
> current reading  
> simulated/live mode  
> configurable properties

Select a resistor and it shows:

> resistance  
> tolerance  
> power rating  
> simulated current  
> simulated voltage drop

---

## Instrumentation

The lower portion behaves like the test bench.

The user switches between:

> Console  
> Logic Analyzer  
> Scope  
> Bus Monitor  
> Electrical Analysis  
> Events  
> Firmware

That gives the user one workspace rather than forcing them to jump between six applications.

---

# Live and simulated components should look different

This matters for usability.

The workbench should clearly distinguish:

**Physical / Connected**

Meaning the state comes from real hardware.

**Virtual / Simulated**

Meaning the state comes from a simulation model.

**Disconnected**

Meaning this was physical hardware but is no longer connected.

**Unknown / User-defined**

Meaning the user has placed a component but the system cannot independently verify it.

This should integrate directly with the device-state system we discussed earlier.

If the controller gets unplugged, the prototype should remain on the screen but visibly transition to:

> DISCONNECTED

Any operations requiring real hardware are disabled.

The design itself is preserved.

---

# Fault injection belongs in this tool

You specifically mentioned faults and tolerances.

That is an excellent feature.

In simulation, the user should eventually be able to inject conditions such as:

> resistor ±5% tolerance  
> low supply voltage  
> noisy ADC input  
> sensor disconnected  
> I²C NACK  
> UART corruption  
> GPIO stuck HIGH  
> GPIO stuck LOW  
> bus timeout  
> sensor out-of-range  
> dropped network connection

This lets the user answer:

> What happens when the hardware stops behaving perfectly?

That moves the tool from simple prototyping into actual robustness testing.

It should come after the core environment works, but the architecture should accommodate it from the beginning.

---

# What we can reuse versus what we genuinely have to build

This is the important division.

### We can reuse

Wokwi/Fritzing for much of the visual parts ecosystem.

CircuitJS/ngspice for electrical simulation.

Renode and browser CPU emulators for MCU/firmware simulation.

Firmata/Johnny-Five and your existing device adapters for host hardware control.

sigrok for signal and protocol decoding.

KiCad for the detailed engineering handoff.

Existing vendor metadata, CMSIS, Zephyr, PlatformIO, DeviceTree, datasheets, and your scanner for hardware knowledge.

### We need to build

The **Prototype Workbench UI** that combines those technologies.

The normalized component format that lets parts from different ecosystems coexist.

The mapping between your discovered device pins and the visual component pins.

The project connection graph.

The live-binding system connecting a graphical pin/component to a real hardware endpoint.

The validation rules that compare connections against hardware metadata.

The adapter interfaces between your project and the outside simulators/tools.

That is a manageable scope.

We are not building ten simulators.

We are building **one orchestration product around existing simulators and hardware engines**.

---

# The requirements I would give the engineering agent

The Prototype capability must allow a previously selected and analyzed device to be opened directly into a 2D visual electronic workbench. The original selected-device profile remains authoritative; Prototype must consume its known pins, buses, electrical capabilities, onboard components, connection status, firmware information, and transport adapters rather than creating an independent duplicate device definition.

The workbench must provide a searchable reusable component catalog sourced wherever possible from existing open hardware ecosystems such as Wokwi Elements/Boards, Fritzing libraries, KiCad libraries, manufacturer component libraries, and the application's own known-device database. The user must be able to drag controllers, sensors, displays, LEDs, passive components, power components, drivers, connectors, and related hardware onto the canvas and visually connect actual component pins.

Connections must be stored as real structured hardware relationships rather than graphical lines. Every connection must identify its endpoints and, where known, signal type, bus, voltage domain, direction, physical/live status, and validation state. The workbench must use the detected-device metadata to prevent or warn about incompatible pins, inappropriate voltage levels, reserved pins, bus-address conflicts, output-to-output conflicts, missing supporting circuitry, and other known design errors.

The same prototype project must support both simulated and physical state. A component may represent an entirely virtual device or may be bound to a real device discovered by the hardware system. When a supported physical endpoint is available, changes or measurements must flow between the hardware service and the corresponding object in the Prototype UI. The UI must never pretend a physical capability exists when the current board firmware, transport, debugger, or operating system does not expose it.

Live device control must therefore use the application's existing hardware adapters behind a normalized control interface capable of exposing operations such as digital I/O, analog acquisition, PWM, bus operations, serial communication, reset, debugging, and other functions when supported. Firmata, Johnny-Five, vendor tools, native Linux interfaces, serial protocols, JTAG/SWD tooling, or custom board agents may implement those operations underneath the abstraction depending on the selected hardware.

The first electrical simulation integration should reuse an existing simulator rather than implementing circuit mathematics internally. CircuitJS should be investigated for interactive web simulation, while ngspice should be available for higher-fidelity analysis and generated SPICE netlists. The prototype project must remain usable even when no electrical simulation model exists for a particular component.

The workbench must support instrumentation rather than merely drawing circuitry. Protocol analysis should integrate existing tooling such as sigrok wherever practical, and the UI should eventually expose virtual scopes, logic analyzers, bus inspection, serial consoles, electrical measurements, and component-state displays. Instrument availability should depend on whether the source is simulated or whether physical measurement hardware exposes the necessary information.

The architecture must allow optional processor and firmware emulation through projects such as Renode, AVR8js, or rp2040js without making those systems mandatory for ordinary prototype editing. Simulation support will vary by processor and peripheral; unsupported processors must still be usable as visual/live prototype devices.

The user must be able to preserve a prototype even when real hardware disconnects. Physical components transition to a disconnected state while the topology, metadata, measurements, firmware references, and visual project remain intact. Reconnecting the same hardware should rebind it to the existing prototype instance wherever reliable device identity allows it.

Finally, the prototype must be exportable. The long-term handoff target should include KiCad schematic generation, SPICE netlists, BOM generation, firmware/project configuration where practical, and the application's own portable project format. The Prototype system is intended to accelerate experimentation and hardware/software integration—not replace professional PCB engineering software.

---

That is the complete vision I would use as the foundation: **a hardware-aware visual workbench that starts with a device your system has already discovered, lets the user visually extend it using existing component libraries, validates the wiring, optionally simulates the electronics and firmware using existing engines, binds the same visual design to real USB-connected hardware when available, exposes instrumentation and fault testing, and then hands the proven design off to professional tools instead of attempting to replace them.**