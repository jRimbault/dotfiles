#!/usr/bin/env python

from pathlib import Path
from pprint import pprint


def interpret(action):
    token = next(t.strip("'") for t in action.split(" ") if t.strip("'")[0] == "$")
    return action.replace(token, variables[token])


config = Path.home().joinpath(".config", "sway", "config")
variables = {}
bindings = {}
MODIFIER = "Super"
with open(config, encoding="utf8") as fd:
    for line in fd:
        if line.startswith("#"):
            continue
        if " mode " in line:
            continue
        if line.startswith("set"):
            line = line.split(" ")
            variables[line[1].strip()] = " ".join(line[2:]).strip()
            continue
        if line.startswith("bindsym"):
            line = line.replace("$mod", MODIFIER).strip()[8:].split(" ")
            bindings[line[0]] = " ".join(line[1:])


for key, action in bindings.items():
    try:
        bindings[key] = interpret(action)
    except StopIteration:
        pass

padding = max(map(lambda item: len(item[0]) + len(item[1]), bindings.items())) + 1
for key, action in bindings.items():
    pvalue = padding - len(key)
    print(f"{key}: {action:>{pvalue}}")


def display_modes(modes):
    for mode in modes.keys():
        print(modes[mode]["__enter__"][1])
        enter = modes[mode]["__enter__"][0]
        print(f"  {enter}")
        for key, action in modes[mode].items():
            if key == "__enter__":
                continue
            p = pvalue - len(key)
            print(f"    {key}: {action:>{p}}")


modes = {}
with open(config, encoding="utf8") as fd:
    current_mode = None
    for line in fd:
        line = line.strip()
        if line.startswith("mode"):
            mode = next(
                t.strip("'") for t in line.split(" ") if t.strip("'")[0] == "$"
            )
            current_mode = mode
            modes[mode] = {}
        if current_mode is not None:
            if line.startswith("bindsym"):
                line = line.replace("$mod", MODIFIER).strip()[8:].split(" ")
                modes[current_mode][line[0]] = " ".join(line[1:])
            elif line.startswith("}"):
                current_mode = None
        else:
            if line.startswith("bindsym") and " mode " in line:
                mode = list(
                    t.strip("'") for t in line.split(" ") if t.strip("'")[0] == "$"
                )
                mode = mode[1]
                line = line.replace("$mod", MODIFIER).strip()[8:].split(" ")
                modes[mode]["__enter__"] = (
                    line[0],
                    interpret(" ".join(line[2:]).strip("'")),
                )

display_modes(modes)
