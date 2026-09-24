Exactly. The catalog should be **board-first**, not chip-first. The board is what you physically buy and prototype with; underneath it we record the SoC, CPU, NPU/AI accelerator, RAM, camera interfaces, and software stack.

Your reference point is:

**Sipeed LicheeRV Nano → SOPHGO SG2002 → 1 TOPS INT8 NPU → RISC-V/ARM + Linux → 256 MB DDR3.** :chatgpt-content-reference{index="0"}

Here is the corrected board-level list I would use.

| Actual development board / device | Processor / AI silicon | AI compute | Architecture | Class / relationship to LicheeRV |
|---|---|---:|---|---|
| **Sipeed LicheeRV Nano** | SOPHGO SG2002 | **1 TOPS INT8** | RISC-V C906 / selectable Cortex-A53 + RISC-V secondary core | Reference board |
| **Milk-V Duo** | SOPHGO CV1800B | ~0.5 TOPS class | RISC-V | Tiny direct competitor |
| **Milk-V Duo 256M** | SOPHGO SG2002 | ~1 TOPS | RISC-V / ARM | Extremely close LicheeRV alternative |
| **Milk-V Duo S** | SOPHGO SG2000 | ~1 TOPS class | RISC-V / ARM | Direct SG-series alternative |
| **Luckfox Pico** | Rockchip RV1103 | **0.5 TOPS** | Cortex-A7 + MCU/NPU | Tiny Linux vision board |
| **Luckfox Pico Mini A** | RV1103 | **0.5 TOPS** | Cortex-A7 | Tiny module |
| **Luckfox Pico Mini B** | RV1103 | **0.5 TOPS** | Cortex-A7 | Tiny module + onboard flash |
| **Luckfox Pico Plus** | RV1103 | **0.5 TOPS** | Cortex-A7 | Expanded Pico |
| **Luckfox WebBee** | RV1103 | **0.5 TOPS** | Cortex-A7 | Embedded module |
| **Luckfox Pico Ultra** | RV1106G3 | **1 TOPS** | Cortex-A7 | Strong direct LicheeRV alternative |
| **Luckfox Pico Ultra W** | RV1106G3 | **1 TOPS** | Cortex-A7 | Ultra + Wi-Fi 6/Bluetooth |
| **Luckfox Pico Ultra B** | RV1106G2 | **0.5 TOPS** | Cortex-A7 | Lower-memory Ultra |
| **Luckfox Pico Ultra BW** | RV1106G2 | **0.5 TOPS** | Cortex-A7 | B + wireless |
| **Luckfox Pico Pi A** | RV1106G3 | **1 TOPS** | Cortex-A7 | Raspberry-Pi-style carrier |
| **Luckfox Pico Pi A W** | RV1106G3 | **1 TOPS** | Cortex-A7 | Pico Pi + wireless |
| **Luckfox Pico Pi B** | RV1106G2 | **0.5 TOPS** | Cortex-A7 | Lower-end Pico Pi |
| **Luckfox Pico Pi B W** | RV1106G2 | **0.5 TOPS** | Cortex-A7 | Lower-end + wireless |
| **Sipeed MaixCAM / CanMV-K230 class** | Kendryte K230 | ~**6 TOPS class** | Dual 64-bit RISC-V | Huge step up while remaining small |
| **Sipeed MAIX-III AXera-Pi** | Axera AX620A | **3.6 TOPS INT8 / 14.4 INT4** | Quad Cortex-A7 | Excellent dedicated AI vision board |
| **Milk-V Jupiter** | SpacemiT K1/M1 | **2 TOPS** | 8-core RISC-V | Larger RISC-V Linux edge computer |
| **Banana Pi BPI-F3** | SpacemiT K1 | **2 TOPS** | 8-core RISC-V | Industrial RISC-V SBC |
| **Orange Pi RV2** | Ky X1 | **2 TOPS AI compute** | 8-core RISC-V | RISC-V SBC / edge AI |
| **Orange Pi 5** | Rockchip RK3588S | **6 TOPS** | 4×A76 + 4×A55 | Powerful ARM edge-AI SBC |
| **Orange Pi 5B** | RK3588S | **6 TOPS** | ARM | Orange Pi 5 with extra connectivity/storage |
| **Orange Pi 5 Plus** | RK3588 | **6 TOPS** | ARM | Larger/high-I/O RK3588 board |
| **Radxa ROCK 5B** | RK3588 | **6 TOPS** | ARM | RK3588 Linux SBC |
| **Radxa ROCK 5B+** | RK3588 | **6 TOPS** | ARM | Newer/high-memory ROCK 5 |
| **D-Robotics RDK X3 / Sunrise X3 Pi** | Horizon/D-Robotics Sunrise X3 | **5 TOPS** | ARM + BPU | Dedicated robotics/vision SBC |
| **D-Robotics RDK X3 Module** | Sunrise X3 | **5 TOPS** | ARM + BPU | CM4-style AI module |
| **D-Robotics RDK X5** | Sunrise 5 | **10 TOPS** | 8× Cortex-A55 + BPU | Higher-performance robotics |
| **D-Robotics RDK X5 Module** | Sunrise 5 | **10 TOPS** | ARM + BPU | Production compute module |
| **BeagleBoard BeagleY-AI** | TI AM67A | **4 TOPS** | Cortex-A53 + TI accelerator | Industrial/open edge AI |
| **Arduino UNO Q 2GB** | Qualcomm Dragonwing QRB2210 + STM32U585 | Integrated AI acceleration | Quad Cortex-A53 + Cortex-M33 | Hybrid Linux + real-time MCU board |
| **Arduino UNO Q 4GB** | QRB2210 + STM32U585 | Integrated AI acceleration | ARM | More RAM/storage version |
| **Raspberry Pi 5 + AI HAT+ 13 TOPS** | BCM2712 + Hailo-8L | **13 TOPS** | ARM + discrete NPU | Modular AI SBC |
| **Raspberry Pi 5 + AI HAT+ 26 TOPS** | BCM2712 + Hailo-8 | **26 TOPS** | ARM + discrete NPU | Much heavier vision inference |
| **Raspberry Pi 5 + AI HAT+ 2** | BCM2712 + Hailo-10H + 8GB NPU RAM | **40 TOPS INT4** | ARM + discrete NPU | Vision + small LLM/VLM edge system |
| **NVIDIA Jetson Orin Nano Super Developer Kit** | Tegra Orin / Ampere Tensor Cores | **67 sparse TOPS / 33 dense** | ARM + NVIDIA GPU | High-performance AI computer |
| **NVIDIA Jetson Orin NX carrier/development systems** | Tegra Orin NX | up to **157 sparse TOPS** | ARM + CUDA/Tensor cores | Advanced robotics/vision |
| **Google Coral Dev Board** | NXP SoC + Google Edge TPU | **4 TOPS INT8** | ARM + Edge TPU | TFLite-centric edge AI |
| **Coral USB Accelerator + host board** | Google Edge TPU | **4 TOPS** | Discrete accelerator | Add AI to Linux SBC |
| **Hailo-8 M.2 modules + host SBC** | Hailo-8 | **26 TOPS INT8** | Discrete accelerator | Industrial inference |
| **Hailo-8L M.2 modules + host SBC** | Hailo-8L | **13 TOPS INT8** | Discrete accelerator | Low-power inference |
| **Hailo-10H modules + host** | Hailo-10H | **40 TOPS INT4** | Discrete accelerator | Vision + GenAI |
| **Seeed XIAO ESP32-S3 Sense** | ESP32-S3 | TinyML/vector acceleration, not a true TOPS-class NPU | Xtensa MCU | Much smaller TinyML class |
| **Seeed reComputer Jetson series** | Jetson Orin Nano/NX modules | depends on installed Orin | ARM + CUDA | Packaged commercial edge computer |
| **Seeed reComputer J-series** | NVIDIA Orin | tens–hundreds TOPS | ARM + GPU | Production robotics/AI box |

A few important corrections to the material you pasted:

**Luckfox Pico Mini is absolutely one of the boards you were looking for.** The RV1103 versions use a 1.2 GHz Cortex-A7, 64 MB DDR2 and a **0.5 TOPS NPU supporting INT4/INT8/INT16**. Luckfox actually has a whole RV1103 board family: Pico, Pico Mini A/B, Pico Plus and WebBee. :chatgpt-content-reference{index="1"}

The newer **Luckfox Pico Ultra** family is even more interesting. **Ultra/Ultra W use RV1106G3 with 256 MB DDR3L and 1 TOPS**, while Ultra B/BW use RV1106G2 with 128 MB and 0.5 TOPS. The W models additionally have Wi-Fi 6 + Bluetooth 5.2/BLE. :chatgpt-content-reference{index="2"}

That makes this progression particularly useful:

```text
LicheeRV Nano
SG2002
1 TOPS
256 MB
       │
       ├──────────────┐
       ▼              ▼
Milk-V Duo S      Luckfox Pico Ultra
SG2000            RV1106G3
~1 TOPS class     1 TOPS
RISC-V/ARM        Cortex-A7
       │              │
       └──────┬───────┘
              ▼
      Sipeed K230 boards
            K230
          ~6 TOPS
          RISC-V
              │
              ▼
      MAIX-III AXera-Pi
          AX620A
        3.6T INT8
              │
              ▼
          RDK X3
         5 TOPS
              │
              ▼
      Orange Pi 5 / ROCK 5
           RK3588
           6 TOPS
```

### The RISC-V branch is bigger than just LicheeRV

This is particularly relevant to what you're building because there is now a nice progression of **actual purchasable RISC-V boards**:

**Milk-V Duo → Duo 256M → Duo S → LicheeRV Nano → K230 boards → Milk-V Jupiter → Banana Pi BPI-F3 → Orange Pi RV2.**

The **Milk-V Jupiter** is based on SpacemiT K1/M1 and advertises **2 TOPS AI compute**, up to 16 GB LPDDR4X and a full Mini-ITX form factor. :chatgpt-content-reference{index="3"}

The **Banana Pi BPI-F3** uses the same SpacemiT K1 family, with an eight-core RISC-V processor and **2 TOPS AI compute**, up to 16 GB RAM, eMMC, dual MIPI cameras and PCIe. :chatgpt-content-reference{index="4"}

And **Orange Pi RV2** is another eight-core RISC-V board in this class, using the **Ky X1**, with **2 TOPS**, 2/4/8 GB LPDDR4X, dual four-lane MIPI CSI and dual M.2 sockets. :chatgpt-content-reference{index="5"}

So those three belong next to each other in our database.

### Then there is the Rockchip board ecosystem

Don't store merely:

> RK3588 — 6 TOPS

Store:

```text
Rockchip RK3588 / RK3588S
│
├── Orange Pi 5
├── Orange Pi 5B
├── Orange Pi 5 Plus
├── Radxa ROCK 5A
├── Radxa ROCK 5B
├── Radxa ROCK 5B+
└── many industrial compute modules
```

For example, the **Radxa ROCK 5B/5B+** use the RK3588 with an NPU supporting INT4, INT8, INT16, FP16, BF16 and TF32 and delivering **up to 6 TOPS**. :chatgpt-content-reference{index="6"}

That same distinction should exist everywhere in our catalog:

```text
MANUFACTURER
   ↓
PRODUCT FAMILY
   ↓
BOARD / MODULE
   ↓
SoC
   ↓
CPU
   ↓
AI ACCELERATOR
   ↓
MEMORY
   ↓
CAMERA / ISP
   ↓
I/O
   ↓
SDK / OS
```

### The MAIX boards are particularly relevant

Another one that absolutely should not just appear as **“AX620A”**:

**Sipeed MAIX-III AXera-Pi → Axera AX620A → 3.6 TOPS INT8 / 14.4 TOPS INT4 → quad Cortex-A7 → 2GB LPDDR4X → up to three cameras.** :chatgpt-content-reference{index="7"}

That's a real purchasable AI development board and is very much in the family you're asking about.

### D-Robotics/Horizon has actual boards too

Rather than merely listing “Horizon Sunrise X3,” use:

**D-Robotics RDK X3 / Sunrise X3 Pi → Sunrise X3 → 5 TOPS.**

Then:

**D-Robotics RDK X5 → Sunrise 5 → 10 TOPS.**

D-Robotics also sells **X3 Module and X5 Module** variants for building them into products. :chatgpt-content-reference{index="8"}

That product-module distinction is valuable for your system because you could select:

```text
Prototype:
RDK X5 complete SBC

Production:
RDK X5 Module
       +
custom carrier PCB
```

### BeagleY-AI

This should be:

**BeagleBoard BeagleY-AI → Texas Instruments AM67A → 4 TOPS → Cortex-A53 + TI C7x/MMA AI acceleration → 4GB LPDDR4 → multi-camera ISP.**

The official board documentation explicitly identifies the AM67A as a **4 TOPS vision SoC**. :chatgpt-content-reference{index="9"}

### Arduino UNO Q absolutely belongs in the database

This is another good example of why the board name matters.

**Arduino UNO Q 2GB / UNO Q 4GB → Qualcomm Dragonwing QRB2210 MPU + STM32U585 MCU.**

It is not merely an Arduino microcontroller anymore. The QRB2210 side is a **quad-core Cortex-A53 Linux processor with GPU, DSP/AI acceleration and dual ISP**, while the STM32U585 handles real-time hardware. It runs Debian and can run Docker. :chatgpt-content-reference{index="10"}

The two current board SKUs give you roughly:

```text
UNO Q 2GB
├── 2 GB LPDDR4
└── 16 GB eMMC

UNO Q 4GB
├── 4 GB LPDDR4
└── 32 GB eMMC
```

Arduino officially added the 4 GB version in January 2026. :chatgpt-content-reference{index="11"}

For your hardware system, I would categorize UNO Q as:

**Hybrid MPU + MCU Edge AI Board**

rather than grouping it with ESP32 or Raspberry Pi.

### Raspberry Pi is different again

The **Raspberry Pi 5 itself does not contain an NPU**.

But there are now three useful official configurations:

```text
Raspberry Pi 5
   │
   ├── AI HAT+ 13 TOPS
   │      └── Hailo-8L
   │
   ├── AI HAT+ 26 TOPS
   │      └── Hailo-8
   │
   └── AI HAT+ 2 40 TOPS
          └── Hailo-10H
              + 8 GB dedicated RAM
```

The new **AI HAT+ 2** is especially interesting because the 8 GB onboard memory lets the Hailo-10H run supported **LLMs and VLMs up to roughly six billion parameters**, in addition to conventional vision models. :chatgpt-content-reference{index="12"}

That is a completely different class than your LicheeRV, but it belongs in the same searchable **Edge AI Development Boards** category.

### And Jetson should be represented by actual kits/modules

Don't just store “Jetson.”

Store:

**NVIDIA Jetson Orin Nano Developer Kit**

**NVIDIA Jetson Orin Nano Super Developer Kit**

**Jetson Orin Nano 4GB module**

**Jetson Orin Nano 8GB module**

**Jetson Orin NX 8GB module**

**Jetson Orin NX 16GB module**

and then carrier-board systems from NVIDIA, Seeed, Waveshare, AAEON, etc.

The current Orin Nano Super configuration reaches **67 sparse TOPS / about 33 dense INT8 TOPS**, with six Cortex-A78AE CPU cores, 1,024 CUDA cores and 32 Tensor Cores. :chatgpt-content-reference{index="13"}

---

## The board catalog I would actually seed first

For **our virtual electronics/prototyping application**, I would make these the initial board families:

```text
EDGE AI / LINUX AI BOARDS

Sipeed
├── LicheeRV Nano
├── MAIX-III AXera-Pi
├── MaixCAM
└── K230 / CanMV boards

Milk-V
├── Duo
├── Duo 256M
├── Duo S
└── Jupiter

Luckfox
├── Pico
├── Pico Mini A
├── Pico Mini B
├── Pico Plus
├── WebBee
├── Pico Ultra
├── Pico Ultra W
├── Pico Ultra B
├── Pico Ultra BW
├── Pico Pi A
├── Pico Pi A W
├── Pico Pi B
└── Pico Pi B W

Orange Pi
├── Orange Pi RV2
├── Orange Pi 5
├── Orange Pi 5B
└── Orange Pi 5 Plus

Banana Pi
└── BPI-F3

Radxa
├── ROCK 5A
├── ROCK 5B
└── ROCK 5B+

D-Robotics
├── RDK X3
├── RDK X3 Module
├── RDK X5
└── RDK X5 Module

BeagleBoard
└── BeagleY-AI

Arduino
├── UNO Q 2GB
└── UNO Q 4GB

Raspberry Pi
├── Pi 5 + AI HAT+ 13T
├── Pi 5 + AI HAT+ 26T
└── Pi 5 + AI HAT+ 2 40T

NVIDIA
├── Jetson Orin Nano Dev Kit
├── Jetson Orin Nano Super Dev Kit
├── Jetson Orin Nano modules
└── Jetson Orin NX modules

Google Coral
├── Coral Dev Board
├── Coral Dev Board Mini
├── Coral USB Accelerator
└── Coral M.2 Accelerator
```

And **under each board record**, the application should then know the underlying silicon:

```text
BOARD:
Luckfox Pico Ultra W

manufacturer:
Luckfox

category:
Edge AI Development Board

soc:
Rockchip RV1106G3

cpu:
ARM Cortex-A7 @ 1.2 GHz

npu:
Rockchip NPU

aiPerformance:
1 TOPS

precisions:
INT4
INT8
INT16

memory:
256 MB DDR3L

storage:
8 GB eMMC

camera:
2-lane MIPI CSI

isp:
5 MP @ 30 FPS

network:
100 Mbps Ethernet
Wi-Fi 6
Bluetooth 5.2
BLE

interfaces:
GPIO
UART
SPI
I2C
USB
MIPI CSI
RGB666

os:
Buildroot Linux

boardType:
SBC / embedded vision board
```

**That is the data model we want.**

Then when you type:

> “Give me a tiny Linux board under 2 W with a camera interface and at least 0.5 TOPS”

our component engine can return **LicheeRV Nano, Milk-V Duo family, Luckfox Pico family, etc.**, rather than returning some fucking BGA chip that you can't simply plug into your prototype. :chatgpt-content-reference{index="14"}

And when you click the board, **then** we drill through:

**Board → SoC → NPU → CPU → ISP → pinout → electrical requirements → available cameras → SDK → compatible libraries.**

That's the hierarchy I think you were actually trying to get me to establish.

Yes. **The silicon list is much smaller than the board list**, because a dozen manufacturers can build different boards around the same Rockchip, SOPHGO, Hailo, etc.

I would structure our database exactly this way:

```text
AI HARDWARE CATALOG
│
├── SILICON
│   ├── SoC
│   ├── NPU / AI accelerator
│   ├── CPU architecture
│   ├── AI performance
│   └── supported precision
│
└── DEVICES
    ├── Development boards
    ├── Compute modules
    ├── SBCs
    ├── M.2 modules
    └── USB / PCIe accelerators
         │
         └── references SILICON record
```

So **Orange Pi 5, ROCK 5B, etc. don't each get duplicate RK3588 specifications**. They all reference one `Rockchip RK3588` silicon record.

## Consolidated Edge-AI Silicon Catalog

This is the useful **main-chip list** I would seed into our application. It covers the major silicon behind the boards we've been discussing plus several important families that weren't represented well in the previous board list.

| Manufacturer | Main chip / family | Type | AI performance | CPU / architecture | Example boards/devices |
|---|---|---|---:|---|---|
| **SOPHGO** | **CV1800B** | AI SoC | ~0.5 TOPS class | RISC-V | Milk-V Duo |
| **SOPHGO** | **SG2000** | AI SoC | ~1 TOPS class | RISC-V + ARM | Milk-V Duo S |
| **SOPHGO** | **SG2002** | AI SoC | ~1 TOPS | RISC-V + ARM | **LicheeRV Nano**, Milk-V Duo 256M |
| **Rockchip** | **RV1103** | Vision AI SoC | **0.5 TOPS** | Cortex-A7 + MCU | Luckfox Pico / Mini / Plus |
| **Rockchip** | **RV1106 / RV1106G2** | Vision AI SoC | **0.5 TOPS** | Cortex-A7 | Luckfox Pico Ultra B |
| **Rockchip** | **RV1106G3** | Vision AI SoC | **1 TOPS** | Cortex-A7 | Luckfox Pico Ultra / Ultra W |
| **Rockchip** | **RV1126** | Vision AI SoC | ~2 TOPS | Quad Cortex-A7 | Industrial AI cameras |
| **Rockchip** | **RK3566** | General AI SoC | ~0.8–1 TOPS | Quad Cortex-A55 | Orange Pi 3B-class boards |
| **Rockchip** | **RK3568** | Industrial AI SoC | ~0.8–1 TOPS | Quad Cortex-A55 | Industrial SBCs / CM boards |
| **Rockchip** | **RK3576** | AI SoC | ~6 TOPS | Cortex-A72/A53 class | Newer Radxa/embedded systems |
| **Rockchip** | **RK3588S** | AI SoC | **6 TOPS** | 4×A76 + 4×A55 | Orange Pi 5 / 5B |
| **Rockchip** | **RK3588** | AI SoC | **6 TOPS** | 4×A76 + 4×A55 | Orange Pi 5 Plus, ROCK 5B |
| **Kendryte / Canaan** | **K210** | AI MCU/SoC | ~1 TOPS class | Dual RISC-V | Maix Bit / older Maix boards |
| **Kendryte** | **K510** | AI SoC | ~2.5–3 TOPS class | RISC-V | K510 development platforms |
| **Kendryte** | **K230 / K230D** | AI Vision SoC | ~6 TOPS class | Dual 64-bit RISC-V | Sipeed MaixCAM / CanMV-K230 |
| **Allwinner** | **V853** | Vision AI SoC | **1 TOPS INT8** | Cortex-A7 + RISC-V E907 | V853 dev boards / camera modules |
| **Allwinner** | **V851S** | Vision AI SoC | ~1 TOPS class | ARM | Smart-camera boards |
| **SpacemiT** | **K1** | AI SoC | **2 TOPS class** | 8-core RISC-V | Banana Pi BPI-F3, Milk-V Jupiter |
| **SpacemiT** | **M1** | AI SoC | ~2 TOPS class | RISC-V | Milk-V / SpacemiT products |
| **Ky / KySilicon** | **X1** | AI SoC | **~2 TOPS** | 8-core RISC-V | Orange Pi RV2 |
| **Axera** | **AX620A** | Vision AI SoC | **3.6T INT8 / up to 14.4T INT4** | Cortex-A7 | Sipeed MAIX-III AXera-Pi |
| **Axera** | **AX620Q** | Vision AI SoC | Similar AX620 family | ARM | Embedded AI cameras |
| **Axera** | **AX630C** | Vision AI SoC | **3.2T INT8 / 12.8T INT4** | Dual Cortex-A53 | AX630C AI modules |
| **Axera** | **AX650N** | High-end Vision SoC | higher AI class | ARM | Edge-AI modules |
| **D-Robotics / Horizon** | **Sunrise X3** | Robotics AI SoC | **5 TOPS** | ARM + BPU | RDK X3 / X3 Module |
| **D-Robotics** | **Sunrise 5** | Robotics AI SoC | **10 TOPS** | 8× Cortex-A55 + BPU | RDK X5 / X5 Module |
| **TI** | **AM67A** | Vision AI SoC | **4 TOPS** | 4× Cortex-A53 + R5F + C7x/MMA | **BeagleY-AI**, TI EVM |
| **NXP** | **i.MX 8M Plus** | Industrial AI SoC | **2.3 TOPS** | Cortex-A53 + M7 | Variscite, Toradex, NXP EVK |
| **NXP** | **i.MX 93** | AI/industrial MPU | NPU integrated | Cortex-A55 + M33 | i.MX93 EVK / SOMs |
| **NXP** | **i.MX 95** | High-end industrial AI SoC | multi-TOPS NPU | Cortex-A55 + M7 | i.MX95 EVKs/modules |
| **Renesas** | **RZ/V2L** | Vision AI MPU | lower-power DRP-AI | Cortex-A55 | RZ/V2L EVK |
| **Renesas** | **RZ/V2N** | Vision AI MPU | **4 dense / 15 sparse TOPS** | 4× Cortex-A55 + M33 | RZ/V2N EVK |
| **Renesas** | **RZ/V2H** | High-end AI MPU | higher-performance DRP-AI | Cortex-A55 | Robotics / industrial boards |
| **Synaptics** | **Astra SL2610** | AI SoC | **1 TOPS** | Cortex-A55 + Cortex-M52 | Astra embedded platforms |
| **Qualcomm** | **QRB2210** | Robotics/IoT SoC | GPU/DSP AI, **not dedicated TOPS NPU** | Quad Cortex-A53 + Adreno + Hexagon | **Arduino UNO Q**, Qualcomm kits |
| **Qualcomm** | **QCS5430** | Edge AI SoC | multi-TOPS AI | ARM + Hexagon | Qualcomm/partner modules |
| **Qualcomm** | **QCS6490** | Edge AI SoC | ~12 TOPS-class advertised platforms | Kryo + Adreno + Hexagon | RB3 Gen 2-class hardware |
| **Qualcomm** | **IQ-8275** | High-end robotics SoC | **up to 40 dense TOPS** | ARM + AI accelerator | Arduino VENTUNO Q |
| **Google** | **Edge TPU** | Discrete NPU | **4 TOPS INT8** | NPU only | Coral USB / M.2 / Dev Board |
| **Hailo** | **Hailo-8L** | Discrete NPU | **13 TOPS** | NPU only | Pi AI HAT+, M.2 |
| **Hailo** | **Hailo-8** | Discrete NPU | **26 TOPS** | NPU only | Pi AI HAT+, M.2 / PCIe |
| **Hailo** | **Hailo-10H** | GenAI/vision accelerator | **40 TOPS INT4** | NPU accelerator | Pi AI HAT+ 2 / modules |
| **Kneron** | **KL520** | Discrete AI processor | low-power AI | NPU | USB/embedded modules |
| **Kneron** | **KL720** | Discrete AI processor | ~4 TOPS class | NPU | Kneron accelerator modules |
| **Kneron** | **KL730** | AI accelerator | newer/high-performance class | NPU | Edge modules |
| **NVIDIA** | **Jetson Orin Nano SoC/module** | GPU AI SoC | tens of TOPS | Cortex-A78AE + Ampere GPU | Jetson Orin Nano |
| **NVIDIA** | **Jetson Orin NX** | GPU AI SoC | much higher | Cortex-A78AE + Ampere GPU | Orin NX modules |
| **NVIDIA** | **Jetson AGX Orin** | GPU AI SoC | hundreds of TOPS class | ARM + Ampere GPU | AGX Orin |
| **Espressif** | **ESP32-S3** | MCU with vector AI instructions | **not NPU/TOPS-class** | Xtensa LX7 | XIAO ESP32-S3 Sense |
| **Ambarella** | **CV22 / CV25** | Vision AI SoC | CVflow accelerator | ARM + CVflow | Commercial cameras |
| **Ambarella** | **CV5 / CV7 family** | High-performance vision SoC | high-end CVflow | ARM + CVflow | Automotive / advanced vision |

A couple of these are worth distinguishing technically.

The **Allwinner V853**, for example, is a proper integrated AI SoC: Cortex-A7 + RISC-V E907 + **1 TOPS INT8 NPU**, ISP and camera interfaces on one chip. :chatgpt-content-reference{index="0"}

The **TI AM67A** has **two deep-learning accelerators totaling 4 TOPS**, alongside Cortex-A53 and R5F processors, ISP, vision accelerators and camera support. That's the silicon underneath boards such as BeagleY-AI. :chatgpt-content-reference{index="1"}

The **NXP i.MX 8M Plus** contains a dedicated **2.3 TOPS NPU**, dual ISP and dual MIPI CSI, which makes it particularly useful as a production/industrial alternative rather than only a hobby development board. :chatgpt-content-reference{index="2"}

And the current **Renesas RZ/V2N** is much further up the stack: Renesas specifies **4 TOPS dense / 15 TOPS sparse** DRP-AI3 performance, with four Cortex-A55 cores, Cortex-M33 and dual camera interfaces. :chatgpt-content-reference{index="3"}

---

## The key simplification

Once we deduplicate the boards, the stuff we're really choosing between becomes something like this:

```text
ULTRA-SMALL / LOW COST

CV1800B
SG2000
SG2002       ← LicheeRV Nano
RV1103
RV1106
V853
SL2610


RISC-V AI

CV1800B
SG2000
SG2002
K210
K230
SpacemiT K1
SpacemiT M1
Ky X1


MID-RANGE EDGE VISION

AX620A
AX630C
Sunrise X3
AM67A
i.MX 8M Plus
RK3576
RK3588


HIGHER-END EDGE / ROBOTICS

Sunrise 5
RZ/V2N
QCS6490
Hailo-8L
Hailo-8
Hailo-10H
Jetson Orin


DISCRETE NPU ONLY

Google Edge TPU
Hailo-8L
Hailo-8
Hailo-10H
Kneron KL520
Kneron KL720
Kneron KL730
```

D-Robotics is a good example of why this organization works: **RDK X3 and RDK X3 Module both point to Sunrise X3 / 5 TOPS**, while **RDK X5 and RDK X5 Module point to Sunrise 5 / 10 TOPS**. We don't need four copies of the silicon description. :chatgpt-content-reference{index="4"}

Likewise:

```text
RK3588
├── Orange Pi 5 Plus
├── Radxa ROCK 5B
├── ROCK 5B+
├── FriendlyElec boards
├── industrial SOMs
└── dozens of other products


SG2002
├── LicheeRV Nano
└── Milk-V Duo 256M


SpacemiT K1
├── Banana Pi BPI-F3
├── Milk-V Jupiter variants
└── other K1 modules


Sunrise X3
├── RDK X3
└── RDK X3 Module


Hailo-8
├── Raspberry Pi AI HAT+
├── M.2 modules
├── mini-PCIe systems
└── third-party SBC accelerators
```

That's **exactly why the chip table should be the canonical source**.

### One important correction from the earlier list

I would **not classify Arduino UNO Q's QRB2210 as a conventional dedicated NPU chip** the way we would an RK3588, Hailo-8 or SG2002. Qualcomm documents AI inference on its CPU/GPU and Hexagon DSP, but does not describe QRB2210 as having a standalone TOPS-rated NPU. :chatgpt-content-reference{index="5"}

So our database should be sophisticated enough to distinguish:

**Dedicated NPU**  
**BPU/TPU/DRP-AI accelerator**  
**GPU/Tensor acceleration**  
**DSP AI acceleration**  
**MCU SIMD/vector acceleration**

rather than calling all of them simply an NPU.

And no, even this table is **not every AI silicon part manufactured anywhere in the world**—there are hundreds of automotive ASICs, camera SoCs, NPUs and Chinese-market parts. But this is now a much closer representation of the **practical, obtainable edge-AI silicon ecosystem we'd want available in your prototyping application**. I would treat this as the core silicon library and then expand manufacturer families underneath it rather than endlessly adding duplicate boards.