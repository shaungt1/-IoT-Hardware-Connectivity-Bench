from __future__ import annotations

import base64
import hashlib
import re
import threading
from dataclasses import dataclass
from typing import Any

import paramiko


SAFE_COMMANDS = {
    "identity": "hostname; uname -m; cat /proc/device-tree/model 2>/dev/null; . /etc/os-release 2>/dev/null; echo ${PRETTY_NAME:-Linux}",
    "cpu": "lscpu 2>/dev/null || cat /proc/cpuinfo 2>/dev/null",
    "memory": "cat /proc/meminfo 2>/dev/null",
    "interfaces": "ip -brief address 2>/dev/null || ifconfig 2>/dev/null",
    "usb": "lsusb 2>/dev/null || true",
    "i2c": "i2cdetect -l 2>/dev/null || true",
    "gpio": "gpioinfo 2>/dev/null || true",
    "media": "for p in /dev/video* /dev/media*; do [ -e \"$p\" ] && echo \"$p\"; done",
    "compatible": "tr '\\000' '\\n' </proc/device-tree/compatible 2>/dev/null || true",
    "pci": "lspci -nn 2>/dev/null || true",
    "jetson": "cat /etc/nv_tegra_release 2>/dev/null || true",
    "hailo": "command -v hailortcli >/dev/null 2>&1 && hailortcli fw-control identify 2>/dev/null || true",
}


@dataclass
class SshEnrollment:
    identifier: str
    host: str
    port: int
    username: str
    fingerprint: str
    password: str


class SshTargetError(ValueError):
    pass


def key_fingerprint(key: paramiko.PKey) -> str:
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


class SshTargetManager:
    """Holds explicitly approved SSH credentials in memory and exposes read-only inspection."""

    def __init__(self) -> None:
        self._targets: dict[str, SshEnrollment] = {}
        self._guard = threading.Lock()

    def probe(self, host: str, port: int = 22) -> dict[str, Any]:
        key = self._read_server_key(host, port)
        return {
            "host": host,
            "port": port,
            "algorithm": key.get_name(),
            "fingerprint": key_fingerprint(key),
            "requires_confirmation": True,
        }

    def enroll(self, host: str, port: int, username: str, password: str, expected_fingerprint: str) -> dict[str, Any]:
        key = self._read_server_key(host, port)
        actual = key_fingerprint(key)
        if not expected_fingerprint or actual != expected_fingerprint:
            raise SshTargetError(f"SSH host key mismatch; observed {actual}")
        client = self._connect(host, port, username, password, key)
        try:
            identity = self._command(client, "printf 'iot-bench-ssh-ok'")
            if identity != "iot-bench-ssh-ok":
                raise SshTargetError("SSH authentication succeeded but the target did not return the enrollment marker")
        finally:
            client.close()
        identifier = f"ssh:{host}:{port}:{username}"
        with self._guard:
            self._targets[identifier] = SshEnrollment(identifier, host, port, username, actual, password)
        return {"enrolled": True, **self._public(self._targets[identifier])}

    def remove(self, identifier: str) -> bool:
        with self._guard:
            target = self._targets.pop(identifier, None)
        return target is not None

    def inventory(self) -> list[dict[str, Any]]:
        with self._guard:
            targets = list(self._targets.values())
        return [
            {
                "id": target.identifier,
                "kind": "ssh_target",
                "device": f"{target.host}:{target.port}",
                "name": f"Linux target at {target.host}",
                "description": "Explicitly enrolled SSH target",
                "manufacturer": None,
                "serial_number": None,
                "vid": None,
                "pid": None,
                "transport": "SSH (host key pinned)",
                "classification": "linux_single_board_computer",
                "device_category": "Circuit, controller, or compute target",
                "ip_address": target.host,
                "ssh_username": target.username,
                "ssh_host_key_fingerprint": target.fingerprint,
            }
            for target in targets
        ]

    def inspect(self, identifier: str) -> dict[str, Any]:
        target = self._get(identifier)
        key = self._read_server_key(target.host, target.port)
        if key_fingerprint(key) != target.fingerprint:
            raise SshTargetError("The SSH host key changed after enrollment; access was refused")
        client = self._connect(target.host, target.port, target.username, target.password, key)
        try:
            outputs = {name: self._command(client, command) for name, command in SAFE_COMMANDS.items()}
        finally:
            client.close()
        identity_lines = [line.strip() for line in outputs["identity"].splitlines() if line.strip()]
        hostname = identity_lines[0] if identity_lines else target.host
        architecture = identity_lines[1] if len(identity_lines) > 1 else "Unknown"
        model = identity_lines[2].replace("\x00", "") if len(identity_lines) > 2 else "Linux compute target"
        runtime = identity_lines[-1] if len(identity_lines) > 3 else "Linux"
        components = self._components(outputs)
        family = self._family(model, outputs)
        capabilities = [
            {"id": "linux", "name": "Linux operating system", "status": "verified", "source": "Pinned SSH runtime inspection"},
            {"id": "ssh", "name": "SSH management", "status": "verified", "source": "Pinned SSH runtime inspection"},
        ]
        if outputs["i2c"]:
            capabilities.append({"id": "i2c", "name": "I2C controller", "status": "verified", "source": "Remote i2cdetect adapter listing"})
        if outputs["gpio"]:
            capabilities.append({"id": "gpio", "name": "GPIO controllers", "status": "verified", "source": "Remote gpioinfo listing"})
        if outputs["media"]:
            capabilities.append({"id": "camera", "name": "Media device nodes", "status": "detected", "source": "Remote /dev inventory"})
        if family["id"] == "nvidia-jetson":
            capabilities.append({"id": "nvidia-edge-ai", "name": "NVIDIA Jetson/Tegra platform", "status": "verified", "source": family["source"]})
        if outputs["hailo"] or "hailo" in outputs["pci"].lower():
            capabilities.append({"id": "hailo-accelerator", "name": "Hailo AI accelerator", "status": "verified", "source": "Remote HailoRT or PCI identity"})
        return {
            "identity": {
                "model": model,
                "family": family["name"],
                "manufacturer": family["manufacturer"],
                "classification": "linux_single_board_computer",
                "mcu": next((item["name"] for item in components if item["type"] == "processor"), "Linux SoC"),
                "architecture": architecture,
                "runtime": runtime,
                "confidence": 0.97,
                "candidates": [model],
                "capabilities": capabilities,
                "components": components,
                "resources": [],
            },
            "telemetry": {
                "ssh_authenticated": True,
                "device": hostname,
                "firmware": runtime,
                "architecture": architecture,
                "i2c_adapters": outputs["i2c"],
                "gpio_controllers": outputs["gpio"],
                "media_devices": outputs["media"],
                "device_tree_compatible": outputs["compatible"],
                "pci_devices": outputs["pci"],
                "vendor_pack": family["id"],
            },
            "services": {"ssh": True},
            "online": True,
            "adapter": {"id": "linux_ssh", "name": "Pinned SSH Linux board inspector", "safety": "read-only allowlist"},
            "evidence": [
                {"source": "Pinned SSH runtime inspection", "claim": f"Exact board runtime model {model}", "status": "verified"},
                {"source": "Pinned SSH runtime inspection", "claim": f"Architecture {architecture}", "status": "verified"},
                {"source": family["source"], "claim": f"Board family {family['name']}", "status": "verified"},
            ],
            "identity_layers": [
                {"id": "ssh", "layer": "Transport", "name": f"SSH {target.host}:{target.port}", "status": "verified", "source": "Pinned SSH host key"},
                {"id": "linux-board", "layer": "Board", "name": model, "status": "verified", "source": "Remote device-tree model"},
                {"id": "linux-family", "layer": "Vendor family", "name": family["name"], "status": "verified", "source": family["source"]},
                {"id": "linux-runtime", "layer": "Runtime", "name": runtime, "status": "verified", "source": "Remote /etc/os-release"},
            ],
        }

    def _get(self, identifier: str) -> SshEnrollment:
        with self._guard:
            target = self._targets.get(identifier)
        if target is None:
            raise SshTargetError("SSH target is not enrolled in this process")
        return target

    @staticmethod
    def _read_server_key(host: str, port: int) -> paramiko.PKey:
        transport = paramiko.Transport((host, port))
        try:
            transport.start_client(timeout=5)
            return transport.get_remote_server_key()
        except (OSError, paramiko.SSHException) as error:
            raise SshTargetError(f"Unable to read SSH host key: {error}") from error
        finally:
            transport.close()

    @staticmethod
    def _connect(host: str, port: int, username: str, password: str, key: paramiko.PKey) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.get_host_keys().add(host, key.get_name(), key)
        try:
            client.connect(
                host,
                port=port,
                username=username,
                password=password,
                timeout=5,
                banner_timeout=5,
                auth_timeout=5,
                allow_agent=False,
                look_for_keys=False,
            )
            return client
        except (OSError, paramiko.SSHException) as error:
            client.close()
            raise SshTargetError(f"SSH authentication failed: {error}") from error

    @staticmethod
    def _command(client: paramiko.SSHClient, command: str) -> str:
        _, stdout, stderr = client.exec_command(command, timeout=8)
        output = stdout.read().decode("utf-8", "replace").strip().replace("\x00", "")
        error = stderr.read().decode("utf-8", "replace").strip()
        return output or error

    @staticmethod
    def _components(outputs: dict[str, str]) -> list[dict[str, Any]]:
        cpu = re.search(r"^Model name:\s*(.+)$", outputs["cpu"], re.MULTILINE | re.IGNORECASE)
        components = [{
            "id": "cpu",
            "name": cpu.group(1).strip() if cpu else "Linux processor",
            "type": "processor",
            "status": "verified",
            "source": "Remote lscpu or /proc/cpuinfo",
        }]
        for index, line in enumerate(outputs["usb"].splitlines()):
            if line.strip():
                components.append({"id": f"usb-{index}", "name": line.strip(), "type": "usb_device", "status": "detected", "source": "Remote lsusb"})
        for index, line in enumerate(outputs.get("pci", "").splitlines()):
            if line.strip() and any(token in line.lower() for token in ("hailo", "nvidia", "vpu", "neural", "accelerator")):
                components.append({"id": f"pci-accelerator-{index}", "name": line.strip(), "type": "accelerator", "status": "verified", "source": "Remote lspci"})
        return components

    @staticmethod
    def _family(model: str, outputs: dict[str, str]) -> dict[str, str]:
        evidence = "\n".join((model, outputs.get("compatible", ""), outputs.get("jetson", ""), outputs.get("pci", ""))).lower()
        families = (
            (("nvidia jetson", "tegra"), "nvidia-jetson", "NVIDIA Jetson", "NVIDIA"),
            (("raspberry pi", "brcm,bcm"), "raspberry-pi", "Raspberry Pi", "Raspberry Pi Ltd"),
            (("lichee", "sipeed"), "sipeed-lichee", "Sipeed Lichee", "Sipeed"),
            (("orange pi", "orangepi"), "orange-pi", "Orange Pi", "Shenzhen Xunlong"),
            (("radxa", "rock 5", "rock-5"), "radxa", "Radxa", "Radxa"),
            (("beaglebone", "beagleboard"), "beagleboard", "BeagleBoard", "BeagleBoard.org"),
        )
        for tokens, identifier, name, manufacturer in families:
            if any(token in evidence for token in tokens):
                return {"id": identifier, "name": name, "manufacturer": manufacturer, "source": "Remote device-tree/vendor runtime evidence"}
        if outputs.get("hailo") or "hailo" in evidence:
            return {"id": "linux-hailo-host", "name": "Linux host with Hailo accelerator", "manufacturer": "Hailo", "source": "Remote HailoRT or PCI identity"}
        return {"id": "generic-linux-sbc", "name": model or "Linux compute target", "manufacturer": "Unknown", "source": "Remote device-tree model"}

    @staticmethod
    def _public(target: SshEnrollment) -> dict[str, Any]:
        return {
            "identifier": target.identifier,
            "host": target.host,
            "port": target.port,
            "username": target.username,
            "fingerprint": target.fingerprint,
            "credential_storage": "memory_only",
        }
