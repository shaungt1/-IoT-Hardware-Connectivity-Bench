from __future__ import annotations

import unittest
from unittest.mock import patch

from iot_hardware_connectivity_bench.inventory import collect_inventory, filter_devices


class FakePort:
    device = "/dev/ttyUSB0"
    name = "ttyUSB0"
    description = "USB Serial Device"
    hwid = "USB VID:PID=2341:0043"
    vid = 0x2341
    pid = 0x0043
    serial_number = "ABC123"
    manufacturer = "Arduino"
    product = "Uno"
    interface = "USB"
    location = "1-1"


class InventoryTests(unittest.TestCase):
    @patch("iot_hardware_connectivity_bench.inventory.host_metadata", return_value={"hostname": "bench"})
    @patch("iot_hardware_connectivity_bench.inventory.list_network_interfaces", return_value=[])
    @patch("iot_hardware_connectivity_bench.inventory.list_storage_devices", return_value=[])
    @patch("iot_hardware_connectivity_bench.inventory.list_video_devices", return_value=[])
    @patch("iot_hardware_connectivity_bench.inventory.list_ports.comports", return_value=[FakePort()])
    def test_collect_inventory_includes_serial_ports(self, *_mocks):
        inventory = collect_inventory()

        self.assertEqual(inventory["device_count"], 1)
        self.assertEqual(inventory["host"]["hostname"], "bench")
        self.assertEqual(inventory["devices"][0]["identifier"], "/dev/ttyUSB0")
        self.assertEqual(inventory["devices"][0]["details"]["manufacturer"], "Arduino")

    def test_filter_devices_supports_kind_and_query(self):
        inventory = {
            "devices": [
                {"kind": "serial", "identifier": "/dev/ttyUSB0", "summary": "Arduino Uno"},
                {"kind": "camera", "identifier": "/dev/video0", "summary": "USB Camera"},
            ]
        }

        serial_only = filter_devices(inventory, kind="serial")
        query_only = filter_devices(inventory, query="camera")

        self.assertEqual(len(serial_only), 1)
        self.assertEqual(serial_only[0]["identifier"], "/dev/ttyUSB0")
        self.assertEqual(len(query_only), 1)
        self.assertEqual(query_only[0]["identifier"], "/dev/video0")


if __name__ == "__main__":
    unittest.main()

