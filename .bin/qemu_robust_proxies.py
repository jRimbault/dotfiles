#!/usr/bin/env python3

"""Script to run all of the instructions in the qemu integration guide."""

import argparse
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from urllib.request import urlretrieve
from datetime import datetime
from pathlib import Path
from pprint import pprint


def main(args):
    pprint(vars(args))
    provencore_delivery = args.dest.joinpath("integration", "buildroot_external")
    untar_delivery(args)
    os.environ.update({"PATH_TO_PNC_DELIVERY": str(provencore_delivery)})
    buildroot = getting_buildroot(args)
    building_buildroot(args, buildroot, provencore_delivery)
    setup_network_devices(args)
    if args.compile_qemu:
        compile_qemu_7(args, provencore_delivery)
    run_qemu(args, provencore_delivery)


def untar_delivery(args):
    subprocess.run(
        (
            "tar",
            "xf",
            args.delivery.expanduser(),
            "-C",
            args.dest,
            "--strip-components=1",
        ),
        check=True,
    )
    print("untarred delivery")


def getting_buildroot(args):
    path = args.dest.joinpath("buildroot-2022.02.tar.gz")
    print("downloading buildroot...")
    urlretrieve(
        "https://buildroot.org/downloads/buildroot-2022.02.tar.gz",
        path,
    )
    subprocess.run(("tar", "xf", path), check=True, cwd=args.dest)
    print("downloaded buildroot")
    return args.dest.joinpath("buildroot-2022.02")


def building_buildroot(args, buildroot, provencore_delivery):
    subprocess.run(
        (
            "make",
            "-C",
            buildroot,
            f"BR2_EXTERNAL={provencore_delivery}",
            f"O={args.working_dir}",
            "list-defconfigs",
        ),
        check=True,
        env=os.environ,
    )
    subprocess.run(
        (
            "make",
            "-C",
            buildroot,
            f"BR2_EXTERNAL={provencore_delivery}",
            f"O={args.working_dir}",
            "pnc_qemu_virt_robust_proxies_defconfig",
        ),
        check=True,
        env=os.environ,
    )
    working_dir_config = args.working_dir.joinpath(".config")
    with open(working_dir_config, "a", encoding="utf8") as fd:
        print(f'BR2_PACKAGE_PROVENCORE_CONFIG_EXTERNAL_PATH="{args.dest}"', file=fd)
    print("built buildroot config")
    subprocess.run(
        (
            "make",
            "-C",
            buildroot,
            f"BR2_EXTERNAL={provencore_delivery}",
            f"O={args.working_dir}",
        ),
        check=True,
        env=os.environ,
    )


def setup_network_devices(args):
    for i in range(3):
        subprocess.run(
            ("sudo", "ip", "tuntap", "add", f"tap{i}", "mode", "tap"), check=False
        )
    subprocess.run(
        ("sudo", "ip", "addr", "add", "192.168.18.1/24", "dev", "tap2"), check=False
    )
    subprocess.run(("sudo", "ip", "link", "set", "dev", "tap2", "up"), check=False)


def run_qemu(args, provencore_delivery):
    print(
        textwrap.dedent(
            f"""
        Run the following commands to start the emulated machine:

            # run_simu.sh depends on specific files being in the CWD
            cd {args.working_dir}/images
            {provencore_delivery}/board/qemu/aarch64-virt/scripts/run_simu.sh -gicv3 -netdev tap -dtb pnc_virt.dtb -smp 1

        Quit qemu by entering the following key sequence:

            C-a c q RET
    """
        )
    )
    if args.start_vm:
        print("\nstarting vm in 10 seconds")
        time.sleep(10)
        subprocess.run(
            (
                f"{provencore_delivery}/board/qemu/aarch64-virt/scripts/run_simu.sh",
                "-gicv3",
                "-netdev",
                "tap",
                "-dtb",
                "pnc_virt.dtb",
                "-smp 1",
            ),
            cwd=args.working_dir.joinpath("images"),
            check=True,
        )


def compile_qemu_7(args, provencore_delivery):
    version = "qemu-7.2.5"
    urlretrieve(
        f"https://download.qemu.org/{version}.tar.bz2", f"/tmp/{version}.tar.bz2"
    )
    subprocess.run(("tar", "xf", f"/tmp/{version}.tar.bz2"), cwd="/tmp", check=True)
    subprocess.run(
        (
            "patch",
            "-p1",
            "-i",
            provencore_delivery.joinpath(
                "board",
                "qemu",
                "aarch64-virt",
                "patches",
                "qemu",
                "0001-Increase-size-of-secure-memory-of-virt-platform.patch",
            ),
        ),
        check=True,
        cwd=f"/tmp/{version}",
    )
    os.mkdir(f"/tmp/{version}/build")
    subprocess.run(
        ("../configure", f"--prefix={os.environ['HOME']}/.local"),
        cwd=f"/tmp/{version}/build",
        check=True,
    )
    subprocess.run(("make", "-j"), cwd=f"/tmp/{version}/build", check=True)
    subprocess.run(("make", "install"), cwd=f"/tmp/{version}/build", check=True)
    if b"version 7.2.5" not in subprocess.check_output(
        ("qemu-system-aarch64", "--version")
    ):
        raise Exception("wrong `qemu-system-aarch64` version in $PATH")


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "delivery",
        help="""Path to the robust_proxies deliveries archive.""",
        type=Path,
    )
    parser.add_argument(
        "-d",
        "--dest",
        help="""
            Where to put the archive's contents.
            Defaults to a temporary directory.
        """,
        required=False,
        type=Path,
    )
    parser.add_argument(
        "-w",
        "--working-dir",
        help="""
            Where to put the build's artefacts.
            Defaults to a temporary directory.
        """,
        required=False,
        type=Path,
    )
    parser.add_argument("--compile-qemu", action="store_true", help="compile QEMU 7")
    parser.add_argument(
        "--start-vm",
        action="store_true",
        help="start VM immediately after build",
    )
    args = parser.parse_args(argv)
    if args.dest is None:
        now = datetime.now().strftime("%F")
        dest_dir = tempfile.mkdtemp(prefix=f"{now}.ls1043ardb-qemu.")
        args.dest = Path(dest_dir)
    if args.working_dir is None:
        work_dir = args.dest.parent.joinpath(f"{args.dest.name}.working-dir")
        args.working_dir = Path(work_dir)
    return args


if __name__ == "__main__":
    main(parse_args(sys.argv[1:]))
