#!/usr/bin/env python3
"""Генерирует clash-domains.txt из domains.lst.

domains.lst  — единственный источник правды, формат podkop/sing-box:
               голые домены, каждый трактуется как domain_suffix.
clash-domains.txt — тот же список для mihomo/Clash rule-provider
               (behavior: domain, format: text), где суффиксная
               семантика требует префикса '+.'.
"""
import ipaddress
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parent.parent / "domains.lst"
DST = pathlib.Path(__file__).resolve().parent.parent / "clash-domains.txt"


def is_ip_like(value: str) -> bool:
    try:
        ipaddress.ip_network(value, strict=False)
        return True
    except ValueError:
        return False


def main() -> int:
    out, seen, bad = [], set(), []
    for raw in SRC.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip().lower().rstrip(".")
        if not line:
            continue
        if line.startswith(("+.", "*.", ".")):
            bad.append(f"{raw!r}: источник должен содержать голые домены, без wildcard")
            continue
        if is_ip_like(line):
            bad.append(f"{raw!r}: IP/подсеть — им место в user_subnets подкоп, не здесь")
            continue
        if "/" in line or " " in line:
            bad.append(f"{raw!r}: не похоже на домен")
            continue
        if "." not in line:
            bad.append(f"{raw!r}: домен без точки")
            continue
        if line in seen:
            continue
        seen.add(line)
        out.append(line)

    # Записи суффиксные, поэтому более широкий домен покрывает все свои
    # поддомены. Узкая строка рядом с широкой ничего не добавляет и со
    # временем превращается в мусор, который все боятся трогать.
    covered = set(out)
    for d in out:
        parent = d
        while "." in parent:
            parent = parent.split(".", 1)[1]
            if parent in covered:
                bad.append(
                    f"{d!r}: уже покрыт записью {parent!r} — суффикс включает поддомены, "
                    f"удалите узкую строку"
                )
                break

    if bad:
        print("Ошибки в domains.lst:", file=sys.stderr)
        for b in bad:
            print("  " + b, file=sys.stderr)
        return 1

    out.sort()
    # Без комментариев и пустых строк: mihomo не документирует поддержку '#'
    # в rule-provider format: text, поэтому файл держим строго машинным.
    DST.write_text("\n".join(f"+.{d}" for d in out) + "\n", encoding="utf-8")
    print(f"{len(out)} домен(ов) -> {DST.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
