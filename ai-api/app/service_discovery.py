from __future__ import annotations

import threading
import time

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf


SERVICE_TYPES = (
    "_http._tcp.local.",
    "_https._tcp.local.",
    "_ssh._tcp.local.",
    "_rtsp._tcp.local.",
    "_mqtt._tcp.local.",
)


class _Listener(ServiceListener):
    def __init__(self, zeroconf: Zeroconf) -> None:
        self.zeroconf = zeroconf
        self.lock = threading.Lock()
        self.services: dict[tuple[str, str], dict] = {}

    def _record(self, service_type: str, name: str) -> None:
        info = self.zeroconf.get_service_info(service_type, name, timeout=750)
        if info is None:
            return
        record = {
            "name": name.removesuffix(f".{service_type}"),
            "type": service_type.removesuffix(".local."),
            "server": (info.server or "").removesuffix("."),
            "port": info.port,
            "addresses": info.parsed_addresses(),
            "property_keys": sorted(
                key.decode("utf-8", errors="replace") if isinstance(key, bytes) else str(key)
                for key in info.properties
            ),
        }
        with self.lock:
            self.services[(service_type, name)] = record

    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        self._record(service_type, name)

    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        self._record(service_type, name)

    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        with self.lock:
            self.services.pop((service_type, name), None)


def discover_services(timeout_seconds: float = 2.5) -> dict:
    timeout_seconds = min(max(timeout_seconds, 0.5), 5.0)
    zeroconf = Zeroconf()
    listener = _Listener(zeroconf)
    browsers = [ServiceBrowser(zeroconf, service_type, listener) for service_type in SERVICE_TYPES]
    try:
        time.sleep(timeout_seconds)
        with listener.lock:
            services = sorted(listener.services.values(), key=lambda item: (item["type"], item["name"]))
    finally:
        for browser in browsers:
            browser.cancel()
        zeroconf.close()
    return {
        "provider": "zeroconf",
        "duration_seconds": timeout_seconds,
        "service_types": list(SERVICE_TYPES),
        "count": len(services),
        "services": services,
    }
