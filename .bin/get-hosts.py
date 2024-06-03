#!/usr/bin/env python3

from pathlib import Path

with open(Path.home() / ".ssh/config", encoding="utf8") as f:
    hosts = {
        host.strip()
        for line in f
        if line.startswith("Host")
        for host in line.replace("Host", "").strip().split(" ")
        if "*" not in host
    }

print(*hosts, sep="\n")
