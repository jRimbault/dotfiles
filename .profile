#!/usr/bin/env bash

test -f ~/.env && source ~/.env

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
prepend:path "$GOBIN"


EDITOR="$(command -v hx)"

export N_PREFIX
export PATH
export EDITOR

