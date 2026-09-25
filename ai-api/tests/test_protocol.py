from app.protocol import MAGIC, PACKET_JPEG, PACKET_TELEMETRY, PacketParser, encode_packet


def test_parser_handles_fragmented_packets_and_noise() -> None:
    telemetry = encode_packet(PACKET_TELEMETRY, 7, b'{"ok":true}')
    jpeg = encode_packet(PACKET_JPEG, 8, b"\xff\xd8frame\xff\xd9")
    parser = PacketParser()

    assert parser.feed(b"startup text" + telemetry[:9]) == []
    packets = parser.feed(telemetry[9:] + jpeg)

    assert [packet.packet_type for packet in packets] == [PACKET_TELEMETRY, PACKET_JPEG]
    assert packets[0].sequence == 7
    assert packets[1].payload.startswith(b"\xff\xd8")


def test_encoder_uses_neutral_magic_and_parser_accepts_legacy_firmware() -> None:
    encoded = encode_packet(PACKET_TELEMETRY, 9, b"{}")
    assert encoded.startswith(MAGIC)
    assert MAGIC == b"IOTB"

    legacy = b"LMNI" + bytes((PACKET_TELEMETRY,)) + (2).to_bytes(4, "little") + (10).to_bytes(4, "little") + b"{}"
    packets = PacketParser().feed(legacy)

    assert len(packets) == 1
    assert packets[0].sequence == 10
