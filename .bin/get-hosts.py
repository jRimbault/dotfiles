#!/usr/bin/env python3

import sys
from pathlib import Path


file = sys.argv[1] if len(sys.argv) > 1 else Path.home() / ".ssh/config"

with open(file, encoding="utf8") as f:
    hosts = {
        host.strip()
        for line in f
        if line.startswith("Host")
        for host in line.replace("Host", "").strip().split(" ")
        if "*" not in host
    }

hosts = sorted(hosts)
print(*hosts, sep="\n")
