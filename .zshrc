#!/usr/bin/env zsh
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
COMPLETION_WAITING_DOTS=0
umask 022
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="symbols"

plugins=()

_zsh_cli_fg() { fg; }
zle -N _zsh_cli_fg
bindkey '^Z' _zsh_cli_fg

source "$ZSH/oh-my-zsh.sh"
autoload -z edit-command-line
zle -N edit-command-line
bindkey -M vicmd v edit-command-line
# Disable colors in tab completion
zstyle ':completion:*' list-colors
zstyle ':completion:*:*:git:*' user-commands ${${(M)${(k)commands}:#git-*}/git-/}

test -f ~/.def-env-vars && . ~/.def-env-vars
test -f ~/.env && . ~/.env # if environment overwrite previous settings
. ~/.profile
eval "$(zoxide init zsh)"
