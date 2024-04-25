#!/usr/bin/env python3

"""Continuous integration script."""

import argparse
import queue
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from multiprocessing import Process, Lock
from pathlib import Path
from pprint import pprint
from typing import List


def main(args):
    # subprocess.run = lambda *a, **k: 0
    pprint(vars(args))
    network_ifs = list(setup_network("tap", "192.168.18.1/24"))
    add_test_identity(args)
    with start_qemu(args, "tap"):
        run_tests(args, network_ifs)
    print("end of tests, `qemu-system-aarch64` should be down")


def run_tests(args, network_ifs: List[str]):
    """Execute the pytest test suite."""
    if0, if1, if2 = network_ifs
    cmd = [
        args.test_script,
        "-c",
        if0,
        "-s",
        if1,
        "-L",
        if2,
        "-p",
        args.test_script.parent.joinpath("test-cases", "pnr.css"),
        "--",
        "-x",
        "-m",
        "not fast_link",
        args.tests,
    ]
    return subprocess.run(cmd, check=False)


@contextmanager
def start_qemu(args, devices: str):
    """Starts qemu in another process in the background."""

    def background_start():
        # send "poweroff" to stdin when we get the signal
        # from the tests they finished running
        cmd = [
            args.platform_integration.joinpath(
                "buildroot_external",
                "board",
                "qemu",
                "aarch64-virt",
                "scripts",
                "run_simu.sh",
            ),
            "-gicv3",
            "-netdev",
            devices,
            "-dtb",
            "pnc_virt.dtb",
            "-smp",
            "1",
        ]
        pipe = subprocess.PIPE
        with subprocess.Popen(
            cmd,
            stdin=pipe,
            stderr=pipe,
            stdout=pipe,
            cwd=args.images,
        ) as child:
            reader = Process(target=read_child, args=(child,))
            reader.start()
            if qemu.poweroff.acquire(True):
                reader.terminate()
                child.communicate(b"poweroff\n")
                time.sleep(3)
                child.wait()
                reader.join()
                qemu.poweroff.release()

    def read_child(child):
        """Qemu needs something to consume its outputs.

        Else it won't anwser to various inputs.
        """
        child.stdout.read()
        child.stderr.read()

    class Qemu:
        def __init__(self):
            self.poweroff = Lock()
            self.process = Process(target=background_start)

        def start(self):
            self.poweroff.acquire()
            self.process.start()
            # let the emulator boot up completely
            print("waiting for qemu to boot up")
            time.sleep(10)

        def end(self):
            print("sending poweroff signal, releasing lock...")
            self.poweroff.release()
            self.process.join()

    qemu = Qemu()
    qemu.start()
    try:
        yield None
    finally:
        qemu.end()


def add_test_identity(args):
    """We need to ensure we have the right to login via SSH into the SUT."""
    key = args.platform_integration.joinpath(
        "buildroot_external",
        "board",
        "qemu",
        "aarch64-virt",
        "extra",
        "test-keys",
        "id_ecdsa_test",
    )
    os.chmod(key, 0o600)
    subprocess.run(
        [
            "ssh-add",
            key,
        ],
        check=True,
    )


def setup_network(name: str, address: str):
    """Creates the network interfaces which the tests will use."""
    run = subprocess.run
    for i in range(3):
        interface = f"{name}{i}"
        run(["sudo", "ip", "tuntap", "add", interface, "mode", "tap"], check=False)
        yield interface
    run(
        ["sudo", "ip", "addr", "add", address, "dev", interface],
        check=False,
    )
    run(["sudo", "ip", "link", "set", "dev", interface, "up"], check=False)


def parse_args(argv):
    """Defines this program's options."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    pr_metavar = "PR_PLATFORM_INTEGRATION_REPOSITORY_PATH"
    pr = os.environ.get(pr_metavar)
    parser.add_argument(
        "--platform-integration",
        metavar=pr_metavar,
        help="path to the platform-integration directory",
        type=Path,
        required=pr is None,
        default=pr,
    )
    parser.add_argument(
        "images", help="directory where the buildroot image is", type=Path
    )
    parser.add_argument("test_script", help="path to the test script", type=Path)
    parser.add_argument("tests", help="path to the tests directory", type=Path)
    args = parser.parse_args(argv)
    args.platform_integration = args.platform_integration.absolute()
    args.images = args.images.absolute()
    args.test_script = args.test_script.absolute()
    args.tests = args.tests.absolute()
    return args


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
