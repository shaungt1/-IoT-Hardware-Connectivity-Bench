from app.ssh_targets import SshTargetError, SshTargetManager, key_fingerprint


class FakeKey:
    def asbytes(self):
        return b"fixture-host-key"

    def get_name(self):
        return "ssh-ed25519"


class FakeStream:
    def __init__(self, value: str):
        self.value = value

    def read(self):
        return self.value.encode()


class FakeClient:
    def exec_command(self, command: str, timeout: int):
        return None, FakeStream("iot-bench-ssh-ok"), FakeStream("")

    def close(self):
        pass


def test_ssh_enrollment_pins_host_key_and_never_exposes_password(monkeypatch) -> None:
    manager = SshTargetManager()
    key = FakeKey()
    fingerprint = key_fingerprint(key)
    monkeypatch.setattr(manager, "_read_server_key", lambda *_: key)
    monkeypatch.setattr(manager, "_connect", lambda *_: FakeClient())

    result = manager.enroll("192.0.2.4", 22, "bench", "super-secret", fingerprint)
    inventory = manager.inventory()

    assert result["enrolled"] is True
    assert result["credential_storage"] == "memory_only"
    assert "password" not in result
    assert inventory[0]["transport"] == "SSH (host key pinned)"
    assert "super-secret" not in repr(inventory)


def test_ssh_enrollment_rejects_changed_host_key(monkeypatch) -> None:
    manager = SshTargetManager()
    key = FakeKey()
    monkeypatch.setattr(manager, "_read_server_key", lambda *_: key)

    try:
        manager.enroll("192.0.2.4", 22, "bench", "secret", "SHA256:wrong")
    except SshTargetError as error:
        assert "host key mismatch" in str(error)
    else:
        raise AssertionError("host-key mismatch was accepted")


def test_linux_component_parser_extracts_cpu_and_usb() -> None:
    components = SshTargetManager._components({
        "cpu": "Architecture: aarch64\nModel name: Cortex-A76\n",
        "usb": "Bus 001 Device 002: ID 1234:5678 Camera\n",
        "pci": "",
    })

    assert components[0]["name"] == "Cortex-A76"
    assert components[1]["type"] == "usb_device"


def test_linux_family_pack_classifies_common_edge_compute_boards() -> None:
    jetson = SshTargetManager._family("NVIDIA Jetson Orin Nano", {"compatible": "nvidia,p3767", "jetson": "R36", "pci": ""})
    raspberry = SshTargetManager._family("Raspberry Pi 5 Model B", {"compatible": "raspberrypi,5-model-b", "jetson": "", "pci": ""})
    hailo = SshTargetManager._family("Ubuntu edge host", {"compatible": "", "jetson": "", "pci": "01:00.0 Co-processor: Hailo Technologies Hailo-8" , "hailo": "Hailo-8"})
    assert jetson["id"] == "nvidia-jetson"
    assert raspberry["id"] == "raspberry-pi"
    assert hailo["id"] == "linux-hailo-host"
