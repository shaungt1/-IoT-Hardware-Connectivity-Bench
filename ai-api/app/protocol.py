from __future__ import annotations

from dataclasses import dataclass


MAGIC = b"IOTB"
LEGACY_MAGICS = (b"LMNI",)
ACCEPTED_MAGICS = (MAGIC, *LEGACY_MAGICS)
HEADER_SIZE = 13
PACKET_TELEMETRY = 1
PACKET_JPEG = 2
MAX_PAYLOAD_SIZE = 2_000_000


@dataclass(frozen=True)
class Packet:
    packet_type: int
    sequence: int
    payload: bytes


class PacketParser:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[Packet]:
        self._buffer.extend(data)
        packets: list[Packet] = []

        while True:
            markers = [(position, magic) for magic in ACCEPTED_MAGICS if (position := self._buffer.find(magic)) >= 0]
            if not markers:
                if len(self._buffer) > len(MAGIC) - 1:
                    del self._buffer[: -(len(MAGIC) - 1)]
                break
            marker, _ = min(markers, key=lambda match: match[0])
            if marker:
                del self._buffer[:marker]
            if len(self._buffer) < HEADER_SIZE:
                break

            packet_type = self._buffer[4]
            length = int.from_bytes(self._buffer[5:9], "little")
            sequence = int.from_bytes(self._buffer[9:13], "little")
            if length > MAX_PAYLOAD_SIZE:
                del self._buffer[0]
                continue
            if len(self._buffer) < HEADER_SIZE + length:
                break

            payload = bytes(self._buffer[HEADER_SIZE : HEADER_SIZE + length])
            del self._buffer[: HEADER_SIZE + length]
            packets.append(Packet(packet_type, sequence, payload))

        return packets


def encode_packet(packet_type: int, sequence: int, payload: bytes) -> bytes:
    return (
        MAGIC
        + bytes((packet_type,))
        + len(payload).to_bytes(4, "little")
        + sequence.to_bytes(4, "little")
        + payload
    )
