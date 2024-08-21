#!/usr/bin/env bash

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Environment variables :
N_PREFIX="$HOME/.local/n"


prepend:path()
{
  if [[ :$PATH: == *:"$1":* ]]; then
    # already in path
    return
  fi
  if [ -d "$1" ]; then
    PATH="$1:$PATH"
  fi
}

prepend:path "/opt/gradle/gradle-5.0/bin"
prepend:path "/snap/bin"
prepend:path "$HOME/.cargo/bin"
prepend:path "$HOME/.gem/ruby/2.5.0/bin"
prepend:path "$N_PREFIX/bin"
prepend:path "$HOME/.local/bin"
prepend:path "$HOME/.bin"
prepend:path "$HOME/bin"
prepend:path "$GOBIN"
prepend:path "$HOME/.local/share/JetBrains/Toolbox/scripts"


EDITOR="$(command -v nvim)"

export N_PREFIX
export PATH
export EDITOR
