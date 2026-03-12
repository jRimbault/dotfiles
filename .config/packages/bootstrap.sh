#!/usr/bin/env bash
#/ Usage: bootstrap.sh [OPTIONS]
#/
#/ Bootstrap a fresh Ubuntu/Debian system with required packages.
#/
#/ Options:
#/   --no-desktop    Skip sway/desktop packages
#/   --dry-run       Print what would be installed without doing it
#/   --help          Show this help message
#/
#/ Package lists are read from .list files alongside this script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() { grep "^#/" "$0" | cut -c4-; }

log()  { printf '\033[1;34m>>>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarn:\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# Parse a .list file: strip comments and blank lines
read_list() {
    sed 's/#.*//; /^[[:space:]]*$/d' "$1"
}

# -- Installers ---------------------------------------------------------

install_apt() {
    local packages=()
    while IFS= read -r pkg; do
        packages+=("$pkg")
    done < <(read_list "$SCRIPT_DIR/apt.list")

    if [[ "${NO_DESKTOP:-0}" == 1 ]]; then
        local desktop_packages
        # Sway desktop section
        desktop_packages=(
            sway swayidle swaylock swaybg i3status wofi
            mako-notifier grimshot brightnessctl poweralertd
            wl-clipboard
        )
        local filtered=()
        for pkg in "${packages[@]}"; do
            local skip=0
            for dpkg in "${desktop_packages[@]}"; do
                if [[ "$pkg" == "$dpkg" ]]; then skip=1; break; fi
            done
            [[ "$skip" == 0 ]] && filtered+=("$pkg")
        done
        packages=("${filtered[@]}")
    fi

    if [[ ${#packages[@]} -eq 0 ]]; then
        warn "no apt packages to install"
        return
    fi
    log "installing ${#packages[@]} apt packages"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        printf '  %s\n' "${packages[@]}"
        return
    fi
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${packages[@]}"
}

install_rustup() {
    log "installing rustup"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        echo "  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
        return
    fi
    if command -v rustup >/dev/null 2>&1; then
        warn "rustup already installed, updating"
        rustup update
    else
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        # shellcheck source=/dev/null
        source "$HOME/.cargo/env"
    fi

    # Add rustup components
    local components=()
    while IFS= read -r component; do
        components+=("$component")
    done < <(read_list "$SCRIPT_DIR/rustup.list")
    for component in "${components[@]}"; do
        log "adding rustup component: $component"
        rustup component add "$component"
    done
}

install_cargo_binstall() {
    log "installing cargo-binstall"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        echo "  curl -L --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.sh | bash"
        read_list "$SCRIPT_DIR/cargo-binstall.list" | sed 's/^/  /'
        return
    fi
    if ! command -v cargo-binstall >/dev/null 2>&1; then
        curl -L --proto '=https' --tlsv1.2 -sSf \
            https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.sh | bash
    fi

    local packages=()
    while IFS= read -r pkg; do
        packages+=("$pkg")
    done < <(read_list "$SCRIPT_DIR/cargo-binstall.list")
    log "installing ${#packages[@]} crates via cargo-binstall"
    cargo binstall --no-confirm "${packages[@]}"
}

install_github_releases() {
    while IFS= read -r entry; do
        local repo="${entry%%:*}"
        local asset_hint="${entry#*:}"
        # If no colon was present, asset_hint == entry == repo
        [[ "$asset_hint" == "$entry" ]] && asset_hint=""
        case "$repo" in
            junegunn/fzf)              install_fzf ;;
            ryanoasis/nerd-fonts)      install_nerd_font "$asset_hint" ;;
            firecow/gitlab-ci-local)   install_github_tarball "$repo" ;;
            jesseduffield/lazygit)     install_github_tarball "$repo" ;;
            *)                         warn "unknown github-releases entry: $entry" ;;
        esac
    done < <(read_list "$SCRIPT_DIR/github-releases.list")
}

install_fzf() {
    log "installing fzf from GitHub"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        echo "  git clone https://github.com/junegunn/fzf.git ~/.fzf && ~/.fzf/install"
        return
    fi
    if command -v fzf >/dev/null 2>&1; then
        warn "fzf already installed"
        return
    fi
    git clone --depth 1 https://github.com/junegunn/fzf.git "$HOME/.fzf"
    "$HOME/.fzf/install" --bin
    ln -sf "$HOME/.fzf/bin/fzf" "$HOME/.local/bin/fzf"
}

install_nerd_font() {
    local font_name="${1:-Hack}"
    log "installing Nerd Font: $font_name"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        echo "  download $font_name.tar.xz from GitHub to ~/.local/share/fonts"
        return
    fi
    local font_dir="$HOME/.local/share/fonts"
    mkdir -p "$font_dir"
    local url
    url="$(curl -s "https://api.github.com/repos/ryanoasis/nerd-fonts/releases/latest" \
        | jq -r --arg name "$font_name" '.assets[] | select(.name | test($name + "\\.tar\\.(xz|gz)$")) | .browser_download_url' \
        | head -1)"
    if [[ -z "$url" ]]; then
        warn "could not find Nerd Font release asset for $font_name"
        return
    fi
    log "downloading $url"
    local tmp
    tmp="$(mktemp -d)"
    curl -fsSL -o "$tmp/font.tar.xz" "$url"
    tar -xf "$tmp/font.tar.xz" -C "$tmp"
    find "$tmp" -name '*.ttf' -o -name '*.otf' | xargs -I{} cp {} "$font_dir/"
    rm -rf "$tmp"
    if command -v fc-cache >/dev/null 2>&1; then
        fc-cache -f "$font_dir"
    fi
}

install_github_tarball() {
    local repo="$1"
    local name="${repo##*/}"
    log "installing $name from GitHub releases"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        echo "  download latest $name linux tarball to ~/.local/bin"
        return
    fi
    if command -v "$name" >/dev/null 2>&1; then
        warn "$name already installed"
        return
    fi
    local raw_arch
    raw_arch="$(uname -m)"
    # Match common naming conventions: linux-amd64, linux_x86_64, etc.
    local url
    url="$(curl -s "https://api.github.com/repos/$repo/releases/latest" \
        | jq -r --arg arch "$raw_arch" \
            '.assets[]
             | select(.name | test("[Ll]inux[_-](" + $arch + "|amd64|x86_64)"))
             | select(.name | test("\\.(tar\\.gz|tgz)$"))
             | .browser_download_url' \
        | head -1)"
    if [[ -z "$url" ]]; then
        warn "could not find release asset for $repo (linux-$raw_arch)"
        return
    fi
    local tmp
    tmp="$(mktemp -d)"
    curl -fsSL "$url" | tar -xz -C "$tmp"
    # Install the binary (may be at top level or in a subdirectory)
    find "$tmp" -maxdepth 2 -name "$name" -type f -executable -exec cp {} "$HOME/.local/bin/" \;
    rm -rf "$tmp"
}

install_standalone() {
    while IFS= read -r tool; do
        case "$tool" in
            oh-my-zsh) install_oh_my_zsh ;;
            uv)        install_uv ;;
            bun)       install_bun ;;
            *)         warn "unknown standalone tool: $tool" ;;
        esac
    done < <(read_list "$SCRIPT_DIR/standalone.list")
}

install_uv_tools() {
    local tools=()
    while IFS= read -r tool; do
        tools+=("$tool")
    done < <(read_list "$SCRIPT_DIR/uv-tools.list")
    if [[ ${#tools[@]} -eq 0 ]]; then return; fi
    log "installing ${#tools[@]} tools via uv tool install"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        printf '  uv tool install %s\n' "${tools[@]}"
        return
    fi
    export PATH="$HOME/.local/bin:$PATH"
    for tool in "${tools[@]}"; do
        uv tool install "$tool"
    done
}

install_oh_my_zsh() {
    log "installing oh-my-zsh"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        echo "  sh -c \"\$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)\" -- --unattended"
        return
    fi
    if [[ -d "$HOME/.oh-my-zsh" ]]; then
        warn "oh-my-zsh already installed"
        return
    fi
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" -- --unattended
}

install_uv() {
    log "installing uv"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        return
    fi
    if command -v uv >/dev/null 2>&1; then
        warn "uv already installed"
        return
    fi
    curl -LsSf https://astral.sh/uv/install.sh | sh
}

install_bun() {
    log "installing bun"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        echo "  curl -fsSL https://bun.sh/install | bash"
        return
    fi
    if command -v bun >/dev/null 2>&1; then
        warn "bun already installed"
        return
    fi
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
    # Bun can serve as a node runtime for tools that expect it
    ln -sf "$HOME/.bun/bin/bun" "$HOME/.bun/bin/node"
}

install_bun_globals() {
    local packages=()
    while IFS= read -r pkg; do
        packages+=("$pkg")
    done < <(read_list "$SCRIPT_DIR/bun-global.list")
    if [[ ${#packages[@]} -eq 0 ]]; then return; fi
    log "installing ${#packages[@]} packages via bun install -g"
    if [[ "${DRY_RUN:-0}" == 1 ]]; then
        printf '  bun install -g %s\n' "${packages[@]}"
        return
    fi
    export PATH="$HOME/.bun/bin:$PATH"
    bun install -g "${packages[@]}"
}

# -- Main ---------------------------------------------------------------

main() {
    local NO_DESKTOP=0
    local DRY_RUN=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-desktop) NO_DESKTOP=1 ;;
            --dry-run)    DRY_RUN=1 ;;
            --help)       usage; exit 0 ;;
            *)            err "unknown option: $1" ;;
        esac
        shift
    done

    export NO_DESKTOP DRY_RUN

    mkdir -p "$HOME/.local/bin"

    install_apt
    install_rustup
    install_cargo_binstall
    install_github_releases
    install_standalone
    install_uv_tools
    install_bun_globals

    log "bootstrap complete"
}

main "$@"
