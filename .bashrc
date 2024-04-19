#!/usr/bin/env bash
# shellcheck disable=SC1090
# shellcheck disable=SC2016

# Stop if not interactive mode
case $- in
  *i*) ;;
    *) return;;
esac

umask 022

HISTSIZE=1000
HISTFILESIZE=2000
# Don't log duplicate
HISTCONTROL=ignoreboth
# Append to histfile, don't overwrite
shopt -s histappend

# Update LINES and COLUMNS after each command
shopt -s checkwinsize

declare -ra libs=(
  "alias.sh"
  "function.sh"
  "gh.sh"
  "theme.sh"
)

# Load aliases and functions
for lib in "${libs[@]}"; do
  lib="$HOME/.config/bash/$lib"
  test -f "$lib" && source "$lib"
done

# Custom keybindings
bind -x '"\C-s":"goto_project"'
bind -x '"\C-k":"git_log_pager_short"'
bind -x '"\C-r":"history_fuzzy_finder"'

# Enable variables in prompt
shopt -s promptvars

test -f ~/.def-env-vars && . ~/.def-env-vars
test -f ~/.env && . ~/.env # if environment overwrite previous settings
