#!/usr/bin/env python

from pathlib import Path
from pprint import pprint

config = Path.home().joinpath(".config", "sway", "config")
mod4_modifier = "Super"
with open(config, encoding="utf8") as fd:
    bindings = {}
    for line in fd:
        if line.startswith("set $mod"):
            modifier = line.split(" ")[-1].strip()
            continue
        if line.startswith("#"):
            continue
        if " mode " in line:
            continue
        if line.startswith("bindsym"):
            line = line.replace("$mod", mod4_modifier).strip()[8:].split(" ")
            bindings[line[0]] = " ".join(line[1:])

pprint(bindings, sort_dicts=False)
