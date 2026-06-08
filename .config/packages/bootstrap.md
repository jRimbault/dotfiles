# Package bootstrap

The package bootstrap entrypoint lives in `.config/packages/bootstrap.sh` and delegates to `.config/packages/bootstrap.py`.

## Behavior

- The bootstrap can be run as either a regular user with `sudo` or directly as `root`.
- When a bootstrap step fails, the overall process exits with a non-zero status and logs the error.
- Most dev tools are declared in `.config/mise/config.toml` and installed with [mise](https://mise.jdx.dev/) (`mise install`). The script installs mise itself if it is missing.
- The pieces mise does not manage are handled directly: apt system packages, the rustup toolchain (with the `rust-analyzer` component), oh-my-zsh, and the Hack Nerd Font.
- `apt.list` entries can opt out of recommended packages with the `[no-recommends]` suffix.
- By default, rerunning the bootstrap leaves independently installed tools in place unless they are missing.
- `--refresh-independent` updates the independently managed tools: it runs `mise upgrade`, updates rustup, pulls oh-my-zsh, and re-fetches the Nerd Font, while skipping apt. Optional tool names are passed straight to `mise upgrade` (e.g. `--refresh-independent neovim ripgrep`).
- `--no-desktop` skips the packages listed in `.config/packages/apt-no-desktop.list`.

## Container validation

This bootstrap was validated in an Ubuntu 24.04 container with:

```sh
docker run --rm -v "$PWD:/repo:ro" -w /repo ubuntu:24.04 bash -lc '
  export DEBIAN_FRONTEND=noninteractive
  export MISE_GLOBAL_CONFIG_FILE=/repo/.config/mise/config.toml
  /repo/.config/packages/bootstrap.sh --verbose
'
```

`MISE_GLOBAL_CONFIG_FILE` points mise at the in-repo config when the dotfiles are
not checked out into `$HOME`; `bootstrap.py` sets it automatically, so it is only
needed when invoking mise by hand.
