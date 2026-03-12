# Vagrant Verification Flow

Goal: verify a fresh Ubuntu 24.04 VM can install the dotfiles repo into `$HOME`
using the bare-repo workflow from `README.md`, then run the package bootstrap.

1. Start a disposable Ubuntu 24.04 VM with Vagrant.
   Use one of these boxes:
   - `bento/ubuntu-24.04`
   - `cloud-image/ubuntu-24.04`
   Preferred provider on Linux: `libvirt`/KVM.
   Acceptable alternative: VirtualBox if the host is known-good.

2. In the guest, install minimal prerequisites needed to fetch the repo:
   ```sh
   sudo apt-get update -qq
   sudo apt-get install -y -qq git curl
   ```

3. Clone the repo as a bare repo into the guest home:
   ```sh
   git clone --bare https://github.com/jRimbault/dotfiles.git "$HOME/.dotfiles"
   alias dot='/usr/bin/git --git-dir="$HOME/.dotfiles" --work-tree="$HOME"'
   ```

4. Apply the dotfiles to the guest home following `README.md`:
   ```sh
   dot checkout
   dot config --local status.showUntrackedFiles no
   dot update-index --skip-worktree README.md
   rm -f "$HOME/README.md"
   ```

5. Run the bootstrap from the checked-out home tree:
   ```sh
   "$HOME/.config/packages/bootstrap.sh" --verbose
   ```

6. Validation passes if:
   - the bare checkout succeeds into a clean guest home,
   - `bootstrap.sh --verbose` exits with code `0`,
   - expected tools are installed without manual intervention.

7. Optional follow-up checks:
   ```sh
   "$HOME/.config/packages/bootstrap.sh" --dry-run --verbose
   "$HOME/.config/packages/bootstrap.sh" --refresh-independent --verbose
   ```
   These help verify rerun behavior and independent tool refreshes.
