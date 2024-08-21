#!/usr/bin/env zsh
umask 022
HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=10000
setopt histignorespace
setopt appendhistory
setopt extended_history
setopt hist_expire_dups_first
setopt hist_ignore_dups
setopt hist_ignore_space
setopt hist_verify
setopt share_history

ZSH_CUSTOM="$HOME/.config/shell"
ZSH_THEME="symbols"

fpath+="$ZSH_CUSTOM/completions"
autoload -U compinit
compinit

declare -ra libs=(
  "aliases"
  "functions"
  "fzf-git.sh"
  "gh.function"
  "keybindings.zsh"
  "env_vars"
  "themes/$ZSH_THEME.zsh-theme"
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

test -f ~/.cargo/env && . ~/.cargo/env
test -f ~/.env && . ~/.env # if environment overwrite previous settings
test -f ~/.profile && . ~/.profile
eval "$(zoxide init zsh)"
source <(fzf --zsh)
