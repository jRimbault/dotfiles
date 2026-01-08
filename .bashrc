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
  "aliases"
  "functions"
  "gh.function"
  "theme.bash"
)

# Load aliases and functions
for lib in "${libs[@]}"; do
  lib="$HOME/.config/shell/$lib"
  test -f "$lib" && source "$lib"
done

# Custom keybindings
bind -x '"\C-s":"goto_project"'
bind -x '"\C-k":"git_log_pager_short"'
bind -x '"\C-r":"history_fuzzy_finder"'

# Enable variables in prompt
shopt -s promptvars

test -f ~/.env && . ~/.env # if environment overwrite previous settings
test -f ~/.profile && . ~/.profile

export STM32_PRG_PATH=/opt/stm32/STMicroelectronics/STM32Cube/STM32CubeProgrammer/bin
