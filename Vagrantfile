# Vagrantfile for verifying dotfiles bootstrap on a fresh Ubuntu 24.04
# See VAGRANT_VERIFICATION_GUIDE.md for the manual steps this automates.

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-24.04"
  config.vm.hostname = "dotfiles-test"

  config.vm.provider :libvirt do |v|
    v.memory = 4096
    v.cpus = 2
  end

  config.vm.provider :virtualbox do |v|
    v.memory = 4096
    v.cpus = 2
  end

  # Run the dotfiles verification as the vagrant user
  config.vm.provision "shell", privileged: false, inline: <<-SHELL
    set -euo pipefail

    dot() { /usr/bin/git --git-dir="$HOME/.dotfiles" --work-tree="$HOME" "$@"; }

    echo "=== Step 1: Install prerequisites ==="
    sudo apt-get update -qq
    sudo apt-get install -y -qq git curl

    echo "=== Step 2: Clone bare repo ==="
    git clone --bare https://github.com/jRimbault/dotfiles.git "$HOME/.dotfiles"

    echo "=== Step 3: Checkout dotfiles ==="
    # Remove default Ubuntu skeleton files that would conflict with checkout
    if ! dot checkout 2>/dev/null; then
      checkout_err=$(dot checkout 2>&1 || true)
      echo "$checkout_err" | awk '/^\t/{print $1}' | xargs -r -I{} rm -f "$HOME/{}"
      dot checkout
    fi
    dot config --local status.showUntrackedFiles no
    dot update-index --skip-worktree README.md
    rm -f "$HOME/README.md"

    echo "=== Step 4: Run bootstrap ==="
    "$HOME/.config/packages/bootstrap.sh" --no-desktop --verbose
  SHELL
end
