#!/usr/bin/env python

import re
from pathlib import Path
from pprint import pprint

config = Path.home().joinpath(".config", "sway", "config")
variables = {}
MODIFIER = "Super"
with open(config, encoding="utf8") as fd:
    bindings = {}
    for line in fd:
        if line.startswith("#"):
            continue
        if " mode " in line:
            continue
        if line.startswith("set"):
            line = line.split(" ")
            variables[line[1].strip()] = line[2].strip()
            continue
        if line.startswith("bindsym"):
            line = line.replace("$mod", MODIFIER).strip()[8:].split(" ")
            bindings[line[0]] = " ".join(line[1:])

for key in bindings.keys():
    action = bindings[key]
    try:
        var = next(v for v in action.split(" ") if v[0] == "$")
        bindings[key] = action.replace(var, variables[var])
    except:
        pass

padding = max(map(lambda item: len(item[0]) + len(item[1]), bindings.items())) + 1
for key, action in bindings.items():
    pvalue = padding - len(key)
    print(f"{key}: {action:>{pvalue}}")

