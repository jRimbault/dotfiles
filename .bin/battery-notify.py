#!/usr/bin/env python3
# pyright: strict

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class Opt:
    notify: bool


def main(args: Opt):
    id = find_battery()
    percentage = battery_percentage(id)

    if args.notify:
        subprocess.run(
            ["notify-send", "Battery Status", f"Battery Percentage: {percentage}%"]
        )
    else:
        print(f"Battery Percentage: {percentage}%")


def find_battery():
    output = subprocess.check_output(["upower", "-e"], text=True)
    return next(line.strip() for line in output.splitlines() if "BAT" in line)


def battery_percentage(battery_id: str):
    output = subprocess.check_output(["upower", "-i", battery_id], text=True)
    result = search(r"percentage:\s+(\d+)%", output)
    return int(result.group(1))


def search(pattern: str, string: str):
    class RegexNotFoundError(Exception):
        pass

    if result := re.search(pattern, string):
        return result
    raise RegexNotFoundError(f"No match found for pattern: {pattern}")


def parse_args(argv: list[str]):
    """Parse arguments given to the script"""
    parser = argparse.ArgumentParser(description="Check battery status")
    parser.add_argument(
        "-n", "--notify", action="store_true", help="Send a desktop notification"
    )
    args = parser.parse_args(argv)
    return Opt(notify=args.notify)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    main(args)
