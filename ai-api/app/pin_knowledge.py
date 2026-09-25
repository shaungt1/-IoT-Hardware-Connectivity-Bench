from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


PIN_KNOWLEDGE: dict[str, dict[str, str]] = {
    "gpio": {
        "canonical": "GPIO",
        "category": "digital",
        "summary": "General-purpose digital input or output. Direction, voltage, and drive strength must be verified before use.",
        "caution": "Never drive an unknown or externally driven line until its voltage and direction are known.",
    },
    "adc": {
        "canonical": "ADC",
        "category": "analog",
        "summary": "Analog-to-digital input used to measure a voltage within the controller's supported range.",
        "caution": "Input voltage must remain inside the documented ADC and reference-voltage limits.",
    },
    "dac": {
        "canonical": "DAC",
        "category": "analog",
        "summary": "Digital-to-analog output that produces a programmable voltage or waveform.",
        "caution": "Output range and source current are device-specific and may require buffering.",
    },
    "pwm": {
        "canonical": "PWM",
        "category": "digital",
        "summary": "Pulse-width-modulated output used for dimming, motor control, servos, and approximate analog output.",
        "caution": "Loads such as motors and high-current LEDs require a suitable driver and protection circuit.",
    },
    "sda": {
        "canonical": "I2C SDA",
        "category": "bus",
        "summary": "Bidirectional I2C data line shared by addressed devices on the same bus.",
        "caution": "The bus normally needs pull-up resistors and all devices must tolerate the selected voltage.",
    },
    "scl": {
        "canonical": "I2C SCL",
        "category": "bus",
        "summary": "I2C clock line driven by the controller and shared by devices on the bus.",
        "caution": "Check pull-ups, clock speed, voltage, and clock-stretching support.",
    },
    "mosi": {
        "canonical": "SPI MOSI / COPI",
        "category": "bus",
        "summary": "SPI data from controller to peripheral.",
        "caution": "SPI devices also require a compatible clock mode and an explicit chip-select connection.",
    },
    "miso": {
        "canonical": "SPI MISO / CIPO",
        "category": "bus",
        "summary": "SPI data from peripheral to controller.",
        "caution": "Multiple peripherals must release this line when their chip-select is inactive.",
    },
    "sck": {
        "canonical": "SPI SCK / SCLK",
        "category": "bus",
        "summary": "SPI serial clock from controller to peripheral.",
        "caution": "Clock frequency and polarity/phase must match the peripheral.",
    },
    "cs": {
        "canonical": "SPI CS / SS",
        "category": "bus",
        "summary": "SPI chip-select line used to choose one peripheral.",
        "caution": "Its active level and boot-time state are device-specific.",
    },
    "tx": {
        "canonical": "UART TX",
        "category": "bus",
        "summary": "Asynchronous serial transmit signal.",
        "caution": "Connect to the peer's RX and verify logic voltage, baud rate, and polarity before transmitting.",
    },
    "rx": {
        "canonical": "UART RX",
        "category": "bus",
        "summary": "Asynchronous serial receive signal.",
        "caution": "Connect to the peer's TX and verify voltage compatibility; RS-232 levels are not logic UART levels.",
    },
    "gnd": {
        "canonical": "Ground",
        "category": "power",
        "summary": "Electrical reference and current return path shared by the connected circuit.",
        "caution": "A common ground is normally required, but unsafe ground loops and high currents must be avoided.",
    },
    "power": {
        "canonical": "Power rail",
        "category": "power",
        "summary": "Supply or raw input rail. The exact voltage, direction, and current limit come from the board definition.",
        "caution": "Do not infer voltage from position or color; verify the board-specific rail before connecting it.",
    },
    "reset": {
        "canonical": "Reset",
        "category": "control",
        "summary": "Hardware reset control for the processor or board.",
        "caution": "The active level and whether the pin tolerates external drive are board-specific.",
    },
    "enable": {
        "canonical": "Enable",
        "category": "control",
        "summary": "Enables a regulator, peripheral, radio, or the complete board.",
        "caution": "Changing it can remove power or alter boot behavior.",
    },
    "boot": {
        "canonical": "Boot strap",
        "category": "control",
        "summary": "A boot-mode strap sampled during reset to choose startup or programming behavior.",
        "caution": "External circuitry can prevent normal boot or accidentally enter a programming mode.",
    },
}

ALIASES = {
    "sclk": "sck", "clk": "sck", "copi": "mosi", "cipo": "miso", "ss": "cs",
    "txd": "tx", "rxd": "rx", "ground": "gnd", "rst": "reset", "en": "enable",
    "3v3": "power", "3.3v": "power", "5v": "power", "vcc": "power", "vin": "power",
    "vbus": "power", "vbat": "power", "bat": "power",
}


def _tokens(pin: dict[str, Any]) -> set[str]:
    values = [pin.get("name", ""), *pin.get("aliases", []), *pin.get("functions", [])]
    tokens: set[str] = set()
    for value in values:
        normalized = str(value).lower().replace("i²c", "i2c")
        tokens.update(part for part in re.split(r"[^a-z0-9.]+", normalized) if part)
    return tokens


def annotate_pins(pins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = []
    for original in pins:
        pin = deepcopy(original)
        keys: list[str] = []
        tokens = _tokens(pin)
        for token in tokens:
            key = ALIASES.get(token, token)
            if key in PIN_KNOWLEDGE and key not in keys:
                keys.append(key)
        if not keys and any(token.startswith(("d", "a", "gpio")) for token in tokens):
            keys.append("gpio")
        pin["knowledge"] = [{"id": key, **PIN_KNOWLEDGE[key]} for key in keys]
        annotated.append(pin)
    return annotated
