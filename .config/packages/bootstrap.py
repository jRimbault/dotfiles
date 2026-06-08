#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich==14.3.3", "httpx==0.28.1", "pydantic==2.12.5"]
# ///
"""Bootstrap a fresh Ubuntu/Debian system with required packages.

Most dev tools are declared in ../mise/config.toml and installed by mise. This
script handles the pieces mise cannot: apt system packages, the rustup toolchain
(with the rust-analyzer component), oh-my-zsh, and the Hack Nerd Font. apt
package lists live in .list files next to this script.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import typing
from dataclasses import dataclass, field
from pathlib import Path

import httpx  # ty: ignore[unresolved-import]
from pydantic import BaseModel  # ty: ignore[unresolved-import]
from rich.logging import RichHandler  # ty: ignore[unresolved-import]

type Installer = typing.Callable[[Config], None]

log = logging.getLogger(Path(__file__).stem)

PACKAGES_DIR = Path(__file__).resolve().parent
MISE_CONFIG = PACKAGES_DIR.parent / "mise" / "config.toml"

GITHUB_API_BASE = "https://api.github.com"
NERD_FONTS_REPO = "ryanoasis/nerd-fonts"
NERD_FONT = "Hack"
OH_MY_ZSH_REPO = "ohmyzsh/ohmyzsh"
MISE_INSTALL_URL = "https://mise.run"
APT_NO_RECOMMENDS_SUFFIX = "[no-recommends]"
NO_DESKTOP_APT_LIST = "apt-no-desktop.list"


class GitHubAsset(BaseModel):
    name: str
    browser_download_url: str


class GitHubRelease(BaseModel):
    tag_name: str
    assets: list[GitHubAsset]

    def find_asset(self, pattern: re.Pattern[str]) -> GitHubAsset | None:
        """Find the first asset whose name matches the pattern."""
        for asset in self.assets:
            if pattern.search(asset.name):
                return asset
        return None


@dataclass(frozen=True)
class AptPackage:
    name: str
    no_recommends: bool = False


@dataclass
class Config:
    no_desktop: bool = False
    dry_run: bool = False
    refresh: bool = False
    refresh_tools: list[str] = field(default_factory=list)
    home: Path = field(default_factory=Path.home)

    @property
    def local_bin(self) -> Path:
        return self.home / ".local" / "bin"

    @property
    def cargo_bin(self) -> Path:
        return self.home / ".cargo" / "bin"

    @property
    def mise_shims(self) -> Path:
        return self.home / ".local" / "share" / "mise" / "shims"


def main(config: Config) -> int:
    config.local_bin.mkdir(parents=True, exist_ok=True)
    extend_path(config.local_bin, config.cargo_bin, config.mise_shims)

    # On refresh we only update independently managed tools (mise, rustup,
    # oh-my-zsh, fonts) and skip the system package manager.
    if config.refresh:
        steps: list[tuple[str, Installer]] = [
            ("rustup", install_rustup),
            ("mise tools", install_mise),
            ("oh-my-zsh", install_oh_my_zsh),
            ("Nerd Font", install_nerd_font),
        ]
    else:
        steps = [
            ("apt packages", install_apt),
            ("rustup", install_rustup),
            ("mise tools", install_mise),
            ("oh-my-zsh", install_oh_my_zsh),
            ("Nerd Font", install_nerd_font),
        ]
    failures: list[str] = []
    for label, step in steps:
        log.info("[bold]%s[/bold]", label, extra={"markup": True})
        try:
            step(config)
        except Exception:
            log.exception("failed during: %s", label)
            failures.append(label)

    if failures:
        log.error(
            "[bold red]bootstrap failed[/bold red]: %s",
            ", ".join(failures),
            extra={"markup": True},
        )
        return 1

    log.info("[bold green]bootstrap complete[/bold green]", extra={"markup": True})
    return 0


def install_apt(config: Config):
    packages = read_apt_list("apt.list")
    if config.no_desktop:
        excluded_packages = set(read_list(NO_DESKTOP_APT_LIST))
        packages = [p for p in packages if p.name not in excluded_packages]
    if not packages:
        log.warning("no apt packages to install")
        return
    default_packages = [p.name for p in packages if not p.no_recommends]
    no_recommends_packages = [p.name for p in packages if p.no_recommends]
    if no_recommends_packages:
        log.info(
            "installing %d apt packages (%d without recommends)",
            len(packages),
            len(no_recommends_packages),
        )
    else:
        log.info("installing %d apt packages", len(packages))
    if config.dry_run:
        for package in default_packages:
            log.info("%s", package)
        for package in no_recommends_packages:
            log.info("%s %s", package, APT_NO_RECOMMENDS_SUFFIX)
        return
    run(as_root(["apt-get", "update", "-qq"]))
    if default_packages:
        run(as_root(["apt-get", "install", "-y", "-qq", *default_packages]))
    if no_recommends_packages:
        run(
            as_root(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "-qq",
                    "--no-install-recommends",
                    *no_recommends_packages,
                ]
            )
        )


def install_rustup(config: Config):
    log.info("installing rustup")
    if config.dry_run:
        log.info("curl ... https://sh.rustup.rs | sh -s -- -y")
        return
    if has("rustup"):
        log.warning("rustup already installed, updating")
        run(["rustup", "update"])
    else:
        run_piped(
            ["curl", "--proto", "=https", "--tlsv1.2", "-sSf", "https://sh.rustup.rs"],
            stdin_to=["sh", "-s", "--", "-y"],
        )
        source_cargo_env()
    for component in read_list("rustup.list"):
        log.info("adding rustup component: %s", component)
        run(["rustup", "component", "add", component])


def install_mise(config: Config):
    """Install mise if missing, then install or upgrade the tools it manages.

    mise is pointed at the dotfiles copy of the config via MISE_GLOBAL_CONFIG_FILE
    so it works whether or not the dotfiles are already checked out into $HOME.
    """
    if config.refresh:
        targets = ", ".join(config.refresh_tools) if config.refresh_tools else "all"
        log.info("upgrading mise tools (%s)", targets)
        mise_cmd = ["mise", "upgrade", *config.refresh_tools]
    else:
        log.info("installing mise tools from %s", MISE_CONFIG)
        mise_cmd = ["mise", "install"]
    if config.dry_run:
        if not has("mise"):
            log.info("curl %s | sh", MISE_INSTALL_URL)
        log.info("MISE_GLOBAL_CONFIG_FILE=%s %s", MISE_CONFIG, shlex.join(mise_cmd))
        return
    if not has("mise"):
        run_piped(["curl", MISE_INSTALL_URL], stdin_to=["sh"])
        extend_path(config.local_bin, config.mise_shims)
    env = {**os.environ, "MISE_GLOBAL_CONFIG_FILE": str(MISE_CONFIG)}
    run(mise_cmd, env=env)


def install_oh_my_zsh(config: Config):
    log.info("installing oh-my-zsh")
    if config.dry_run:
        if config.refresh:
            log.info("git clone/update oh-my-zsh")
        else:
            log.info("curl ... ohmyzsh/install.sh | sh -- --unattended")
        return
    oh_my_zsh_dir = config.home / ".oh-my-zsh"
    if oh_my_zsh_dir.exists():
        if not config.refresh:
            log.warning("oh-my-zsh already installed")
            return
        if not _git_clone_or_pull(
            f"https://github.com/{OH_MY_ZSH_REPO}.git",
            oh_my_zsh_dir,
            depth=None,
        ):
            return
        zshrc = config.home / ".zshrc"
        if not zshrc.exists():
            shutil.copy2(oh_my_zsh_dir / "templates" / "zshrc.zsh-template", zshrc)
        return
    run_piped(
        [
            "curl",
            "-fsSL",
            f"https://raw.githubusercontent.com/{OH_MY_ZSH_REPO}/master/tools/install.sh",
        ],
        stdin_to=["sh", "-s", "--", "--unattended", "--keep-zshrc"],
    )


def install_nerd_font(config: Config):
    log.info("installing Nerd Font: %s", NERD_FONT)
    if config.dry_run:
        log.info("download %s.tar.xz to ~/.local/share/fonts", NERD_FONT)
        return
    font_dir = config.home / ".local" / "share" / "fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    release = get_latest_release(NERD_FONTS_REPO)
    if not release:
        log.warning("could not fetch Nerd Font releases")
        return
    pattern = re.compile(rf"{re.escape(NERD_FONT)}\.tar\.(xz|gz)$")
    asset = release.find_asset(pattern)
    if not asset:
        log.warning("could not find Nerd Font release for %s", NERD_FONT)
        return
    log.info("downloading %s", asset.browser_download_url)
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "font.tar.xz"
        download(asset.browser_download_url, archive)
        with tarfile.open(archive) as tf:
            tf.extractall(tmp)
        for font_file in Path(tmp).glob("*.[to]tf"):
            shutil.copy2(font_file, font_dir)
    if has("fc-cache"):
        run(["fc-cache", "-f", str(font_dir)])


def read_list(name: str) -> list[str]:
    """Read a .list file, stripping comments and blank lines."""
    path = PACKAGES_DIR / name
    if not path.exists():
        log.warning("list file not found: %s", path)
        return []
    lines = path.read_text().splitlines()
    entries = []
    for line in lines:
        line = re.sub(r"#.*", "", line).strip()
        if line:
            entries.append(line)
    return entries


def read_apt_list(name: str) -> list[AptPackage]:
    return [parse_apt_package(entry) for entry in read_list(name)]


def parse_apt_package(entry: str) -> AptPackage:
    if entry.endswith(APT_NO_RECOMMENDS_SUFFIX):
        name = entry.removesuffix(APT_NO_RECOMMENDS_SUFFIX).rstrip()
        if not name:
            raise ValueError(f"invalid apt package entry: {entry!r}")
        return AptPackage(name=name, no_recommends=True)
    return AptPackage(name=entry)


def run(cmd: list[str], **kwargs: typing.Any):
    """Run a command, raising on failure."""
    log.debug("+ %s", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def run_piped(cmd: list[str], *, stdin_to: list[str]):
    """Run a 'curl ... | installer' pattern."""
    log.debug("+ %s | %s", shlex.join(cmd), shlex.join(stdin_to))
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as curl:
        subprocess.run(stdin_to, stdin=curl.stdout, check=True)


def as_root(cmd: list[str]) -> list[str]:
    """Run apt commands via sudo unless the current process is already root."""
    return cmd if os.geteuid() == 0 else ["sudo", *cmd]


def has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def extend_path(*dirs: Path):
    """Prepend directories to PATH if they exist or may soon exist."""
    current = os.environ.get("PATH", "")
    additions = [str(d) for d in dirs if str(d) not in current]
    if additions:
        os.environ["PATH"] = os.pathsep.join([*additions, current])


def source_cargo_env():
    """Add cargo bin to PATH after rustup install."""
    extend_path(Path.home() / ".cargo" / "bin")


def get_latest_release(repo: str) -> GitHubRelease | None:
    """Fetch and validate the latest release for a GitHub repo."""
    try:
        resp = httpx.get(
            f"{GITHUB_API_BASE}/repos/{repo}/releases/latest",
            headers={"Accept": "application/vnd.github+json"},
            follow_redirects=True,
        )
        resp.raise_for_status()
        return GitHubRelease.model_validate(resp.json())
    except (httpx.HTTPError, Exception) as exc:
        log.warning("GitHub API request failed for %s: %s", repo, exc)
        return None


def download(url: str, dest: Path):
    """Download a URL to a local file."""
    with httpx.stream("GET", url, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)


def _git_clone_or_pull(repo: str, dest: Path, *, depth: int | None = 1) -> bool:
    if dest.exists():
        if not (dest / ".git").exists():
            log.warning("%s exists but is not a git checkout", dest)
            return False
        run(["git", "-C", str(dest), "pull", "--ff-only"])
        return True
    cmd = ["git", "clone"]
    if depth is not None:
        cmd.extend(["--depth", str(depth)])
    cmd.extend([repo, str(dest)])
    run(cmd)
    return True


def parse_args(argv: list[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description="Bootstrap a fresh Ubuntu/Debian system with required packages.",
    )
    parser.add_argument(
        "--no-desktop",
        action="store_true",
        help="skip sway/desktop packages",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be installed without doing it",
    )
    parser.add_argument(
        "--refresh-independent",
        nargs="*",
        metavar="TOOL",
        help="update independently managed tools (mise, rustup, oh-my-zsh, "
        "fonts); optionally name specific mise tools to pass to `mise upgrade`",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    ns = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if ns.verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    return Config(
        no_desktop=ns.no_desktop,
        dry_run=ns.dry_run,
        refresh=ns.refresh_independent is not None,
        refresh_tools=ns.refresh_independent or [],
    )


if __name__ == "__main__":
    sys.exit(main(parse_args()))
