from app.host_wifi import parse_netsh_networks


def test_parse_netsh_networks_tracks_band_and_strongest_bssid() -> None:
    output = """
SSID 1 : Test Network
    Authentication         : WPA2-Personal
    BSSID 1                : aa:bb:cc:dd:ee:ff
         Signal            : 42%
         Channel           : 11
    BSSID 2                : aa:bb:cc:dd:ee:00
         Signal            : 75%
         Channel           : 11
SSID 2 : Studio 5G
    Authentication         : WPA3-Personal
    BSSID 1                : 11:22:33:44:55:66
         Signal            : 61%
         Channel           : 149
"""

    networks = parse_netsh_networks(output)

    assert networks[0]["ssid"] == "Test Network"
    assert networks[0]["signal_percent"] == 75
    assert networks[0]["band"] == "2.4 GHz"
    assert networks[1]["band"] == "5 GHz"
