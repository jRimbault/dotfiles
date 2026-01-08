#!/usr/bin/env zsh
# zmodload zsh/zprof
# zmodload zsh/datetime; zmodload zsh/parameter; typeset -F SECONDS

umask 022
export HISTSIZE=10000000
export SAVEHIST="$HISTSIZE"

export ZSH="$HOME/.oh-my-zsh"

ZSH_CUSTOM="$HOME/.config/shell"
ZSH_THEME="symbols"

plugins=()

source "$ZSH/oh-my-zsh.sh"
declare -ra libs=(
  "aliases"
  "functions"
  "fzf-git.sh"
  "gh.function"
  "keybindings.zsh"
  "env_vars"
)

# Load aliases and functions
for lib in "${libs[@]}"; do
  lib="$ZSH_CUSTOM/$lib"
  test -f "$lib" && source "$lib"
done
autoload -z edit-command-line
zle -N edit-command-line
bindkey -M vicmd v edit-command-line
# Disable colors in tab completion
zstyle ':completion:*' list-colors
zstyle ':completion:*:*:git:*' user-commands ${${(M)${(k)commands}:#git-*}/git-/}

test -f ~/.env && . ~/.env # if environment overwrite previous settings
test -f ~/.profile && . ~/.profile

