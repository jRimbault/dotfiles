#!/usr/bin/env python

import argparse
from pathlib import Path
from pprint import pprint


def main(args):
    config = parse_config()
    ACTIONS[args.action](config, args.needle)


class Config:
    def __init__(self, bindings, modes, variables):
        self.bindings = bindings
        self.modes = modes
        self.variables = variables


def parse_config():
    def interpret(action, variables):
        token = next(t.strip("'") for t in action.split(" ") if t.strip("'")[0] == "$")
        return action.replace(token, variables[token])

    config = Path.home().joinpath(".config", "sway", "config")
    variables = {}
    bindings = {}
    MODIFIER = "Super"
    modes = {}
    with open(config, encoding="utf8") as fd:
        current_mode = None
        for line in map(str.strip, fd):
            if line == "" or line.startswith("#"):
                continue
            if line.startswith("set"):
                line = line.split(" ")
                variables[line[1].strip()] = " ".join(line[2:]).strip()
                continue
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
                if line.startswith("bindsym"):
                    if " mode " in line:
                        mode = list(
                            t.strip("'")
                            for t in line.split(" ")
                            if t.strip("'")[0] == "$"
                        )
                        mode = mode[1]
                        line = line.replace("$mod", MODIFIER).strip()[8:].split(" ")
                        modes[mode]["__enter__"] = (
                            line[0],
                            interpret(" ".join(line[2:]).strip("'"), variables),
                        )
                    else:
                        line = line.replace("$mod", MODIFIER).strip()[8:].split(" ")
                        bindings[line[0]] = " ".join(line[1:])

    for key, action in bindings.items():
        try:
            bindings[key] = interpret(action, variables)
        except StopIteration:
            pass

    return Config(bindings, modes, variables)


def direct(config, needle=None):
    needle = needle if needle else ""
    bindings = config.bindings
    padding = max(map(lambda item: len(item[0]) + len(item[1]), bindings.items())) + 1
    for key, action in bindings.items():
        if needle not in action:
            continue
        p = padding - len(key)
        print(f"{key}: {action:>{p}}")


def modes(config, needle=None):
    needle = needle if needle else ""
    modes = config.modes
    padding = max(
        map(
            lambda mode: max(
                map(lambda key: len(key) + len(modes[mode][key]), modes[mode].keys())
            ),
            modes.keys(),
        )
    )
    for mode in modes.keys():
        title = modes[mode]["__enter__"][1]
        if needle not in title.replace("]", ""):
            continue
        print(title)
        enter = modes[mode]["__enter__"][0]
        print(f"  {enter}")
        for key, action in modes[mode].items():
            if key == "__enter__":
                continue
            p = padding - len(key)
            print(f"    {key}: {action:>{p}}")


ACTIONS = {
    direct.__name__: direct,
    modes.__name__: modes,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", nargs="?", choices=list(ACTIONS.keys()), default=direct.__name__
    )
    parser.add_argument("needle", nargs="?")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
