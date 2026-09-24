import ipaddress

import pytest

from app import network_discovery


def test_target_must_be_on_private_local_network(monkeypatch):
    monkeypatch.setattr(
        network_discovery,
        "local_private_networks",
        lambda: [network_discovery.LocalNetwork("Ethernet", "192.168.5.192", ipaddress.ip_network("192.168.5.0/24"))],
    )
    monkeypatch.setattr(network_discovery, "_neighbor_cache", lambda: {})

    with pytest.raises(ValueError, match="inside"):
        network_discovery.discover_network_devices("standard", "192.168.6.10")


def test_standard_discovery_only_probes_neighbors_and_requested_target(monkeypatch):
    monkeypatch.setattr(
        network_discovery,
        "local_private_networks",
        lambda: [network_discovery.LocalNetwork("Ethernet", "192.168.5.192", ipaddress.ip_network("192.168.5.0/24"))],
    )
    monkeypatch.setattr(network_discovery, "_neighbor_cache", lambda: {"192.168.5.1": "AA:BB:CC:DD:EE:FF"})
    monkeypatch.setattr(
        network_discovery,
        "_probe",
        lambda host, ports, timeout: {
            "address": host,
            "services": [{"name": "HTTP", "port": 80, "protocol": "tcp", "url": f"http://{host}", "status": "verified"}],
        },
    )

    result = network_discovery.discover_network_devices("standard", "192.168.5.178")

    assert [device["address"] for device in result["devices"]] == ["192.168.5.1", "192.168.5.178"]
    assert result["limits"]["private_subnets_only"] is True
    assert result["limits"]["writes_sent"] is False
