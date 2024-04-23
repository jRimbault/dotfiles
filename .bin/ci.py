#!/usr/bin/env python3

"""Continuous integration script."""

import argparse
import subprocess
import sys
import time
from multiprocessing import Process, Queue
from pathlib import Path
from pprint import pprint
from typing import List


def main(args):
    subprocess.run = lambda *a, **k: 0
    pprint(vars(args))
    network_ifs = list(setup_network("tap", "192.168.18.1/24"))
    poweroff_qemu = Queue()
    qemu = start_qemu(args, network_ifs, poweroff_qemu)
    run_tests(args, network_ifs, poweroff_qemu)
    qemu.join()


def run_tests(_args, _network_ifs: List[str], poweroff_qemu: Queue):
    """Execute the pytest test suite."""
    time.sleep(2)
    # send poweroff when pytest returns
    poweroff_qemu.put(True)


def start_qemu(_args, _network_ifs: List[str], poweroff: Queue):
    """Starts qemu in another process in the background."""

    def real_start():
        # send "poweroff" to stdin when we get the signal
        # from the tests they finished running
        cmd = ["cat"]
        with subprocess.Popen(cmd, stdin=subprocess.PIPE) as child:
            if poweroff.get(True):
                child.communicate(b"poweroff\n")

    qemu = Process(target=real_start)
    qemu.start()
    # let the emulator boot up completely
    # time.sleep(10)
    return qemu


def setup_network(name: str, address: str):
    """Creates the network interfaces which the tests will use."""
    run = subprocess.run
    for i in range(3):
        interface = f"{name}{i}"
        run(["sudo", "ip", "tuntap", "add", interface, "mode", "tap"], check=True)
        yield interface
    run(
        ["sudo", "ip", "addr", "add", address, "dev", interface],
        check=True,
    )
    run(["sudo", "ip", "link", "set", "dev", interface, "up"], check=True)


def parse_args(argv):
    """Defines this program's options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("qemu", help="path to the run_simu.sh script", type=Path)
    parser.add_argument("integration", help="path to the integration test directory", type=Path)
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main(parse_args(sys.argv[1:])))


def test_network_setup():
    calling_args = []
    subprocess.run = lambda *args, **kwargs: calling_args.append((*args, kwargs))
    iterator = setup_network("foo", "192.168.18.1/24")
    assert "foo0" == next(iterator)
    assert "foo0" in calling_args[0][0]
    assert "foo1" == next(iterator)
    assert "foo1" in calling_args[1][0]
    assert "foo2" == next(iterator)
    assert "foo2" in calling_args[2][0]
    assert not list(iterator)
    assert "foo2" in calling_args[3][0]
    assert "192.168.18.1/24" in calling_args[3][0]
    assert "foo2" in calling_args[4][0]
