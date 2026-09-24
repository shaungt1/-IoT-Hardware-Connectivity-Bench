import hashlib

import pytest

from app.workspace import DeviceWorkspace, WorkspaceError


def test_workspace_lists_and_reads_only_allowlisted_text(tmp_path) -> None:
    firmware = tmp_path / "firmware"
    firmware.mkdir()
    (firmware / "main.cpp").write_bytes(b"void setup() {}\n")
    (firmware / "image.bin").write_bytes(b"\x00\x01")
    service = DeviceWorkspace(tmp_path)

    inventory = service.inventory()
    assert [item["path"] for item in inventory["files"]] == ["main.cpp"]
    opened = service.read_text("bench-firmware", "main.cpp")
    assert opened["content"] == "void setup() {}\n"
    assert opened["sha256"] == hashlib.sha256(b"void setup() {}\n").hexdigest()


def test_workspace_rejects_escape_and_stale_write(tmp_path) -> None:
    firmware = tmp_path / "firmware"
    firmware.mkdir()
    path = firmware / "main.py"
    path.write_bytes(b"old\n")
    service = DeviceWorkspace(tmp_path)

    with pytest.raises(WorkspaceError):
        service.read_text("bench-firmware", "../secret.txt")
    with pytest.raises(WorkspaceError, match="changed"):
        service.write_text("bench-firmware", "main.py", "new\n", "0" * 64)
