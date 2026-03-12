#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich==14.3.3", "httpx==0.28.1", "pydantic==2.12.5"]
# ///
"""Bootstrap a fresh Ubuntu/Debian system with required packages.

Reads .list files from the same directory as this script and installs
packages using the appropriate method for each list.
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
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
type GitHubReleaseInstaller = typing.Callable[[Config, str, str], None]

log = logging.getLogger(Path(__file__).stem)

PACKAGES_DIR = Path(__file__).resolve().parent

GITHUB_API_BASE = "https://api.github.com"
FZF_REPO = "junegunn/fzf"
NEOVIM_RELEASE_REPO = "neovim/neovim-releases"
NERD_FONTS_REPO = "ryanoasis/nerd-fonts"
OH_MY_ZSH_REPO = "ohmyzsh/ohmyzsh"
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
    refresh_independent: bool = False
    home: Path = field(default_factory=Path.home)

    @property
    def local_bin(self) -> Path:
        return self.home / ".local" / "bin"

    @property
    def cargo_bin(self) -> Path:
        return self.home / ".cargo" / "bin"

    @property
    def bun_bin(self) -> Path:
        return self.home / ".bun" / "bin"


def main(config: Config) -> int:
    config.local_bin.mkdir(parents=True, exist_ok=True)
    extend_path(config.local_bin, config.cargo_bin, config.bun_bin)

    steps: list[tuple[str, Installer]] = [
        ("apt packages", install_apt),
        ("rustup", install_rustup),
        ("cargo-binstall crates", install_cargo_binstall),
        ("GitHub releases", install_github_releases),
        ("standalone tools", install_standalone),
        ("uv tools", install_uv_tools),
        ("bun global packages", install_bun_globals),
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


def install_cargo_binstall(config: Config):
    packages = read_list("cargo-binstall.list")
    if not packages:
        return
    log.info("installing cargo-binstall + %d crates", len(packages))
    if config.dry_run:
        for p in packages:
            if config.refresh_independent:
                log.info("cargo binstall --no-confirm --force %s", p)
            else:
                log.info("cargo binstall --no-confirm %s", p)
        return
    if not has("cargo-binstall"):
        run_piped(
            [
                "curl",
                "-L",
                "--proto",
                "=https",
                "--tlsv1.2",
                "-sSf",
                "https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.sh",
            ],
            stdin_to=["bash"],
        )
    cmd = ["cargo", "binstall", "--no-confirm", *packages]
    if config.refresh_independent:
        cmd.insert(3, "--force")
    run(cmd)


def install_github_releases(config: Config):
    special_installers: dict[str, GitHubReleaseInstaller] = {
        FZF_REPO: _install_fzf_release,
        NEOVIM_RELEASE_REPO: _install_neovim_release,
        NERD_FONTS_REPO: _install_nerd_font_release,
    }
    for entry in read_list("github-releases.list"):
        repo, _, hint = entry.partition(":")
        installer = special_installers.get(repo)
        if installer is None:
            _install_github_tarball(config, repo)
            continue
        installer(config, repo, hint)


def _install_fzf_release(config: Config, _: str, __: str):
    _install_fzf(config)


def _install_neovim_release(config: Config, repo: str, _: str):
    _install_neovim(config, repo)


def _install_nerd_font_release(config: Config, _: str, hint: str):
    _install_nerd_font(config, hint or "Hack")


def install_standalone(config: Config):
    handlers: dict[str, typing.Callable[[Config], None]] = {
        "oh-my-zsh": _install_oh_my_zsh,
        "uv": _install_uv,
        "bun": _install_bun,
    }
    for tool in read_list("standalone.list"):
        handler = handlers.get(tool)
        if handler:
            handler(config)
        else:
            log.warning("unknown standalone tool: %s", tool)


def install_uv_tools(config: Config):
    tools = read_list("uv-tools.list")
    if not tools:
        return
    log.info("installing %d uv tools", len(tools))
    if config.dry_run:
        for t in tools:
            if config.refresh_independent:
                log.info("uv tool install --upgrade %s", t)
            else:
                log.info("uv tool install %s", t)
        return
    for tool in tools:
        cmd = ["uv", "tool", "install", tool]
        if config.refresh_independent:
            cmd.insert(3, "--upgrade")
        run(cmd)


def install_bun_globals(config: Config):
    packages = read_list("bun-global.list")
    if not packages:
        return
    log.info("installing %d bun global packages", len(packages))
    resolved_specs = (
        [_bun_global_spec(package) for package in packages]
        if config.refresh_independent
        else packages
    )
    if config.dry_run:
        for spec in resolved_specs:
            log.info("bun install -g %s", spec)
        return
    run(["bun", "install", "-g", *resolved_specs])


def _install_fzf(config: Config):
    log.info("installing fzf from GitHub")
    if config.dry_run:
        if config.refresh_independent:
            log.info("git clone/update fzf + install --bin")
        else:
            log.info("git clone fzf + install --bin")
        return
    fzf_dir = config.home / ".fzf"
    if config.refresh_independent:
        if not _git_clone_or_pull(f"https://github.com/{FZF_REPO}.git", fzf_dir):
            return
    else:
        if fzf_dir.exists() or has("fzf"):
            log.warning("fzf already installed")
            return
        run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                f"https://github.com/{FZF_REPO}.git",
                str(fzf_dir),
            ]
        )
    run([str(fzf_dir / "install"), "--bin"])
    link = config.local_bin / "fzf"
    if config.refresh_independent:
        _remove_path(link)
        link.symlink_to(fzf_dir / "bin" / "fzf")
    elif not link.exists():
        link.symlink_to(fzf_dir / "bin" / "fzf")


def _install_nerd_font(config: Config, font_name: str):
    log.info("installing Nerd Font: %s", font_name)
    if config.dry_run:
        log.info("download %s.tar.xz to ~/.local/share/fonts", font_name)
        return
    font_dir = config.home / ".local" / "share" / "fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    release = get_latest_release(NERD_FONTS_REPO)
    if not release:
        log.warning("could not fetch Nerd Font releases")
        return
    pattern = re.compile(rf"{re.escape(font_name)}\.tar\.(xz|gz)$")
    asset = release.find_asset(pattern)
    if not asset:
        log.warning("could not find Nerd Font release for %s", font_name)
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


def _install_neovim(config: Config, repo: str):
    log.info("installing Neovim from GitHub releases")
    asset_name = _neovim_linux_tarball_name(platform.machine())
    if not asset_name:
        log.warning(
            "unsupported architecture for Neovim release installs: %s",
            platform.machine(),
        )
        return
    if config.dry_run:
        log.info(
            "download %s to ~/.local/share/neovim and link ~/.local/bin/nvim",
            asset_name,
        )
        return
    install_dir = config.home / ".local" / "share" / "neovim"
    link = config.local_bin / "nvim"
    if not config.refresh_independent and has("nvim"):
        log.warning("nvim already installed")
        return
    release = get_latest_release(repo)
    if not release:
        log.warning("could not fetch releases for %s", repo)
        return
    asset = release.find_asset(re.compile(rf"^{re.escape(asset_name)}$"))
    if not asset:
        log.warning("could not find Neovim release asset: %s", asset_name)
        return
    with tempfile.TemporaryDirectory() as tmp:
        download_and_extract_tar_gz(asset.browser_download_url, tmp)
        extracted_dir = next(
            (path for path in Path(tmp).iterdir() if (path / "bin" / "nvim").exists()),
            None,
        )
        if not extracted_dir:
            log.warning("Neovim release archive did not contain bin/nvim")
            return
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        _remove_path(install_dir)
        shutil.copytree(extracted_dir, install_dir, symlinks=True)
    _remove_path(link)
    link.symlink_to(install_dir / "bin" / "nvim")


def _install_github_tarball(config: Config, repo: str):
    name = repo.split("/")[-1]
    log.info("installing %s from GitHub releases", name)
    if config.dry_run:
        log.info("download latest %s linux tarball to ~/.local/bin", name)
        return
    if not config.refresh_independent and has(name):
        log.warning("%s already installed", name)
        return
    raw_arch = platform.machine()
    release = get_latest_release(repo)
    if not release:
        log.warning("could not fetch releases for %s", repo)
        return
    asset = _find_linux_tarball_asset(release, raw_arch)
    if not asset:
        log.warning("could not find release asset for %s (linux-%s)", repo, raw_arch)
        return
    with tempfile.TemporaryDirectory() as tmp:
        download_and_extract_tar_gz(asset.browser_download_url, tmp)
        for candidate in Path(tmp).rglob(name):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                dest = config.local_bin / name
                shutil.copy2(candidate, dest)
                dest.chmod(0o755)
                return
        log.warning("binary %s not found in release archive", name)


def _neovim_linux_tarball_name(arch: str) -> str | None:
    match arch:
        case "x86_64":
            release_arch = "x86_64"
        case "aarch64" | "arm64":
            release_arch = "arm64"
        case _:
            return None
    return f"nvim-linux-{release_arch}.tar.gz"


def _install_oh_my_zsh(config: Config):
    log.info("installing oh-my-zsh")
    if config.dry_run:
        if config.refresh_independent:
            log.info("git clone/update oh-my-zsh")
        else:
            log.info("curl ... ohmyzsh/install.sh | sh -- --unattended")
        return
    oh_my_zsh_dir = config.home / ".oh-my-zsh"
    if oh_my_zsh_dir.exists():
        if not config.refresh_independent:
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
        stdin_to=["sh", "-s", "--", "--unattended"],
    )


def _install_uv(config: Config):
    log.info("installing uv")
    if config.dry_run:
        if config.refresh_independent:
            log.info("uv self update")
        else:
            log.info("curl -LsSf https://astral.sh/uv/install.sh | sh")
        return
    if has("uv"):
        if not config.refresh_independent:
            log.warning("uv already installed")
            return
        run(["uv", "self", "update"])
    else:
        run_piped(["curl", "-LsSf", "https://astral.sh/uv/install.sh"], stdin_to=["sh"])


def _install_bun(config: Config):
    log.info("installing bun")
    if config.dry_run:
        if config.refresh_independent:
            log.info("bun upgrade")
        else:
            log.info("curl -fsSL https://bun.sh/install | bash")
        return
    if has("bun"):
        if not config.refresh_independent:
            log.warning("bun already installed")
            return
        run(["bun", "upgrade"])
    else:
        run_piped(["curl", "-fsSL", "https://bun.sh/install"], stdin_to=["bash"])
    extend_path(config.bun_bin)
    node_link = config.bun_bin / "node"
    if not node_link.exists():
        node_link.symlink_to(config.bun_bin / "bun")


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


def _find_linux_tarball_asset(release: GitHubRelease, arch: str) -> GitHubAsset | None:
    """Find a Linux tarball asset matching the given architecture."""
    arch_variants = (
        {arch, "amd64", "x86_64"} if arch == "x86_64" else {arch, "arm64", "aarch64"}
    )
    arch_pattern = "|".join(re.escape(a) for a in arch_variants)
    pattern = re.compile(rf"[Ll]inux[_-]({arch_pattern}).*\.(tar\.gz|tgz)$")
    return release.find_asset(pattern)


def download(url: str, dest: Path):
    """Download a URL to a local file."""
    with httpx.stream("GET", url, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)


def download_and_extract_tar_gz(url: str, dest_dir: str):
    """Download and extract a .tar.gz archive to dest_dir."""
    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp:
        download(url, Path(tmp.name))
        with tarfile.open(tmp.name, mode="r:gz") as tf:
            tf.extractall(dest_dir)


def _remove_path(path: Path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


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


def _bun_global_spec(package: str) -> str:
    if package.startswith(
        (
            "http://",
            "https://",
            "git+",
            "file:",
            "link:",
            "workspace:",
            "./",
            "../",
            "/",
        )
    ):
        return package
    if ":" in package:
        return package
    separator = package.rfind("@")
    if separator > 0:
        return package
    return f"{package}@latest"


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
        action="store_true",
        help="update independently installed tools to their latest managed version",
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
        refresh_independent=ns.refresh_independent,
    )


if __name__ == "__main__":
    sys.exit(main(parse_args()))
