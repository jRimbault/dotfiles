#!/usr/bin/env python3

"""Continuous integration script."""

import argparse
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
    pprint(vars(args))
    # 1. setup the pre requisites to communicate with the emulated device
    network_ifs = setup_network("tap", "192.168.18.1/24")
    add_test_identity(args)
    # 2. use a context manager to ensure the emulated device stays alive
    #    during the tests and killed after the tests
    with Qemu(args, "tap"):
        # 3. run the actual tests
        tests = run_tests(args, network_ifs)
    return tests.returncode


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
    return subprocess.run(cmd, stderr=subprocess.PIPE, check=False)


def start_qemu(args, devices, poweroff):
    """Starts qemu.

    Args:
        args:      this script's arguments
        devices:   base name of network devices, eg: "tap"
        poweroff:  a `multiprocessing.Lock` to signal when to shutoff qemu
    """
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
    with (
        subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=args.images,
        ) as child,
        consumer(child.stdout, args.qemu_stdout),
        consumer(child.stderr, args.qemu_stderr),
    ):
        if poweroff.acquire(True):
            child.communicate(b"poweroff\n")
            child.wait()
            poweroff.release()


@contextmanager
def consumer(reader, writer):
    """Qemu needs something to consume its outputs.

    Else it won't anwser to various inputs.
    """

    def read(stdio, out):
        with open(out, "w", encoding="utf8") as out:
            while line := stdio.readline():
                print(line.decode("utf8").strip(), file=out)

    p = Process(target=read, args=(reader, writer))
    p.start()
    try:
        yield p
    finally:
        p.terminate()
        p.join()


class Qemu:
    """Synchronising type.

    This class concerns itself only with synchronising the background
    process with the rest of the script.

    It should keep alive the emulator only as long as the context manager.
    """

    def __init__(self, args, devices):
        self.poweroff = Lock()
        self.process = Process(target=start_qemu, args=(args, devices, self.poweroff))

    def __enter__(self):
        self.poweroff.acquire()
        self.process.start()
        # let the emulator boot up completely
        print("waiting for qemu to boot up")
        time.sleep(10)

    def __exit__(self, _type, _value, _traceback):
        self.poweroff.release()
        self.process.join()


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


def setup_network(name: str, address: str) -> List[str]:
    """Creates the network interfaces which the tests will use."""
    run = subprocess.run
    interfaces = []
    for i in range(3):
        interface = f"{name}{i}"
        run(["sudo", "ip", "tuntap", "add", interface, "mode", "tap"], check=False)
        interfaces.append(interface)
    run(
        ["sudo", "ip", "addr", "add", address, "dev", interface],
        check=False,
    )
    run(["sudo", "ip", "link", "set", "dev", interface, "up"], check=False)
    return interfaces


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
    parser.add_argument(
        "--qemu-stdout",
        help="where to redirect qemu's stdout",
        type=Path,
        default=Path("qemu-stdout.txt"),
    )
    parser.add_argument(
        "--qemu-stderr",
        help="where to redirect qemu's stderr",
        type=Path,
        default=Path("qemu-stderr.txt"),
    )
    args = parser.parse_args(argv)
    args.platform_integration = args.platform_integration.absolute()
    args.images = args.images.absolute()
    args.test_script = args.test_script.absolute()
    args.tests = args.tests.absolute()
    return args


if __name__ == "__main__":
    sys.exit(main(parse_args(sys.argv[1:])))
