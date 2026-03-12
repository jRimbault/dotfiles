# Package bootstrap

The package bootstrap entrypoint lives in `.config/packages/bootstrap.sh` and delegates to `.config/packages/bootstrap.py`.

## Behavior

- The bootstrap can be run as either a regular user with `sudo` or directly as `root`.
- When a bootstrap step fails, the overall process exits with a non-zero status and logs the error.
- Neovim is installed from the official release tarball instead of the Ubuntu `apt` package.
- By default, rerunning the bootstrap leaves independently installed tools in place unless they are missing.
- `--refresh-independent` refreshes independently installed tools such as GitHub release binaries, `uv` tools, `bun`, and cargo-installed binaries.
- `--no-desktop` skips the packages listed in `.config/packages/apt-no-desktop.list`.

## Container validation

This bootstrap was validated in an Ubuntu 24.04 container with:

```sh
docker run --rm -v "$PWD:/repo:ro" -w /repo ubuntu:24.04 bash -lc '
  export DEBIAN_FRONTEND=noninteractive
  /repo/.config/packages/bootstrap.sh --verbose
'
```
