#!/usr/bin/env bash
#/ Usage: bootstrap.sh [OPTIONS]
#/
#/ Bootstrap a fresh Ubuntu/Debian system with required packages.
#/ Installs minimal apt dependencies and uv, then delegates to bootstrap.py.
#/
#/ Options:
#/   --no-desktop    Skip sway/desktop packages
#/   --refresh-independent
#/                  Update independently installed tools to their latest managed version
#/   --dry-run       Print what would be installed without doing it
#/   --verbose       Enable debug logging in bootstrap.py
#/   --help          Show this help message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() { grep "^#/" "$0" | cut -c4-; }

log()  { printf '\033[1;34m>>>\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    APT_PREFIX=()
else
    APT_PREFIX=(sudo)
fi

for arg in "$@"; do
    case "$arg" in
        --help) usage; exit 0 ;;
    esac
done

# Ensure minimal apt prerequisites for the rest of the bootstrap
log "installing apt prerequisites"
"${APT_PREFIX[@]}" apt-get update -qq
"${APT_PREFIX[@]}" apt-get install -y -qq curl git >/dev/null

# Install uv if not present
if ! command -v uv >/dev/null 2>&1; then
    log "installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Hand off to the Python bootstrap script
log "handing off to bootstrap.py"
exec "$SCRIPT_DIR/bootstrap.py" "$@"
