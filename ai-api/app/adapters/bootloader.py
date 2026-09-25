from __future__ import annotations

from typing import Any

from .base import AdapterManifest


BOOTLOADER_USB_IDS = {
    ("0483", "DF11"): ("STM32 USB DFU bootloader", "STM32"),
    ("2E8A", "0003"): ("Raspberry Pi RP2 Boot", "RP2040 / RP2350"),
    ("2341", "0036"): ("Arduino bootloader", "Arduino"),
}
NAME_HINTS = ("dfu", "bootloader", "rp2 boot", "uf2")


class BootloaderAdapter:
    adapter_id = "usb_bootloader"
    name = "DFU and UF2 bootloader identity adapter"
    manifest = AdapterManifest(
        id=adapter_id,
        name=name,
        version="1.0",
        transports=("USB DFU", "UF2 mass storage", "USB bootloader"),
        families=("STM32", "RP2040", "RP2350", "SAMD", "nRF52", "Arduino"),
        inspection_modes=("passive", "destructive"),
        timeout_seconds=15,
        safety="Inventory identifies only the bootloader interface. Erase, download, upload, and reset require a separate fingerprint-bound operation plan and explicit approval.",
    )

    def supports(self, profile: dict[str, Any]) -> bool:
        identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
        name = f"{profile.get('name', '')} {profile.get('description', '')}".lower()
        return identity in BOOTLOADER_USB_IDS or any(hint in name for hint in NAME_HINTS)

    def inspect_passive(self, profile: dict[str, Any]) -> dict[str, Any]:
        identity = (str(profile.get("vid", "")).upper(), str(profile.get("pid", "")).upper())
        model, family = BOOTLOADER_USB_IDS.get(identity, (profile.get("name") or "USB bootloader interface", "Unresolved bootloader target"))
        usb_identity = f"{identity[0] or '----'}:{identity[1] or '----'}"
        return {
            "adapter": {"id": self.adapter_id, "name": self.name, "mode": "passive bootloader identity"},
            "identity": {
                "model": model,
                "family": family,
                "classification": "microcontroller_bootloader",
                "manufacturer": profile.get("manufacturer"),
                "mcu": None,
                "architecture": None,
                "runtime": "Bootloader mode",
                "confidence": 0.96 if identity in BOOTLOADER_USB_IDS else 0.7,
                "candidates": [],
                "capabilities": [{"id": "firmware_upload", "name": "Firmware upload transport", "status": "detected", "source": f"Bootloader USB identity {usb_identity}"}],
                "components": [],
                "resources": [],
            },
            "identity_layers": [
                {"id": "bootloader", "layer": "Host interface", "name": model, "status": "verified", "source": f"USB {usb_identity}"},
                {"id": "board", "layer": "Carrier board", "name": "Unresolved", "status": "unavailable", "source": "Bootloader identities commonly span multiple boards"},
            ],
            "telemetry": {"bootloader_mode": True},
            "evidence": [{"source": "USB descriptor", "claim": f"Bootloader interface {usb_identity}", "status": "verified"}],
            "tests": [{"id": "bootloader_identity", "name": "Verify bootloader identity", "risk": "passive", "available": True, "description": "Rechecks the USB bootloader identity without reading, erasing, or writing target storage."}],
            "pins": [],
            "attached_peripherals": [],
        }

    def run_test(self, profile: dict[str, Any], test_id: str) -> dict[str, Any] | None:
        if test_id != "bootloader_identity":
            return None
        return {"passed": self.supports(profile), "summary": "USB bootloader identity is present.", "evidence": {"vid": profile.get("vid"), "pid": profile.get("pid")}}
