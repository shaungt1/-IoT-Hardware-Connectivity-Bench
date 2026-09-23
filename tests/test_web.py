from __future__ import annotations

import json
import unittest

from iot_hardware_connectivity_bench.web import application


class WebApplicationTests(unittest.TestCase):
    def _call(self, path: str):
        captured: dict[str, object] = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        response = b"".join(
            application(
                {"PATH_INFO": path},
                start_response,
                inventory_provider=lambda: {
                    "device_count": 1,
                    "captured_at": "2026-01-01T00:00:00Z",
                    "host": {"hostname": "bench"},
                    "devices": [{"kind": "serial", "identifier": "/dev/ttyUSB0", "summary": "Arduino Uno"}],
                },
            )
        )
        return captured, response

    def test_inventory_api_returns_json_snapshot(self):
        captured, response = self._call("/api/inventory")
        payload = json.loads(response.decode("utf-8"))

        self.assertEqual(captured["status"], "200 OK")
        self.assertEqual(payload["device_count"], 1)
        self.assertEqual(payload["devices"][0]["identifier"], "/dev/ttyUSB0")

    def test_index_route_returns_html(self):
        captured, response = self._call("/")

        self.assertEqual(captured["status"], "200 OK")
        self.assertIn(b"IoT Hardware Connectivity Bench", response)

    def test_unknown_route_returns_not_found(self):
        captured, response = self._call("/missing")
        payload = json.loads(response.decode("utf-8"))

        self.assertEqual(captured["status"], "404 Not Found")
        self.assertEqual(payload["error"], "not_found")


if __name__ == "__main__":
    unittest.main()

