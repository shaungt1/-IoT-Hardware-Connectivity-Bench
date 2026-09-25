from app.adapters.firmata import END_SYSEX, REPORT_FIRMWARE, START_SYSEX, FirmataAdapter, _query_firmata


class FakeSerial:
    written = b""

    def __init__(self, *_args, **_kwargs) -> None:
        name = "StandardFirmata"
        encoded = b"".join(bytes((ord(character) & 0x7F, ord(character) >> 7)) for character in name)
        self.response = bytearray(bytes((START_SYSEX, REPORT_FIRMWARE, 2, 5)) + encoded + bytes((END_SYSEX,)))

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def reset_input_buffer(self) -> None:
        return None

    def write(self, value: bytes) -> None:
        FakeSerial.written = value

    def flush(self) -> None:
        return None

    def read(self, _size: int) -> bytes:
        value = bytes(self.response)
        self.response.clear()
        return value


def test_firmata_adapter_does_not_claim_runtime_from_usb_identity() -> None:
    adapter = FirmataAdapter()
    profile = {"kind": "serial", "device": "COM8", "vid": "2341", "pid": "0043"}
    result = adapter.inspect_passive(profile)
    assert adapter.supports(profile)
    assert result["evidence"][0]["status"] == "detected"
    assert result["tests"][0]["risk"] == "disruptive"


def test_firmata_handshake_parses_standard_firmware_report(monkeypatch) -> None:
    monkeypatch.setattr("app.adapters.firmata.serial.Serial", FakeSerial)
    monkeypatch.setattr("app.adapters.firmata.time.sleep", lambda _seconds: None)
    result = _query_firmata("COM8", timeout=0.2)
    assert result == {"ready": True, "protocol": "firmata", "version": "2.5", "firmware": "StandardFirmata"}
    assert FakeSerial.written == bytes((START_SYSEX, REPORT_FIRMWARE, END_SYSEX))
