from app.protocol import PACKET_JPEG, PACKET_TELEMETRY, PacketParser, encode_packet


def test_parser_handles_fragmented_packets_and_noise() -> None:
    telemetry = encode_packet(PACKET_TELEMETRY, 7, b'{"ok":true}')
    jpeg = encode_packet(PACKET_JPEG, 8, b"\xff\xd8frame\xff\xd9")
    parser = PacketParser()

    assert parser.feed(b"startup text" + telemetry[:9]) == []
    packets = parser.feed(telemetry[9:] + jpeg)

    assert [packet.packet_type for packet in packets] == [PACKET_TELEMETRY, PACKET_JPEG]
    assert packets[0].sequence == 7
    assert packets[1].payload.startswith(b"\xff\xd8")

