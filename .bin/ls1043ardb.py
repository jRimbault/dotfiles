#!/usr/bin/env python3

"""Build ls1043ardb_robust_proxies and flash it."""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path
from pprint import pprint


PROVENCORE = os.environ.get(
    "PNC",
    os.environ.get("PROVENCORE"),
)
PLATFORM_INTEGRATION = os.environ.get(
    "PR_PLATFORM_INTEGRATION_REPOSITORY_PATH", os.environ.get("PLATFORM_INTEGRATION")
)
YOCTO = os.environ.get("YOCTO", "/home/nobackup/yocto-sdk")
NETWORK_INTERFACE = os.environ.get("NETWORK_INTERFACE")
CROSS_COMPILE = os.environ.get("CROSS_COMPILE")
CROSS_COMPILE64 = os.environ.get("CROSS_COMPILE64", CROSS_COMPILE)


def main(args):
    env = {
        key.upper(): str(value)
        for key, value in vars(args).items()
        if value is not None and not isinstance(value, bool)
    }
    pprint(env)
    os.environ.update(env)
    compile_lsb1043ardb(args)
    if args.compile_only:
        return
    now = datetime.now().strftime("%FT%Hh%Mm") + "."
    temp_dir = Path(tempfile.mkdtemp(prefix=now, suffix=".ls1043ardb"))
    untar_release(args, temp_dir)
    configure_yocto_bblayers(args, temp_dir)
    yocto_bitbake_image(args)
    flash_image(args)


def compile_lsb1043ardb(args):
    command = ["make", "-C", args.provencore, "ls1043ardb_robust_proxies_release"]
    process = subprocess.run(
        command,
        env=os.environ,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    pattern = r"Check ((/[^/ ]*)+/?.log) too"
    if match := re.search(pattern, process.stderr):
        if process.returncode != 0:
            print(process.stderr, file=sys.stderr)
            print("Compilation failed")
            print(f"Check file://{match[1]}")
            sys.exit(process.returncode)
        else:
            print("Compilation succesful")
            print(f"Check file://{match[1]}")


def yocto_bitbake_image(args):
    source = args.yocto.joinpath("build_ls1043ardb/SOURCE_THIS")
    with subprocess.Popen(
        f". {source} && bitbake fsl-image-networking", shell=True, env=os.environ
    ) as child:
        return child.wait()


def flash_image(args):
    images_dir = args.yocto.joinpath("build_ls1043ardb/tmp/deploy/images/ls1043ardb")
    bl2 = images_dir.joinpath("atf/bl2_sd.pbl")
    fip = images_dir.joinpath("atf/fip_uboot.bin")

    def ssh():
        command = (
            "ssh",
            "root@192.168.18.6",
            "dd",
            "of=/dev/mmcblk0",
            "bs=512",
            "seek=8",
        )
        with open(bl2, "rb") as fd:
            subprocess.call(command, stdin=fd)
        command = (
            "ssh",
            "root@192.168.18.6",
            "dd",
            "of=/dev/mmcblk0",
            "bs=512",
            f"seek={0x20000}",
        )
        with open(fip, "rb") as fd:
            subprocess.call(command, stdin=fd)

    def sdcard():
        command = ("sudo", "dd", f"if={bl2}", f"of={args.sdcard}", "bs=512", "seek=8")
        subprocess.call(command)
        command = (
            "sudo",
            "dd",
            f"if={fip}",
            f"of={args.sdcard}",
            "bs=512",
            f"seek={0x20000}",
        )
        subprocess.call(command)

    match args.via_ssh:
        case True:
            configure_network_interface(args)
            return ssh()
        case False:
            return sdcard()


def untar_release(args, temp_dir: Path):
    release_dir = args.provencore.expanduser().joinpath(
        "releases/ls1043ardb_robust_proxies"
    )
    tar_xz_release = next(
        a for a in release_dir.iterdir() if a.suffixes[-2:] == [".tar", ".xz"]
    )
    return subprocess.call(
        ("tar", "xf", tar_xz_release, "-C", temp_dir, "--strip-components=1")
    )


def configure_yocto_bblayers(args, temp_dir: Path):
    yocto_conf = args.yocto.joinpath("build_ls1043ardb/conf/bblayers.conf")
    with open(yocto_conf, "w", encoding="utf8") as fd:
        print(
            textwrap.dedent(
                f"""\
                # POKY_BBLAYERS_CONF_VERSION is increased each time build/conf/bblayers.conf
                # changes incompatibly
                POKY_BBLAYERS_CONF_VERSION = "2"

                BBPATH = "${{TOPDIR}}"
                BBFILES ?= ""

                BBLAYERS ?= " \\
                    {args.yocto}/sources/poky/meta \\
                    {args.yocto}/sources/poky/meta-poky \\
                    {args.yocto}/sources/poky/meta-yocto-bsp \\
                    {args.yocto}/sources/meta-openembedded/meta-oe \\
                    {args.yocto}/sources/meta-openembedded/meta-multimedia \\
                    {args.yocto}/sources/meta-openembedded/meta-python \\
                    {args.yocto}/sources/meta-openembedded/meta-networking \\
                    {args.yocto}/sources/meta-openembedded/meta-gnome \\
                    {args.yocto}/sources/meta-openembedded/meta-filesystems \\
                    {args.yocto}/sources/meta-openembedded/meta-webserver \\
                    {args.yocto}/sources/meta-openembedded/meta-perl \\
                    {args.yocto}/sources/meta-virtualization \\
                    {args.yocto}/sources/meta-cloud-services \\
                    {args.yocto}/sources/meta-security \\
                    {args.yocto}/sources/meta-freescale \\
                    {args.yocto}/sources/meta-freescale-distro \\
                    {args.yocto}/sources/meta-qoriq \\
                    {temp_dir}/meta-provenrun \\
                    "
            """
            ),
            file=fd,
        )


def configure_network_interface(args):
    if b"inet 192.168.18." not in subprocess.check_output(("ip", "addr")):
        command = (
            "sudo",
            "ip",
            "addr",
            "add",
            "192.168.18.1/24",
            "dev",
            args.network_interface,
        )
        subprocess.call(command)


def parse_args(argv):
    env = os.environ
    parser = argparse.ArgumentParser(
        description="""
            Compile and flash ls1043ardb_robust_proxies image onto SDCARD.
            SD card should be plugged in or the board should be on
            with SSHD running when running this script.

            You might be asked for your password when the script will use sudo.
        """,
        epilog="""
            All arguments can be supplied through the environment or
            via the command line.
            Supplied arguments will override any environment variable
            already set.
        """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sd_card_group = parser.add_argument_group("SD Card", "")
    sd_card_group.add_argument(
        "-s",
        "--sdcard",
        help="path to the sdcard device",
        action="store",
        type=Path,
        default=env.get("SDCARD"),
        metavar="SDCARD",
    )
    sd_card_group.add_argument(
        "-p",
        "--sdcard-partition",
        help="path to the sdcard partition",
        action="store",
        type=Path,
        default=env.get("SDCARD_PARTITION"),
        metavar="SDCARD_PARTITION",
        required=env.get("SDCARD") is not None,
    )
    ssh_group = parser.add_argument_group("SSH", "")
    ssh_group.add_argument(
        "-ssh",
        "--via-ssh",
        help="enable or disable flashing via SSH",
        action="store_true",
        default=bool(int(env.get("VIA_SSH", "0"))),
    )
    ssh_group.add_argument(
        "-if",
        "--network-interface",
        help="device name of the interface used for SSH",
        action="store",
        type=str,
        default=NETWORK_INTERFACE,
        metavar="NETWORK_INTERFACE",
        required=False,
    )
    parser.add_argument(
        "-cc",
        "--cross-compile",
        help="path to the cross compiler toolchain",
        action="store",
        type=Path,
        default=CROSS_COMPILE,
        metavar="CROSS_COMPILE",
        required=CROSS_COMPILE is None,
    )
    parser.add_argument(
        "-cc64",
        "--cross-compile64",
        help="""
            path to the cross compiler toolchain 64bits
            (same as CROSS_COMPILE by default)
        """,
        action="store",
        type=Path,
        default=CROSS_COMPILE64,
        metavar="CROSS_COMPILE64",
        required=False,
    )
    parser.add_argument(
        "-i",
        "--platform-integration",
        help="path to the platform-integration",
        action="store",
        type=Path,
        default=PLATFORM_INTEGRATION,
        metavar="PLATFORM_INTEGRATION",
        required=PLATFORM_INTEGRATION is None,
    )
    parser.add_argument(
        "-pnc",
        "--provencore",
        help="path to provencore repository",
        action="store",
        type=Path,
        default=PROVENCORE,
        metavar="PNC",
        required=PROVENCORE is None,
    )
    parser.add_argument(
        "-y",
        "--yocto",
        help="path to yocto sdk",
        type=Path,
        default=YOCTO,
        metavar="YOCTO",
        required=YOCTO is None,
    )
    parser.add_argument(
        "-C",
        "--compile-only",
        help="compile only provencore",
        action="store_true",
        default=bool(int(env.get("COMPILE_ONLY", "0"))),
    )
    args = parser.parse_args(argv)
    if args.cross_compile64 is None and args.cross_compile is not None:
        args.cross_compile64 = args.cross_compile
    if args.compile_only:
        return args
    if not args.via_ssh and not args.sdcard:
        parser.error("either supply a SD card device or use SSH")
    if (
        args.via_ssh
        and b"inet 192.168.18." not in subprocess.check_output(("ip", "addr"))
        and not args.network_interface
    ):
        parser.error(
            "you must supply a network interface to use for SSH or configure it yourself"
        )
    return args


if __name__ == "__main__":
    main(parse_args(sys.argv[1:]))
    print("READY")
