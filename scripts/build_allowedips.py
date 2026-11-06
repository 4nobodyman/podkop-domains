#!/usr/bin/env python3
"""Build a paste-ready AmneziaWG AllowedIPs value from the Amnezia JSON."""

import ipaddress
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "ip-list-amnezia.json"
OUTPUT = ROOT / "allowedips-amneziawg.txt"


def main():
    entries = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        raise ValueError("Amnezia JSON is empty or invalid")
    networks = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("ips"), list):
            raise ValueError("Amnezia JSON has an invalid entry")
        for value in entry["ips"]:
            network = ipaddress.ip_network(value, strict=False)
            if network.version != 4 or not network.network_address.is_global:
                raise ValueError(f"Non-public IPv4 route: {value}")
            networks.append(network)
    if not networks:
        raise ValueError("No routes for AllowedIPs")
    routes = sorted(ipaddress.collapse_addresses(networks),
                    key=lambda net: (int(net.network_address), net.prefixlen))
    OUTPUT.write_text(", ".join(map(str, routes)) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.name}: {len(routes)} IPv4 routes")


if __name__ == "__main__":
    main()
