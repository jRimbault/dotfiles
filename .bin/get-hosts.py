#!/usr/bin/env python3

import argparse
from collections import defaultdict
import pprint
import sys
from pathlib import Path


def main(opts):
    with open(opts.file, encoding="utf8") as f:
        host = None
        hosts = defaultdict(dict)
        for line in f:
            line = line.strip()
            if line.startswith("Host "):
                _, host = line.split(" ", 1)
                if "*" in host:
                    host = None
                continue
            if host and not line:
                host = None
            if host:
                key, value = line.split(" ", 1)
                hosts[host][key] = value

    if opts.ip_to_find:
        for host, values in hosts.items():
            if values.get("HostName") == opts.ip_to_find:
                print(host)
                sys.exit(0)
        print(f"IP {opts.ip_to_find} not found")
        sys.exit(1)

    hosts = sorted(hosts.keys())
    print(*hosts, sep="\n")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to the SSH config file",
        default=Path.home() / ".ssh" / "config",
    )
    parser.add_argument(
        "--ip-to-find", nargs="?", help="IP address to find", default=None
    )
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
