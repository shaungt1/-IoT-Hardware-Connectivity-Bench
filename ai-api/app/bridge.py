from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import serial
from serial.tools import list_ports

from .protocol import PACKET_JPEG, PACKET_TELEMETRY, PacketParser


ESPRESSIF_VID = 0x303A


@dataclass
class BridgeState:
    connected: bool = False
    port: str | None = None
    error: str | None = None
    telemetry: dict[str, Any] = field(default_factory=dict)
    latest_frame: bytes | None = None
    frame_sequence: int = 0
    frame_received_at: float | None = None
    measured_fps: float = 0.0
    duplicate_frames: int = 0
    bytes_received: int = 0
    packets_received: int = 0
    started_at: float = field(default_factory=time.time)


class SerialBridge:
    def __init__(self, preferred_port: str | None = None) -> None:
        self._preferred_port = preferred_port
        self._serial: serial.Serial | None = None
        self._state = BridgeState()
        self._lock = threading.RLock()
        self._frame_condition = threading.Condition(self._lock)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._frame_times: deque[float] = deque(maxlen=120)
        self._frame_history: deque[tuple[int, float, bytes]] = deque(maxlen=16)

    @staticmethod
    def ports() -> list[dict[str, Any]]:
        return [
            {
                "id": f"serial:{port.device}",
                "kind": "serial",
                "device": port.device,
                "name": "ESP32-S3" if port.vid == ESPRESSIF_VID else port.description,
                "description": port.description,
                "manufacturer": port.manufacturer,
                "serial_number": port.serial_number,
                "vid": f"{port.vid:04X}" if port.vid is not None else None,
                "pid": f"{port.pid:04X}" if port.pid is not None else None,
                "is_esp32": port.vid == ESPRESSIF_VID,
                "is_lichee": False,
                "transport": "USB serial",
            }
            for port in list_ports.comports()
        ]

    def _find_port(self) -> str | None:
        with self._lock:
            preferred_port = self._preferred_port
        if preferred_port:
            available_ports = {port.device for port in list_ports.comports()}
            return preferred_port if preferred_port in available_ports else None
        candidates = [port for port in list_ports.comports() if port.vid == ESPRESSIF_VID]
        return candidates[0].device if candidates else None

    def select_port(self, port: str) -> None:
        available_ports = {item["device"] for item in self.ports()}
        if port not in available_ports:
            raise ValueError(f"Serial port {port} is not available")
        with self._lock:
            self._preferred_port = port
            self._state.port = port
            self._state.error = None
            self._state.telemetry = {}
            self._state.latest_frame = None
            self._state.frame_sequence = 0
            self._state.frame_received_at = None
            self._state.measured_fps = 0.0
            self._state.duplicate_frames = 0
            self._frame_times.clear()
            self._frame_history.clear()
        self._close()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="iot-bench-serial", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._close()

    def _close(self) -> None:
        connection = self._serial
        self._serial = None
        if connection and connection.is_open:
            try:
                connection.close()
            except serial.SerialException:
                pass
        with self._lock:
            self._state.connected = False
            self._state.port = None
            self._state.telemetry = {}
            self._state.latest_frame = None
            self._state.frame_sequence = 0
            self._state.frame_received_at = None
            self._state.measured_fps = 0.0
            self._state.duplicate_frames = 0
            self._state.bytes_received = 0
            self._state.packets_received = 0
            self._frame_times.clear()
            self._frame_history.clear()

    def _open(self, port: str) -> serial.Serial:
        connection = serial.Serial()
        connection.port = port
        connection.baudrate = 921600
        connection.timeout = 0.2
        connection.write_timeout = 2
        connection.dtr = False
        connection.rts = False
        connection.open()
        time.sleep(1.25)
        connection.reset_input_buffer()
        connection.write(b"STREAM ON\nSTATUS\n")
        connection.flush()
        return connection

    def _run(self) -> None:
        parser = PacketParser()
        while not self._stop.is_set():
            if self._serial is None:
                port = self._find_port()
                if port is None:
                    self._set_connection_error("ESP32-S3 USB serial device not found")
                    self._stop.wait(1.5)
                    continue
                try:
                    self._serial = self._open(port)
                    with self._lock:
                        self._state.connected = True
                        self._state.port = port
                        self._state.error = None
                except (OSError, serial.SerialException) as error:
                    self._set_connection_error(str(error))
                    self._close()
                    self._stop.wait(1.5)
                    continue

            try:
                chunk = self._serial.read(65536)
                if not chunk:
                    continue
                with self._lock:
                    self._state.bytes_received += len(chunk)
                for packet in parser.feed(chunk):
                    self._handle_packet(packet.packet_type, packet.sequence, packet.payload)
            except (OSError, serial.SerialException) as error:
                self._set_connection_error(str(error))
                self._close()

    def _set_connection_error(self, message: str) -> None:
        with self._lock:
            self._state.connected = False
            self._state.error = message

    def _handle_packet(self, packet_type: int, sequence: int, payload: bytes) -> None:
        now = time.time()
        with self._lock:
            self._state.packets_received += 1
            if packet_type == PACKET_TELEMETRY:
                try:
                    self._state.telemetry = json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._state.error = "Received malformed telemetry"
            elif packet_type == PACKET_JPEG and payload.startswith(b"\xff\xd8"):
                if self._state.latest_frame is not None and sequence == self._state.frame_sequence:
                    self._state.duplicate_frames += 1
                    return
                self._state.latest_frame = payload
                self._state.frame_sequence = sequence
                self._state.frame_received_at = now
                self._frame_history.append((sequence, now, payload))
                self._frame_times.append(now)
                while self._frame_times and now - self._frame_times[0] > 2:
                    self._frame_times.popleft()
                if len(self._frame_times) > 1:
                    elapsed = self._frame_times[-1] - self._frame_times[0]
                    self._state.measured_fps = (len(self._frame_times) - 1) / elapsed if elapsed else 0.0
                self._frame_condition.notify_all()

    def command(self, command: str) -> None:
        connection = self._serial
        if connection is None or not connection.is_open:
            raise RuntimeError("ESP32-S3 is not connected")
        connection.write(command.encode("utf-8") + b"\n")
        connection.flush()

    def configure_wifi(self, ssid: str, password: str, remember: bool = True) -> None:
        if not ssid.strip():
            raise ValueError("Wi-Fi SSID is required")
        if any(character in ssid or character in password for character in ("\t", "\r", "\n")):
            raise ValueError("Wi-Fi credentials cannot contain tabs or line breaks")
        prefix = "WIFI" if remember else "WIFI ONCE"
        self.command(f"{prefix}\t{ssid}\t{password}")

    def configure_device_access(self, name: str, password: str) -> None:
        if any(character in name or character in password for character in ("\t", "\r", "\n")):
            raise ValueError("Device access settings cannot contain tabs or line breaks")
        self.command(f"DEVICE\t{name}\t{password}" if password else f"NAME\t{name}")

    def configure_camera(self, setting: str, value: int) -> None:
        limits = {
            "brightness": (-2, 2),
            "contrast": (-2, 2),
            "saturation": (-2, 2),
            "sharpness": (-2, 2),
            "exposure": (-2, 2),
            "quality": (4, 63),
        }
        if setting not in limits:
            raise ValueError("Unsupported camera control")
        minimum, maximum = limits[setting]
        if value < minimum or value > maximum:
            raise ValueError(f"Camera {setting} must be between {minimum} and {maximum}")
        self.command(f"CAMERA\t{setting}\t{value}")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "connected": self._state.connected,
                "port": self._state.port,
                "error": self._state.error,
                "telemetry": dict(self._state.telemetry),
                "frame_sequence": self._state.frame_sequence,
                "frame_received_at": self._state.frame_received_at,
                "measured_fps": round(self._state.measured_fps, 2),
                "duplicate_frames": self._state.duplicate_frames,
                "bytes_received": self._state.bytes_received,
                "packets_received": self._state.packets_received,
                "bridge_uptime_seconds": round(time.time() - self._state.started_at, 1),
            }

    def latest_frame(self) -> bytes | None:
        with self._lock:
            return self._state.latest_frame

    def latest_frame_snapshot(self) -> tuple[int, bytes | None]:
        with self._lock:
            return self._state.frame_sequence, self._state.latest_frame

    def latest_frame_transport_snapshot(self) -> tuple[int, float | None, bytes | None]:
        with self._lock:
            return self._state.frame_sequence, self._state.frame_received_at, self._state.latest_frame

    def wait_for_frame(self, previous_sequence: int, timeout: float = 1.0) -> tuple[int, float | None, bytes | None]:
        """Block outside the asyncio loop until a newer complete JPEG is available."""
        with self._frame_condition:
            def next_frame() -> tuple[int, float, bytes] | None:
                if not self._frame_history:
                    return None
                if previous_sequence < 0:
                    return self._frame_history[-1]
                for index, item in enumerate(self._frame_history):
                    if item[0] == previous_sequence:
                        return self._frame_history[index + 1] if index + 1 < len(self._frame_history) else None
                return self._frame_history[-1] if self._frame_history[-1][0] != previous_sequence else None

            self._frame_condition.wait_for(lambda: next_frame() is not None, timeout=timeout)
            available = next_frame()
            if available is not None:
                return available
            return self._state.frame_sequence, self._state.frame_received_at, self._state.latest_frame

    def wait_for_latest_frame(self, previous_sequence: int, timeout: float = 1.0) -> tuple[int, float | None, bytes | None]:
        """Wait for a new frame and return only the newest JPEG.

        Camera clients must never replay a backlog: when decoding or network
        delivery falls behind, skipping stale frames preserves live latency.
        """
        with self._frame_condition:
            self._frame_condition.wait_for(
                lambda: self._state.latest_frame is not None and self._state.frame_sequence != previous_sequence,
                timeout=timeout,
            )
            return self._state.frame_sequence, self._state.frame_received_at, self._state.latest_frame
