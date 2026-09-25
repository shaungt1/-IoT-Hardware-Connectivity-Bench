# AI-Ready Prototype Graph and Circuit Agent Architecture

What we need to build is a **fully addressable prototype graph** underneath the visual breadboard. The screen is only a rendering of that graph. Every board, resistor, capacitor, sensor, wire, pin, bus, connector, property, simulation value, physical-device binding, warning, and measurement must exist as a uniquely identified object that can be read, changed, subscribed to, traced, saved, restored, and acted upon through an internal API.

That is what makes the prototype environment truly agentic.

The AI should never have to “look at the screen and drag a mouse from here to there.” It should be able to say:

> Connect `board_1.GPIO5` to `sensor_3.SDA`.

or:

> Insert a 4.7 kΩ pull-up resistor between `net_i2c_sda` and `rail_3v3`.

or:

> Set the simulated light level on `sensor_3` to 25 lux.

The system changes the canonical graph, emits events, the UI redraws itself, the simulator recalculates the circuit, and—if any parts are bound to physical hardware—the hardware layer receives the appropriate permitted commands.

That is the architecture.

---

## The prototype itself becomes a digital twin graph

Everything gets an ID.

A component is not:

> that green rectangle on the screen.

It is:

```text
component_01
type: controller-board
model: detected-board-model
position: x=412, y=267
```

A pin is not:

> that little circle beside the board.

It is:

```text
component_01.pin.GPIO5
```

A resistor might be:

```text
resistor_14
resistance: 220 ohms
tolerance: 5%
powerRating: 0.25 W
```

And its terminals are individually addressable:

```text
resistor_14.pin.A
resistor_14.pin.B
```

A wire is really a **net connection**:

```text
net_23:
    component_01.GPIO5
    resistor_14.A
```

Then another:

```text
net_24:
    resistor_14.B
    led_08.ANODE
```

The UI can draw those connections however it wants. The actual circuit exists independently from its visual appearance.

That distinction is critical because it means the same prototype can be consumed by:

- the React UI
- the electrical simulator
- the physical hardware bridge
- the validation system
- the AI agent
- firmware generation
- future MCP clients
- exports to KiCad/SPICE/etc.

---

# Every object needs a standard contract

I would define one canonical **Prototype Component Schema**.

Every simple or complex component conforms to it.

A resistor and a Linux AI board are obviously enormously different, but structurally they can still follow the same contract.

A component record needs approximately:

```text
identity
visual representation
properties
ports / pins
internal capabilities
simulation provider
physical binding
validation rules
state
events
provenance
```

For example:

```json
{
  "id": "sensor_4",
  "componentType": "sensor",
  "manufacturer": "Example",
  "model": "Light Sensor",
  "position": {
    "x": 640,
    "y": 220
  },

  "properties": {
    "supplyVoltage": {
      "value": 3.3,
      "unit": "V",
      "access": "read"
    },
    "simulatedLux": {
      "value": 250,
      "unit": "lux",
      "access": "read-write"
    }
  },

  "ports": {
    "VCC": {},
    "GND": {},
    "SDA": {},
    "SCL": {}
  }
}
```

That means the agent can query:

> What properties can I modify?

and receive:

```text
simulatedLux
```

rather than guessing.

---

# Every property does not necessarily need to be writable

This is an important refinement to what you said.

Every property should be:

**addressable**  
We can identify exactly which property we mean.

**observable**  
The application can read its current state.

**typed**  
The application knows whether it is voltage, current, boolean, frequency, resistance, enumeration, string, etc.

**versioned**  
We know whether it changed after an agent inspected it.

**traceable**  
We know what changed it and when.

**event-producing**  
A change can notify interested systems.

But not everything should be writable.

For example:

```text
manufacturer
physical voltage measured at pin
actual MCU model
maximum current rating
```

are read-only.

Whereas:

```text
resistance
simulated temperature
PWM duty cycle
virtual switch state
component location
```

may be writable.

So every property receives an access mode:

```text
read
write
read-write
computed
command-only
```

That prevents an agent from trying to do something meaningless such as:

> Set maximum GPIO voltage to 12 V.

---

# Every pin and connector needs a first-class schema

Pins cannot simply be strings.

Each pin needs something like:

```text
id
componentId
physicalLabel
logicalName
aliases
connector
position
electricalType
direction
voltageMin
voltageMax
currentMax
signalCapabilities
alternateFunctions
busMembership
reservedState
connectionState
physicalBinding
```

For example:

```json
{
  "id": "board_1.GPIO5",
  "label": "D1",
  "aliases": ["GPIO5", "SCL"],

  "capabilities": [
    "GPIO",
    "PWM",
    "I2C_SCL"
  ],

  "electrical": {
    "logicVoltage": 3.3,
    "maxVoltage": 3.6
  },

  "position": {
    "side": "left",
    "x": 0,
    "y": 128
  }
}
```

Now the agent understands both:

> where GPIO5 appears visually

and:

> what GPIO5 is electrically capable of.

---

# Buses also need to become actual objects

Do not store I²C merely as two wires.

Create:

```text
bus_i2c_0
```

containing:

```text
controller
SDA net
SCL net
frequency
voltage
attached devices
addresses
pull-up state
simulation state
physical state
```

Then the agent can ask:

> Show me I²C0.

and receive:

```text
Controller: board_1
SDA: GPIO5
SCL: GPIO6
Voltage: 3.3 V
Frequency: 400 kHz

Devices:
sensor_4 — 0x23
display_8 — 0x3C

Pull-ups:
SDA → 4.7 kΩ → 3V3
SCL → 4.7 kΩ → 3V3
```

Now it can actually reason about the circuit.

---

# Nets should be the fundamental connection model

A visible wire is only one rendering of a **net**.

A net is a collection of electrically connected terminals.

For example:

```text
NET_3V3

board_1.3V3
sensor_4.VCC
display_8.VCC
resistor_12.A
```

Another:

```text
NET_GND

board_1.GND
sensor_4.GND
display_8.GND
```

This is how professional electrical-design systems think about circuits, and it is exactly what the agent needs.

The agent can query:

> What is connected to this net?

or:

> Trace from GPIO5.

And receive the entire path.

---

# Traceability should be built into the graph

You specifically mentioned tracing every point.

Absolutely.

The Prototype Graph Service should expose queries such as:

```text
trace_from_port(portId)

trace_net(netId)

find_path(sourcePort, destinationPort)

get_connected_components(componentId)

get_downstream(componentId)

get_upstream(componentId)

get_bus_members(busId)
```

Suppose the user says:

> Why isn't this LED turning on?

The agent could trace:

```text
controller.GPIO7
        ↓
net_17
        ↓
resistor_2
        ↓
net_18
        ↓
LED anode
        ↓
LED cathode
        ↓
GND
```

Then inspect:

```text
GPIO7 state = HIGH
GPIO voltage = 3.28 V
resistance = 10 kΩ
predicted current = insufficient
```

Now the agent can actually diagnose something instead of merely reading a picture.

---

# The Prototype Graph Service should be the authority

I would create a backend service called something like:

## `PrototypeGraphService`

The React UI never directly edits the canonical circuit.

Instead it requests mutations.

For example:

```text
create_component()
delete_component()

move_component()

set_property()

create_net()
delete_net()

connect_port()
disconnect_port()

create_bus()
assign_bus_member()

bind_physical_port()

bind_simulation_model()

inject_fault()

validate()

simulate()

save_revision()
```

The React application calls these APIs.

The AI calls these APIs.

Later, MCP calls these APIs.

Everything uses the same contract.

---

# Do not let the AI manipulate the browser DOM

This is extremely important.

The agent should not have to do this:

> Find a circle on screen and simulate dragging the mouse to another circle.

That is fragile and unnecessary.

Instead:

```text
Agent:
connect_ports(
  source="board_1.GPIO5",
  destination="sensor_4.SDA"
)
```

The backend modifies the graph.

Then the UI receives:

```text
prototype.connection.created
```

and React Flow draws the wire automatically.

The user sees the agent wiring the circuit in real time.

But technically the AI is modifying structured engineering data.

That is far more reliable.

---

# Grid positions should still be available to the agent

The AI should have access to visual layout information too.

Each component has:

```text
x
y
width
height
rotation
layer
```

Each pin has:

```text
relativeX
relativeY
absoluteX
absoluteY
side
```

So an agent can say:

> Move the light sensor 100 pixels to the right of the controller.

or:

> Put the resistor between the controller and LED.

But layout should be a separate operation from electrical connectivity.

For example:

```text
move_component(
    component="resistor_2",
    x=615,
    y=420
)
```

doesn't change the circuit.

Whereas:

```text
connect_ports(...)
```

does.

---

# Every state change should produce an asynchronous event

This addresses the asynchronous modality you described.

I would create a **Prototype Event Bus**.

Whenever something happens, an event is generated.

Examples:

```text
prototype.component.created
prototype.component.deleted
prototype.component.moved

prototype.property.changed

prototype.port.connected
prototype.port.disconnected

prototype.net.created
prototype.net.changed

prototype.bus.changed

prototype.validation.warning
prototype.validation.error
prototype.validation.resolved

prototype.simulation.started
prototype.simulation.updated
prototype.simulation.failed

prototype.signal.changed

prototype.device.bound
prototype.device.disconnected

prototype.hardware.input
prototype.hardware.output

prototype.agent.plan.created
prototype.agent.action.completed
```

Each event includes:

```json
{
  "eventId": "...",
  "prototypeId": "...",
  "revision": 138,
  "timestamp": "...",
  "source": "user|agent|simulation|hardware|system",
  "subject": "board_1.GPIO5",
  "type": "prototype.signal.changed",
  "before": 0,
  "after": 1
}
```

That event stream can go over the FastAPI WebSocket infrastructure you already have.

Your current application already has a WebSocket delivering runtime status from the hardware service, so this extends an existing architectural pattern rather than introducing something foreign. 

---

# The frontend becomes a projection of backend state

This is another crucial decision.

Think:

```text
Prototype Graph
      ↓
events
      ↓
React state
      ↓
visual breadboard
```

not:

```text
React canvas
      ↓
somehow infer a circuit
```

This makes AI integration dramatically easier.

The current visual environment becomes one **projection** of the canonical graph.

Other projections can exist:

```text
Physical board view
Logical/card view
Netlist view
Bus view
Simulation view
AI graph view
KiCad export
SPICE netlist
```

All represent the same prototype.

---

# Persist the graph, not screenshots

The saved prototype should contain:

```text
prototype
components
ports
properties
nets
buses
bindings
layout
simulation configuration
fault scenarios
validation state
revisions
```

SQLite is perfectly reasonable initially.

You already have a SQLite-backed `StateStore` supporting settings and operation auditing. 

I would add tables such as:

```text
prototype_projects
prototype_components
prototype_ports
prototype_properties
prototype_nets
prototype_net_members
prototype_buses
prototype_bindings
prototype_events
prototype_revisions
prototype_scenarios
```

For larger cloud deployments, that schema can move to PostgreSQL later.

---

# Use optimistic versioning so agents cannot overwrite one another

Imagine:

1. User changes a resistor to 220 Ω.
2. Agent inspected the old circuit when it was 1 kΩ.
3. Agent tries to modify the old version.

We don't want its change silently overwriting the user's work.

Every prototype gets a revision:

```text
revision: 173
```

Agent requests:

```text
set_property(
    component="resistor_7",
    property="resistance",
    value=470,
    expectedRevision=173
)
```

If the project is now revision 174:

```text
409 Conflict

Prototype changed.
Refresh state before applying modification.
```

Your firmware file workspace already uses the same general concept with SHA-256 content hashes to prevent stale file writes. 

Use that same philosophy here.

---

# Agent modifications should use plans and transactions

The AI should not make ten electrical changes one by one and leave a half-finished circuit if step six fails.

Let it produce:

## `PrototypeChangePlan`

For example:

```text
Goal:
Connect light sensor to I2C0.

Changes:

1. Add BH1750.
2. Connect VCC → NET_3V3.
3. Connect GND → NET_GND.
4. Connect SDA → GPIO5.
5. Connect SCL → GPIO6.
6. Add 4.7k SDA pull-up.
7. Add 4.7k SCL pull-up.

Validation:
No voltage errors.
No address conflicts.
```

The user can see the plan before it happens.

Then:

```text
apply_prototype_plan(planId)
```

executes it atomically.

If one step fails, roll back the entire change.

That same pattern fits very well with your existing `OperationManager`, which already implements plan, approval, target fingerprint checking, locking, execution and audit receipts for hardware operations. 

---

# Physical hardware binding

This is where the graph becomes a true digital twin.

A prototype port can optionally have:

```text
physicalBinding
```

For example:

```text
prototype:
board_1.GPIO7

physical:
selected_device.pin.GPIO7
```

Then:

```text
prototype signal change
        ↓
hardware binding service
        ↓
device adapter
        ↓
physical hardware
```

And in the other direction:

```text
physical GPIO changes
        ↓
device adapter
        ↓
hardware event
        ↓
prototype event bus
        ↓
board_1.GPIO7 state updates
        ↓
UI and AI both see it
```

This means the AI can say:

> Set GPIO7 high.

but it is still calling a controlled API.

If that physical target does not expose writable GPIO through the current firmware/debug interface, the command returns:

```text
unsupported
```

rather than pretending to work.

---

# Simulation uses the same event system

The exact same architecture works for simulated devices.

Consider a light sensor.

The user moves:

```text
ambientLux = 20
```

That creates:

```text
prototype.property.changed
```

The behavioral sensor model updates its output/register state.

That creates:

```text
prototype.signal.changed
```

The simulated controller or real bound controller consumes that state.

Then the LED output changes.

Another:

```text
prototype.signal.changed
```

And the UI updates.

The AI can subscribe to the same stream.

---

# Fault injection should be a first-class API

You mentioned eventually predicting and testing failures.

Do that structurally from the beginning.

Every component or connection may support faults.

Examples:

```text
open_circuit
short_circuit
stuck_high
stuck_low
noise
intermittent_connection
overvoltage
undervoltage
component_tolerance
i2c_nack
packet_loss
sensor_out_of_range
overtemperature
```

An agent could request:

```text
inject_fault(
    target="sensor_4.SDA",
    fault="open_circuit"
)
```

The simulator runs again.

The agent observes the circuit behavior and reports what failed.

Now you have a serious engineering test environment.

---

# Custom components become possible automatically

Because everything follows the same schema, a user can create a component that has never existed before.

They define:

```text
name
visual shape/SVG
properties
pins
pin locations
electrical restrictions
capabilities
simulation behavior
```

For example:

```text
Custom LED Strip

pins:
VCC
DATA
GND

properties:
ledCount = 30
voltage = 5 V
brightness = 100%
```

The renderer can dynamically draw 30 LEDs.

Change:

```text
ledCount = 60
```

The component redraws.

The agent sees the exact same property.

Later the strip might support methods:

```text
set_pixel()
set_brightness()
fill()
clear()
```

So it becomes both a visual component and an agent-controllable component.

---

# The AI should receive a purpose-built snapshot, not the entire database

Now we get into the actual LangGraph portion.

Before each reasoning step, create a:

## `PrototypeContext`

It might contain:

```text
project
current revision

selected components
selected nets
selected buses

component summaries
port summaries
warnings

simulation state

physical hardware bindings

recent events

available actions
```

The model does not need five thousand JSON properties every turn.

It asks for deeper information as needed.

For example:

```text
Agent sees:
board_1
sensor_4
led_2
3 nets
2 warnings

Agent asks:
get_component("sensor_4")
```

Then it receives the complete sensor record.

---

# Why LangGraph fits particularly well

LangGraph is actually a very strong fit here because this agent is not merely doing:

```text
prompt → model → answer
```

It is doing:

```text
understand
      ↓
inspect circuit
      ↓
validate
      ↓
research if necessary
      ↓
create plan
      ↓
possibly wait for approval
      ↓
apply changes
      ↓
simulate
      ↓
observe results
      ↓
possibly revise
      ↓
finish
```

LangGraph is specifically designed for long-running stateful workflows where deterministic application logic and LLM-driven decisions coexist. Its current documentation identifies durable execution, persistence, streaming and human-in-the-loop as core features. :chatgpt-content-reference{index="4"}

That is exactly what this prototype agent needs.

---

# The Prototype Agent graph

I would use something approximately like:

```text
                 USER REQUEST
                      │
                      ▼
               Load Prototype
                      │
                      ▼
               Understand Goal
                      │
                      ▼
            Gather Required State
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
     Enough evidence?           No
           │                     │
          Yes              Research / inspect
           │                     │
           └──────────┬──────────┘
                      ▼
               Create Plan
                      │
                      ▼
             Deterministic Check
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
       Valid                   Invalid
          │                       │
          ▼                       ▼
   Approval required?        Revise Plan
          │
     ┌────┴─────┐
     │          │
    No         Yes
     │          │
     │      Wait for user
     │          │
     └────┬─────┘
          ▼
       Apply Plan
          │
          ▼
       Validate
          │
          ▼
       Simulate
          │
          ▼
    Observe Results
          │
     ┌────┴────┐
     ▼         ▼
   Success   Needs work
     │         │
     │      Revise
     │         │
     └────┬────┘
          ▼
        REPORT
```

LangGraph's interrupt mechanism is designed specifically to pause a running graph, persist its state, wait for external approval or input, and then resume from the saved state. :chatgpt-content-reference{index="5"}

Its persistence layer also separates thread-level checkpoints from longer-term stores, which maps cleanly onto an engineering session versus durable prototype knowledge. :chatgpt-content-reference{index="6"}

---

# The prototype AI service should expose engineering tools

The model itself gets tools like:

```text
get_prototype_summary
get_component
get_port
get_net
get_bus

trace_port
trace_net
find_path

search_component_catalog

validate_prototype
simulate_prototype

create_change_plan

add_component
remove_component
move_component

set_property

connect_ports
disconnect_ports

bind_physical_device

inject_fault

run_test
```

But I would divide them into:

### Read tools

Agent can use automatically.

### Planning tools

Agent can use automatically but they only create proposed changes.

### Mutation tools

Used when policy allows or after approval.

### Physical hardware tools

Continue through the stricter existing target-bound operation system.

---

# The AI should be able to watch the prototype asynchronously

This is slightly different from responding to chat.

We should also have a **Prototype Watch Service**.

The graph changes.

The deterministic validator runs automatically.

If something important happens:

```text
voltage violation
short circuit
component failure
bus address collision
physical device disconnected
simulation divergence
unexpected signal
```

the AI service can be notified.

But we should not invoke a large foundation model for every mouse movement.

Instead:

```text
events
  ↓
cheap deterministic filters
  ↓
meaningful engineering event?
  ↓
yes
  ↓
AI analysis
```

So dragging a board ten pixels does not call GPT.

Connecting 5 V directly into a 3.3 V-only input does.

That keeps the system responsive and inexpensive.

---

# The user-facing Prototype Assistant

Inside Prototype, I would add a contextual drawer.

Not a separate generic chatbot.

Something like:

```text
Circuit Assistant
────────────────────────

Prototype:
Book Light v3

3 boards
7 components
14 nets

Warnings:
2

Physical:
Controller connected

Simulation:
Running
```

Then the user says:

> Wire the light sensor into the available I²C bus.

The agent can answer:

> I found I²C0 using GPIO5/SDA and GPIO6/SCL. The sensor accepts 3.3 V. The bus currently has no pull-ups, so I would also add two 4.7 kΩ pull-ups to 3.3 V. No address conflict exists. Apply these changes?

Then show:

```text
[View proposed wiring]
[Apply]
[Cancel]
```

Apply updates the graph.

The wires physically appear.

The resistor components appear.

Simulation reruns.

That is the interaction you are envisioning.

---

# Keep the deterministic engineering systems underneath the AI

One of the most important principles:

**AI proposes and reasons. Engineering systems establish truth.**

Use:

```text
AI
↓
"What should we do?"

Rules engine
↓
"Is this connection valid?"

SPICE
↓
"What does the circuit electrically do?"

Hardware bridge
↓
"What is the physical device actually doing?"

Evidence system
↓
"What do we actually know?"
```

The model should never be the electrical simulator.

It should never be the voltage calculator of record.

It should never turn an inferred connection into a verified physical connection.

It operates the system that does those things.

That matches the philosophy already present in your existing application: physical-device claims are distinguished as verified, detected, declared, expected, inferred and unavailable rather than letting assumptions silently become facts. 

---

# The architecture I would lock in now

The completed prototype subsystem should therefore be:

```text
                    Prototype UI
            Physical / Logical / Editor
                        │
                        ▼
                Prototype Graph API
                        │
             canonical circuit state
                        │
       ┌────────────────┼────────────────┐
       │                │                │
       ▼                ▼                ▼
  Rules Engine     Simulation       Hardware Binding
                       │                │
                  CircuitJS /          Existing
                   ngspice          Device Service
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
                 Prototype Event Bus
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
           UI       Persistence   AI Service
                                  │
                                  ▼
                              LangGraph
                                  │
                                  ▼
                           Prototype Tools
                                  │
                                  ▼
                           Prototype Graph
```

The most important thing to establish **before** adding the LangGraph agent is that the Prototype Graph API is complete.

Once an agent can ask:

> What exists?

> What is connected?

> What values exist?

> What can I change?

> What happened?

> What is physically bound?

> What is simulated?

> What is invalid?

and can make structured changes through the same API the UI uses, the AI integration becomes straightforward.

Without that canonical graph and API, the AI is effectively staring at a picture.

With it, the AI becomes an actual **circuit-building engineering agent**.remeber this need to have the descion made of useing langchain and a class to itneract and change so we need specifcy all input outputs per pin The entire point, we want to ensure, which is very, very, very important, while you're building and rearranging and figuring out and planning out to build this prototype window and how we interact with it and how we can take the map signals that we've already gathered and how we can build from scratch, which would be a new view within the system, or the components library, or how we set it up to have the best user experience and to facilitate best design. Also, I'm hoping you're using ChatCN and you're using icons and all the best user experience performative measures that we need. We have to make sure that every single pin is represented. Now, I don't know if you know what a microcontroller board looks like, but you could probably go online and find some. And I just want to show you that I shared two pictures. The one that's 17, 15, and 21 millimeters is the ESP32-S3 Sensei, with the OV2640 camera. It's exactly what we're using. It's got Wi‑Fi, Bluetooth, and it's robotic, right? Then we have the other ESP, and now you see we got all those pinholes on the ends. Every little tiny circle on the end of the board is a pin. That's a point. That's a post. That's a pin where we can connect to the board to get signals back and forth. And you have to remember, we have to think that there's signals going out, signals going in, and we have to know which ones are which, right? So it's very important we very carefully map these out. That's why I think doing this prototype needs to be done separately, and we need to spend a lot of time methodically going through this to make sure every single thing is represented, is tested, and that we have AI ready. I'm going to go ahead and have the AI introduced on a new branch through the system, and so I want the prototype stuff to hold off for now. But...