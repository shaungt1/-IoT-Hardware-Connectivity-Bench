from __future__ import annotations

import ipaddress
import platform
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable

import psutil


SERVICE_PORTS = {
    22: ("SSH", None),
    80: ("HTTP", "http"),
    443: ("HTTPS", "https"),
    1883: ("MQTT", None),
    3000: ("Web application", "http"),
    5000: ("Web application", "http"),
    8000: ("Web application", "http"),
    8080: ("Web application", "http"),
    8888: ("Web application", "http"),
    18800: ("PicoClaw", "http"),
}


@dataclass(frozen=True)
class LocalNetwork:
    interface: str
    address: str
    network: ipaddress.IPv4Network


def local_private_networks() -> list[LocalNetwork]:
    discovered: dict[str, LocalNetwork] = {}
    for interface, addresses in psutil.net_if_addrs().items():
        for address in addresses:
            if address.family != socket.AF_INET or not address.netmask:
                continue
            try:
                ip = ipaddress.ip_address(address.address)
                network = ipaddress.ip_network(f"{address.address}/{address.netmask}", strict=False)
            except ValueError:
                continue
            if not ip.is_private or ip.is_loopback or ip.is_link_local:
                continue
            # Deep discovery is intentionally capped to the local /24 containing the host.
            bounded = ipaddress.ip_network(f"{address.address}/24", strict=False)
            discovered[str(bounded)] = LocalNetwork(interface, address.address, bounded)
    return list(discovered.values())


def _neighbor_cache() -> dict[str, str | None]:
    command = ["arp", "-a"] if platform.system() == "Windows" else ["ip", "neigh", "show"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    neighbors: dict[str, str | None] = {}
    for line in result.stdout.splitlines():
        ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", line)
        if not ip_match:
            continue
        value = ip_match.group(0)
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            continue
        if not ip.is_private or ip.is_loopback:
            continue
        mac_match = re.search(r"\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b", line, re.IGNORECASE)
        neighbors[value] = mac_match.group(0).replace("-", ":").upper() if mac_match else None
    return neighbors


def _probe(host: str, ports: Iterable[int], timeout: float) -> dict:
    services = []
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                name, scheme = SERVICE_PORTS[port]
                services.append(
                    {
                        "name": name,
                        "port": port,
                        "protocol": "tcp",
                        "url": f"{scheme}://{host}{'' if port in (80, 443) else f':{port}'}" if scheme else None,
                        "status": "verified",
                    }
                )
        except OSError:
            continue
    return {"address": host, "services": services}


def discover_network_devices(mode: str = "standard", target: str | None = None) -> dict:
    if mode not in {"standard", "deep"}:
        raise ValueError("Discovery mode must be standard or deep")
    networks = local_private_networks()
    raw_neighbors = _neighbor_cache()
    neighbors = {
        address: mac
        for address, mac in raw_neighbors.items()
        if any(
            ipaddress.ip_address(address) in item.network
            and ipaddress.ip_address(address) not in {item.network.network_address, item.network.broadcast_address}
            for item in networks
        )
    }
    candidates = set(neighbors)
    if target:
        try:
            requested = ipaddress.ip_address(target)
        except ValueError as error:
            raise ValueError("Target must be a valid IPv4 address") from error
        if not requested.is_private or not any(requested in item.network for item in networks):
            raise ValueError("Target must be inside one of this computer's private local /24 networks")
        candidates.add(str(requested))
    if mode == "deep":
        for item in networks:
            candidates.update(str(host) for host in item.network.hosts() if str(host) != item.address)

    timeout = 0.16 if mode == "deep" else 0.3
    devices: list[dict] = []
    with ThreadPoolExecutor(max_workers=64 if mode == "deep" else 24) as executor:
        jobs = {executor.submit(_probe, host, SERVICE_PORTS, timeout): host for host in sorted(candidates)}
        for job in as_completed(jobs):
            result = job.result()
            address = result["address"]
            if result["services"] or address in neighbors:
                devices.append(
                    {
                        "address": address,
                        "mac_address": neighbors.get(address),
                        "source": "service probe + neighbor cache" if result["services"] else "neighbor cache",
                        "services": result["services"],
                    }
                )
    devices.sort(key=lambda item: tuple(int(part) for part in item["address"].split(".")))
    return {
        "mode": mode,
        "scope": [str(item.network) for item in networks],
        "count": len(devices),
        "devices": devices,
        "limits": {
            "private_subnets_only": True,
            "maximum_prefix": 24,
            "ports": list(SERVICE_PORTS),
            "writes_sent": False,
        },
    }
