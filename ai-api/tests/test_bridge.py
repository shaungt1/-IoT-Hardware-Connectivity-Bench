from app.bridge import SerialBridge
from app.protocol import PACKET_JPEG


def test_bridge_does_not_count_duplicate_sequence_as_new_camera_frame() -> None:
    bridge = SerialBridge()
    jpeg = b"\xff\xd8fixture\xff\xd9"
    bridge._handle_packet(PACKET_JPEG, 7, jpeg)
    bridge._handle_packet(PACKET_JPEG, 7, jpeg)
    snapshot = bridge.snapshot()
    assert snapshot["frame_sequence"] == 7
    assert snapshot["duplicate_frames"] == 1
    assert snapshot["measured_fps"] == 0


def test_wait_for_frame_returns_already_available_new_sequence() -> None:
    bridge = SerialBridge()
    bridge._handle_packet(PACKET_JPEG, 9, b"\xff\xd8fixture\xff\xd9")
    sequence, _, frame = bridge.wait_for_frame(8, timeout=0.01)
    assert sequence == 9
    assert frame == b"\xff\xd8fixture\xff\xd9"


def test_wait_for_frame_preserves_bursted_frames_for_each_client() -> None:
    bridge = SerialBridge()
    bridge._handle_packet(PACKET_JPEG, 10, b"\xff\xd8one\xff\xd9")
    bridge._handle_packet(PACKET_JPEG, 11, b"\xff\xd8two\xff\xd9")
    bridge._handle_packet(PACKET_JPEG, 12, b"\xff\xd8three\xff\xd9")
    assert bridge.wait_for_frame(10, timeout=0.01)[0] == 11
    assert bridge.wait_for_frame(11, timeout=0.01)[0] == 12
    assert bridge.wait_for_frame(10, timeout=0.01)[0] == 11


def test_wait_for_latest_frame_skips_stale_burst() -> None:
    bridge = SerialBridge()
    bridge._handle_packet(PACKET_JPEG, 20, b"\xff\xd8one\xff\xd9")
    bridge._handle_packet(PACKET_JPEG, 21, b"\xff\xd8two\xff\xd9")
    bridge._handle_packet(PACKET_JPEG, 22, b"\xff\xd8latest\xff\xd9")

    sequence, _, frame = bridge.wait_for_latest_frame(20, timeout=0.01)

    assert sequence == 22
    assert frame == b"\xff\xd8latest\xff\xd9"
