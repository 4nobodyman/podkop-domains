#!/usr/bin/env python3
"""Build an Amnezia split-tunneling import from the Podkop source lists."""

import ipaddress
import json
import pathlib
import sys
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "ip-list-amnezia.json"
BASE = "https://raw.githubusercontent.com/itdoginfo/allow-domains/main"
SOURCES = {
    "russia_inside": f"{BASE}/Russia/inside-raw.lst",
    "telegram_domains": f"{BASE}/Services/telegram.lst",
    "telegram_subnets": f"{BASE}/Subnets/IPv4/telegram.lst",
    "google_ai": f"{BASE}/Services/google_ai.lst",
    "meta_subnets": f"{BASE}/Subnets/IPv4/meta.lst",
}
GOOGLE_RANGES = "https://www.gstatic.com/ipranges/goog.json"
GOOGLE_CLOUD_RANGES = "https://www.gstatic.com/ipranges/cloud.json"
# Anthropic's published IPv4 range restored Claude on the user's iPhone.
ANTHROPIC_SUBNET = "160.79.104.0/23"


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


def resolve_ipv4(domain):
    result = set()
    for name in (domain, f"www.{domain}"):
        try:
            url = "https://dns.google/resolve?" + urllib.parse.urlencode({"name": name, "type": "A"})
            request = urllib.request.Request(url, headers={"User-Agent": "podkop-domains-amnezia-builder/1.0"})
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.load(response)
        except (OSError, ValueError):
            continue
        if data.get("Status") != 0:
            continue
        for answer in data.get("Answer", []):
            if answer.get("type") == 1:
                try:
                    ip = ipaddress.IPv4Address(answer["data"])
                except (ValueError, KeyError):
                    continue
                if ip.is_global:
                    result.add(str(ip))
    return sorted(result, key=lambda ip: int(ipaddress.IPv4Address(ip)))


def previous_ips():
    if not OUTPUT.exists():
        return {}
    try:
        entries = json.loads(OUTPUT.read_text(encoding="utf-8"))
        return {entry["hostname"]: [ip for ip in entry.get("ips", [])
                                     if isinstance(ip, str) and is_public_ipv4(ip)]
                for entry in entries if isinstance(entry, dict) and isinstance(entry.get("ips"), list)}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def is_public_ipv4(value):
    try:
        return ipaddress.IPv4Address(value).is_global
    except ValueError:
        return False


def merged_intervals(networks):
    intervals = []
    for network in sorted(networks, key=lambda net: int(net.network_address)):
        start, end = int(network.network_address), int(network.broadcast_address)
        if intervals and start <= intervals[-1][1] + 1:
            intervals[-1] = (intervals[-1][0], max(intervals[-1][1], end))
        else:
            intervals.append((start, end))
    return intervals


def google_service_subnets():
    # Google documents this subtraction for its default service IP ranges.
    def ipv4_prefixes(url):
        payload = json.loads(download(url))
        prefixes = payload.get("prefixes")
        if not isinstance(prefixes, list) or not prefixes:
            raise ValueError(f"Missing IP prefixes in {url}")
        return [ipaddress.IPv4Network(item["ipv4Prefix"])
                for item in prefixes if "ipv4Prefix" in item]

    google = merged_intervals(ipv4_prefixes(GOOGLE_RANGES))
    cloud = merged_intervals(ipv4_prefixes(GOOGLE_CLOUD_RANGES))
    remaining = []
    for start, end in google:
        pieces = [(start, end)]
        for cloud_start, cloud_end in cloud:
            if cloud_start > end:
                break
            if cloud_end < start:
                continue
            next_pieces = []
            for piece_start, piece_end in pieces:
                if cloud_end < piece_start or cloud_start > piece_end:
                    next_pieces.append((piece_start, piece_end))
                    continue
                if piece_start < cloud_start:
                    next_pieces.append((piece_start, cloud_start - 1))
                if cloud_end < piece_end:
                    next_pieces.append((cloud_end + 1, piece_end))
            pieces = next_pieces
        remaining.extend(pieces)
    subnets = [network
               for start, end in remaining
               for network in ipaddress.summarize_address_range(
                   ipaddress.IPv4Address(start), ipaddress.IPv4Address(end))]
    if not subnets:
        raise ValueError("No Google service IP ranges after subtracting Google Cloud")
    return subnets


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

    raw_subnets = (remote["telegram_subnets"] + remote["meta_subnets"]
                   + local_subnets + [ANTHROPIC_SUBNET])
    subnets = sorted(({ipaddress.ip_network(value, strict=True) for value in raw_subnets}
                      | set(google_service_subnets())),
                     key=lambda net: (net.version, int(net.network_address), net.prefixlen))
    if not subnets or not domains:
        raise ValueError("Generated list is empty")
    # iOS 5.0.0.5 strips CIDR masks from hostname on import. A unique placeholder
    # keeps the subnet in ip/ips, which the client passes to the tunnel unchanged.
    entries = []
    for net in subnets:
        cidr = str(net)
        placeholder = "cidr-" + cidr.replace(".", "-").replace(":", "-").replace("/", "-d") + ".invalid"
        entries.append({"hostname": placeholder, "ips": [cidr], "ip": cidr})

    old_ips = previous_ips()
    with ThreadPoolExecutor(max_workers=16) as pool:
        resolved = dict(zip(domains, pool.map(resolve_ipv4, domains)))
    unresolved = []
    for domain in domains:
        ips = resolved[domain] or old_ips.get(domain, [])
        if not ips:
            unresolved.append(domain)
            continue
        entries.append({"hostname": domain, "ips": ips, "ip": ips[0]})
    if len(entries) - len(subnets) < len(domains) * 0.8:
        raise ValueError("Too few domains resolved; refusing to replace the last good file")
    OUTPUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.name}: {len(subnets)} CIDR ranges, {len(entries) - len(subnets)} resolved domains")
    if unresolved:
        print(f"Unresolved domains omitted ({len(unresolved)}): {', '.join(unresolved[:20])}", file=sys.stderr)
    if skipped:
        print(f"Skipped unsupported suffix-only entries: {', '.join(skipped)}", file=sys.stderr)


if __name__ == "__main__":
    main()
