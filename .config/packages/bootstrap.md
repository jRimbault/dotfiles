# Package bootstrap

The package bootstrap entrypoint lives in `.config/packages/bootstrap.sh` and delegates to `.config/packages/bootstrap.py`.

## Behavior

- The bootstrap can be run as either a regular user with `sudo` or directly as `root`.
- When a bootstrap step fails, the overall process exits with a non-zero status and logs the error.
- `--no-desktop` skips the sway-related desktop packages listed in `.config/packages/apt.list`.

## Container validation

This bootstrap was validated in an Ubuntu 24.04 container with:

```sh
docker run --rm -v "$PWD:/repo:ro" -w /repo ubuntu:24.04 bash -lc '
  export DEBIAN_FRONTEND=noninteractive
  /repo/.config/packages/bootstrap.sh --verbose
'
```
