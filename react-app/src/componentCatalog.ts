import type { PrototypeNode, PrototypePin } from "./types";

export interface CatalogPart {
  id: string;
  label: string;
  category: "Boards" | "Sensors" | "Inputs" | "Outputs" | "Displays" | "Modules" | "Passives";
  kind: PrototypeNode["kind"];
  element?: string;
  image?: string;
  pins: PrototypePin[];
  summary: string;
}

const pin = (id: string, functions: string[], direction: PrototypePin["direction"], voltage?: number): PrototypePin => ({ id, label: id, functions, direction, voltage });
const power = (id: string, voltage: number) => pin(id, ["Power"], "power", voltage);
const ground = (id = "GND") => pin(id, ["Ground"], "power", 0);
const gpio = (id: string, functions: string[] = ["GPIO"], direction: PrototypePin["direction"] = "bidirectional", voltage = 3.3) => pin(id, functions, direction, voltage);

function boardPin(id: string, logicVoltage = 3.3): PrototypePin {
  const base = id.split(".")[0].toUpperCase();
  if (base === "GND" || base === "VSS") return ground(id);
  if (base === "3V3" || base === "3.3V") return power(id, 3.3);
  if (base === "5V" || base === "VDD") return power(id, 5);
  if (base === "VIN") return power(id, 5);
  if (["IOREF", "AREF", "V0"].includes(base)) return pin(id, ["Voltage reference"], "input", logicVoltage);
  if (base === "RESET" || base === "EN") return gpio(id, ["Reset / enable"], "input", logicVoltage);
  if (base === "SDA" || base === "A4") return gpio(id, ["GPIO", "I2C SDA"], "bidirectional", logicVoltage);
  if (base === "SCL" || base === "A5") return gpio(id, ["GPIO", "I2C SCL"], "bidirectional", logicVoltage);
  if (["TX", "TX0", "TX2", "1"].includes(base)) return gpio(id, ["GPIO", "UART TX"], "output", logicVoltage);
  if (["RX", "RX0", "RX2", "0"].includes(base)) return gpio(id, ["GPIO", "UART RX"], "input", logicVoltage);
  if (/^A\d+$/.test(base)) return gpio(id, ["GPIO", "ADC"], "input", logicVoltage);
  return gpio(id, ["GPIO"], "bidirectional", logicVoltage);
}

const exactPins = (ids: string[], logicVoltage = 3.3) => ids.map((id) => boardPin(id, logicVoltage));
const esp32Pins = exactPins(["VIN", "GND.2", "D13", "D12", "D14", "D27", "D26", "D25", "D33", "D32", "D35", "D34", "VN", "VP", "EN", "3V3", "GND.1", "D15", "D2", "D4", "RX2", "TX2", "D5", "D18", "D19", "D21", "RX0", "TX0", "D22", "D23"]);
const unoPins = exactPins(["A5.2", "A4.2", "AREF", "GND.1", "13", "12", "11", "10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "0", "IOREF", "RESET", "3.3V", "5V", "GND.2", "GND.3", "VIN", "A0", "A1", "A2", "A3", "A4", "A5"], 5);
const nanoPins = exactPins(["12", "11", "10", "9", "8", "7", "6", "5", "4", "3", "2", "GND.2", "RESET.2", "0", "1", "13", "3.3V", "AREF", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "5V", "RESET", "GND.1", "VIN", "12.2", "5V.2", "13.2", "11.2", "RESET.3", "GND.3"], 5);
const megaPins = exactPins(["SCL", "SDA", "AREF", "GND.1", "13", "12", "11", "10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "0", "14", "15", "16", "17", "18", "19", "20", "21", "5V.1", "5V.2", ...Array.from({ length: 32 }, (_, index) => String(index + 22)), "GND.4", "GND.5", "IOREF", "RESET", "3.3V", "5V", "GND.2", "GND.3", "VIN", ...Array.from({ length: 16 }, (_, index) => `A${index}`)], 5);
const rp2040Pins = exactPins(["D12", "D11", "D10", "D9", "D8", "D7", "D6", "D5", "D4", "D3", "D2", "GND.1", "RESET", "RX", "TX", "D13", "3.3V", "AREF", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "5V", "RESET.2", "GND.2", "VIN"]);
const xiaoSensePins = [
  gpio("D0", ["GPIO", "ADC1_CH0", "Touch1"]), gpio("D1", ["GPIO", "ADC1_CH1", "Touch2"]), gpio("D2", ["GPIO", "ADC1_CH2", "Touch3"]), gpio("D3", ["GPIO", "ADC1_CH3", "Touch4"]),
  gpio("D4", ["GPIO", "I2C SDA", "ADC1_CH4", "Touch5"]), gpio("D5", ["GPIO", "I2C SCL", "ADC1_CH5", "Touch6"]), gpio("D6", ["GPIO", "UART TX"], "output"), gpio("D7", ["GPIO", "UART RX"], "input"),
  gpio("D8", ["GPIO", "SPI SCK", "ADC1_CH6", "Touch7"]), gpio("D9", ["GPIO", "SPI MISO", "ADC1_CH7", "Touch8"]), gpio("D10", ["GPIO", "SPI MOSI", "ADC1_CH8", "Touch9"]), power("3V3", 3.3), ground(), power("5V", 5),
];

export const componentCatalog: CatalogPart[] = [
  { id: "seeed_xiao_esp32s3_sense", label: "XIAO ESP32-S3 Sense", category: "Boards", kind: "controller", image: "/boards/seeed-xiao-esp32s3-sense.jpg", pins: xiaoSensePins, summary: "14-pad ESP32-S3 camera, microphone, microSD, Wi-Fi and BLE board" },
  { id: "wokwi-esp32-devkit-v1", label: "ESP32 DevKit V1", category: "Boards", kind: "controller", element: "wokwi-esp32-devkit-v1", pins: esp32Pins, summary: "30-pin ESP32 development board" },
  { id: "wokwi-arduino-uno", label: "Arduino Uno", category: "Boards", kind: "controller", element: "wokwi-arduino-uno", pins: unoPins, summary: "31 exposed ATmega328P board terminals" },
  { id: "wokwi-arduino-nano", label: "Arduino Nano", category: "Boards", kind: "controller", element: "wokwi-arduino-nano", pins: nanoPins, summary: "30 edge pins plus 6 ICSP terminals" },
  { id: "wokwi-arduino-mega", label: "Arduino Mega", category: "Boards", kind: "controller", element: "wokwi-arduino-mega", pins: megaPins, summary: "85 exposed ATmega2560 board terminals" },
  { id: "wokwi-nano-rp2040-connect", label: "Nano RP2040 Connect", category: "Boards", kind: "controller", element: "wokwi-nano-rp2040-connect", pins: rp2040Pins, summary: "30-pin RP2040 board with Wi-Fi and BLE" },
  { id: "wokwi-dht22", label: "DHT22", category: "Sensors", kind: "sensor", element: "wokwi-dht22", pins: [power("VCC", 3.3), gpio("SDA", ["Single-wire data"]), pin("NC", ["Not connected"], "unknown"), ground()], summary: "Temperature and humidity sensor" },
  { id: "wokwi-mpu6050", label: "MPU6050 IMU", category: "Sensors", kind: "sensor", element: "wokwi-mpu6050", pins: [gpio("INT", ["Interrupt"], "output"), gpio("AD0", ["I2C address select"], "input"), gpio("XCL", ["Auxiliary I2C clock"]), gpio("XDA", ["Auxiliary I2C data"]), gpio("SDA", ["I2C SDA"]), gpio("SCL", ["I2C SCL"]), ground(), power("VCC", 3.3)], summary: "8-terminal 6-axis accelerometer and gyroscope" },
  { id: "wokwi-hc-sr04", label: "HC-SR04", category: "Sensors", kind: "sensor", element: "wokwi-hc-sr04", pins: [power("VCC", 5), gpio("TRIG", ["Trigger"], "input", 5), gpio("ECHO", ["Echo"], "output", 5), ground()], summary: "Ultrasonic distance sensor" },
  { id: "wokwi-pir-motion-sensor", label: "PIR motion sensor", category: "Sensors", kind: "sensor", element: "wokwi-pir-motion-sensor", pins: [power("VCC", 5), gpio("OUT", ["Digital output"], "output", 3.3), ground()], summary: "Passive infrared motion sensor" },
  { id: "wokwi-photoresistor-sensor", label: "Photoresistor module", category: "Sensors", kind: "sensor", element: "wokwi-photoresistor-sensor", pins: [power("VCC", 5), ground(), gpio("DO", ["Digital output"], "output", 5), gpio("AO", ["Analog output"], "output", 5)], summary: "Light level sensor module" },
  { id: "wokwi-potentiometer", label: "Potentiometer", category: "Inputs", kind: "sensor", element: "wokwi-potentiometer", pins: [ground(), gpio("SIG", ["Analog output"], "output", 5), power("VCC", 5)], summary: "Adjustable analog input" },
  { id: "wokwi-pushbutton", label: "Pushbutton", category: "Inputs", kind: "sensor", element: "wokwi-pushbutton", pins: [pin("1.l", ["Switch terminal 1"], "bidirectional"), pin("2.l", ["Switch terminal 2"], "bidirectional"), pin("1.r", ["Switch terminal 1"], "bidirectional"), pin("2.r", ["Switch terminal 2"], "bidirectional")], summary: "Four-lead momentary digital input" },
  { id: "wokwi-led", label: "LED", category: "Outputs", kind: "output", element: "wokwi-led", pins: [pin("A", ["Anode"], "input", 3.3), ground("C")], summary: "Single-color light output" },
  { id: "wokwi-rgb-led", label: "RGB LED", category: "Outputs", kind: "output", element: "wokwi-rgb-led", pins: [gpio("R", ["PWM"], "input"), ground("COM"), gpio("G", ["PWM"], "input"), gpio("B", ["PWM"], "input")], summary: "Three-channel color light" },
  { id: "wokwi-servo", label: "Servo", category: "Outputs", kind: "output", element: "wokwi-servo", pins: [ground(), power("V+", 5), gpio("PWM", ["PWM"], "input", 5)], summary: "Position-controlled actuator" },
  { id: "wokwi-ssd1306", label: "SSD1306 OLED", category: "Displays", kind: "output", element: "wokwi-ssd1306", pins: [gpio("DATA", ["Display data"]), gpio("CLK", ["Display clock"], "input"), gpio("DC", ["Data / command"], "input"), gpio("RST", ["Reset"], "input"), gpio("CS", ["Chip select"], "input"), power("3V3", 3.3), power("VIN", 5), ground()], summary: "8-terminal 128x64 OLED display" },
  { id: "wokwi-lcd1602", label: "LCD1602", category: "Displays", kind: "output", element: "wokwi-lcd1602", pins: [ground("VSS"), power("VDD", 5), pin("V0", ["Contrast voltage"], "input", 5), gpio("RS", ["Register select"], "input", 5), gpio("RW", ["Read / write"], "input", 5), gpio("E", ["Enable"], "input", 5), ...Array.from({ length: 8 }, (_, index) => gpio(`D${index}`, ["Parallel data"], "bidirectional", 5)), power("A", 5), ground("K")], summary: "16-terminal parallel 16x2 character display" },
  { id: "wokwi-franzininho", label: "Franzininho", category: "Boards", kind: "controller", element: "wokwi-franzininho", pins: [], summary: "ATtiny85 development board visual with package-defined terminals" },
  { id: "wokwi-big-sound-sensor", label: "Big sound sensor", category: "Sensors", kind: "sensor", element: "wokwi-big-sound-sensor", pins: [], summary: "Microphone sound level module" },
  { id: "wokwi-small-sound-sensor", label: "Small sound sensor", category: "Sensors", kind: "sensor", element: "wokwi-small-sound-sensor", pins: [], summary: "Compact microphone sound module" },
  { id: "wokwi-flame-sensor", label: "Flame sensor", category: "Sensors", kind: "sensor", element: "wokwi-flame-sensor", pins: [], summary: "Infrared flame detection module" },
  { id: "wokwi-gas-sensor", label: "Gas sensor", category: "Sensors", kind: "sensor", element: "wokwi-gas-sensor", pins: [], summary: "MQ-style gas sensing module" },
  { id: "wokwi-heart-beat-sensor", label: "Heartbeat sensor", category: "Sensors", kind: "sensor", element: "wokwi-heart-beat-sensor", pins: [], summary: "Optical pulse sensor module" },
  { id: "wokwi-ntc-temperature-sensor", label: "NTC temperature sensor", category: "Sensors", kind: "sensor", element: "wokwi-ntc-temperature-sensor", pins: [], summary: "Thermistor temperature module" },
  { id: "wokwi-analog-joystick", label: "Analog joystick", category: "Inputs", kind: "sensor", element: "wokwi-analog-joystick", pins: [], summary: "Two-axis analog joystick with push switch" },
  { id: "wokwi-dip-switch-8", label: "8-position DIP switch", category: "Inputs", kind: "sensor", element: "wokwi-dip-switch-8", pins: [], summary: "Eight independent configuration switches" },
  { id: "wokwi-ir-remote", label: "IR remote", category: "Inputs", kind: "sensor", element: "wokwi-ir-remote", pins: [], summary: "Infrared handheld remote visual" },
  { id: "wokwi-ky-040", label: "KY-040 rotary encoder", category: "Inputs", kind: "sensor", element: "wokwi-ky-040", pins: [], summary: "Incremental rotary encoder module" },
  { id: "wokwi-membrane-keypad", label: "Membrane keypad", category: "Inputs", kind: "sensor", element: "wokwi-membrane-keypad", pins: [], summary: "Matrix keypad input" },
  { id: "wokwi-pushbutton-6mm", label: "6 mm pushbutton", category: "Inputs", kind: "sensor", element: "wokwi-pushbutton-6mm", pins: [], summary: "Compact momentary switch" },
  { id: "wokwi-rotary-dialer", label: "Rotary dialer", category: "Inputs", kind: "sensor", element: "wokwi-rotary-dialer", pins: [], summary: "Pulse-dial telephone input" },
  { id: "wokwi-slide-potentiometer", label: "Slide potentiometer", category: "Inputs", kind: "sensor", element: "wokwi-slide-potentiometer", pins: [], summary: "Linear analog input" },
  { id: "wokwi-slide-switch", label: "Slide switch", category: "Inputs", kind: "sensor", element: "wokwi-slide-switch", pins: [], summary: "Maintained changeover switch" },
  { id: "wokwi-tilt-switch", label: "Tilt switch", category: "Inputs", kind: "sensor", element: "wokwi-tilt-switch", pins: [], summary: "Orientation-triggered switch" },
  { id: "wokwi-biaxial-stepper", label: "Biaxial stepper", category: "Outputs", kind: "output", element: "wokwi-biaxial-stepper", pins: [], summary: "Two-axis stepper mechanism" },
  { id: "wokwi-buzzer", label: "Piezo buzzer", category: "Outputs", kind: "output", element: "wokwi-buzzer", pins: [], summary: "Piezoelectric audio output" },
  { id: "wokwi-ks2e-m-dc5", label: "KS2E-M-DC5 relay", category: "Outputs", kind: "output", element: "wokwi-ks2e-m-dc5", pins: [], summary: "Dual-coil signal relay" },
  { id: "wokwi-led-bar-graph", label: "LED bar graph", category: "Outputs", kind: "output", element: "wokwi-led-bar-graph", pins: [], summary: "Ten-segment LED indicator" },
  { id: "wokwi-led-ring", label: "LED ring", category: "Outputs", kind: "output", element: "wokwi-led-ring", pins: [], summary: "Addressable circular LED array" },
  { id: "wokwi-neopixel", label: "NeoPixel", category: "Outputs", kind: "output", element: "wokwi-neopixel", pins: [], summary: "Addressable RGB LED" },
  { id: "wokwi-neopixel-matrix", label: "NeoPixel matrix", category: "Outputs", kind: "output", element: "wokwi-neopixel-matrix", pins: [], summary: "Addressable RGB LED matrix" },
  { id: "wokwi-stepper-motor", label: "Stepper motor", category: "Outputs", kind: "output", element: "wokwi-stepper-motor", pins: [], summary: "Four-phase stepper motor" },
  { id: "wokwi-7segment", label: "Seven-segment display", category: "Displays", kind: "output", element: "wokwi-7segment", pins: [], summary: "Single-digit LED display" },
  { id: "wokwi-ili9341", label: "ILI9341 TFT", category: "Displays", kind: "output", element: "wokwi-ili9341", pins: [], summary: "Color SPI TFT display" },
  { id: "wokwi-lcd2004", label: "LCD2004", category: "Displays", kind: "output", element: "wokwi-lcd2004", pins: [], summary: "20x4 character LCD" },
  { id: "wokwi-ds1307", label: "DS1307 RTC", category: "Modules", kind: "sensor", element: "wokwi-ds1307", pins: [], summary: "I2C real-time clock module" },
  { id: "wokwi-hx711", label: "HX711 load-cell interface", category: "Modules", kind: "sensor", element: "wokwi-hx711", pins: [], summary: "24-bit load-cell ADC module" },
  { id: "wokwi-ir-receiver", label: "IR receiver", category: "Modules", kind: "sensor", element: "wokwi-ir-receiver", pins: [], summary: "Demodulating infrared receiver" },
  { id: "wokwi-microsd-card", label: "MicroSD card module", category: "Modules", kind: "passive", element: "wokwi-microsd-card", pins: [], summary: "SPI removable storage module" },
  { id: "wokwi-resistor", label: "Resistor", category: "Passives", kind: "passive", element: "wokwi-resistor", pins: [pin("1", ["Passive terminal"], "bidirectional"), pin("2", ["Passive terminal"], "bidirectional")], summary: "Current limiting and pull-up resistor" },
];

export function catalogPart(id?: string) { return componentCatalog.find((part) => part.id === id); }
export interface ComponentVisual { element?: string; image?: string; accuracy: string }

export function visualForComponent(component: PrototypeNode): ComponentVisual | null {
  const known = catalogPart(component.component_id);
  if (known) return { element: known.element, image: known.image, accuracy: "exact catalog part" };
  const identity = `${component.component_id || ""} ${component.label}`.toLowerCase();
  if (identity.includes("xiao") && identity.includes("esp32") && identity.includes("sense")) return { image: "/boards/seeed-xiao-esp32s3-sense.jpg", accuracy: "official Seeed Studio XIAO ESP32-S3 Sense product visual" };
  if (identity.includes("esp32")) return { element: "wokwi-esp32-devkit-v1", accuracy: "representative ESP32 visual; exact board unresolved" };
  if (identity.includes("arduino uno")) return { element: "wokwi-arduino-uno", accuracy: "matched board visual" };
  if (identity.includes("arduino nano")) return { element: "wokwi-arduino-nano", accuracy: "matched board visual" };
  if (identity.includes("rp2040")) return { element: "wokwi-nano-rp2040-connect", accuracy: "representative RP2040 visual" };
  return null;
}
