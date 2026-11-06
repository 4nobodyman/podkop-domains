#!/usr/bin/env python3
"""Build an Amnezia split-tunneling import from the Podkop source lists."""

import ipaddress
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "ip-list-amnezia.json"
BASE = "https://raw.githubusercontent.com/itdoginfo/allow-domains/main"
SOURCES = {
    "russia_inside": f"{BASE}/Russia/inside-raw.lst",
    "telegram_domains": f"{BASE}/Services/telegram.lst",
    "telegram_subnets": f"{BASE}/Subnets/IPv4/telegram.lst",
    "google_ai": f"{BASE}/Services/google_ai.lst",
}


def lines(content):
    return [line.split("#", 1)[0].strip().lower().rstrip(".")
            for line in content.splitlines()
            if line.split("#", 1)[0].strip()]


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "podkop-domains-amnezia-builder/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def valid_domain(value):
    if value.startswith(".") or "*" in value or "/" in value or " " in value:
        return False
    try:
        ascii_name = value.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    labels = ascii_name.split(".")
    return len(labels) >= 2 and all(
        1 <= len(label) <= 63 and not label.startswith("-") and not label.endswith("-")
        for label in labels
    )


def main():
    remote = {name: lines(download(url)) for name, url in SOURCES.items()}
    if any(not values for values in remote.values()):
        raise ValueError("An upstream list is empty; refusing to replace the last good file")

    local_domains = lines((ROOT / "domains.lst").read_text(encoding="utf-8"))
    local_subnets = lines((ROOT / "user_subnets.lst").read_text(encoding="utf-8"))
    if "facetime.apple.com" not in local_domains or "17.0.0.0/8" not in local_subnets:
        raise ValueError("FaceTime rules are missing from the local Podkop sources")

    raw_domains = (remote["russia_inside"] + remote["telegram_domains"]
                   + remote["google_ai"] + local_domains)
    skipped = sorted({value for value in raw_domains if not valid_domain(value)})
    if skipped != [".ua"] and skipped:
        raise ValueError(f"Unsupported domain entries: {skipped}")
    domains = sorted({value for value in raw_domains if valid_domain(value)})

    raw_subnets = remote["telegram_subnets"] + local_subnets
    subnets = sorted({ipaddress.ip_network(value, strict=True) for value in raw_subnets},
                     key=lambda net: (net.version, int(net.network_address), net.prefixlen))
    if not subnets or not domains:
        raise ValueError("Generated list is empty")
    entries = [{"hostname": str(net), "ip": ""} for net in subnets]
    entries.extend({"hostname": domain, "ip": ""} for domain in domains)
    OUTPUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.name}: {len(subnets)} CIDR ranges, {len(domains)} domains")
    if skipped:
        print(f"Skipped unsupported suffix-only entries: {', '.join(skipped)}", file=sys.stderr)


if __name__ == "__main__":
    main()
