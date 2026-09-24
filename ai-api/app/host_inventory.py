from __future__ import annotations

import socket

import psutil


def host_network_inventory() -> dict:
    stats = psutil.net_if_stats()
    interfaces: list[dict] = []
    for name, addresses in psutil.net_if_addrs().items():
        interface_stats = stats.get(name)
        normalized_addresses = []
        for address in addresses:
            if address.family == socket.AF_INET:
                family = "IPv4"
            elif address.family == socket.AF_INET6:
                family = "IPv6"
            elif address.family == psutil.AF_LINK:
                family = "MAC"
            else:
                continue
            normalized_addresses.append(
                {
                    "family": family,
                    "address": address.address.split("%", 1)[0],
                    "netmask": address.netmask,
                }
            )
        interfaces.append(
            {
                "name": name,
                "up": bool(interface_stats and interface_stats.isup),
                "speed_mbps": int(interface_stats.speed) if interface_stats else 0,
                "mtu": int(interface_stats.mtu) if interface_stats else 0,
                "addresses": normalized_addresses,
            }
        )
    interfaces.sort(key=lambda item: (not item["up"], item["name"].lower()))
    return {
        "hostname": socket.gethostname(),
        "provider": "psutil",
        "interfaces": interfaces,
    }
