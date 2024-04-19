#!/usr/bin/env bash

set -eu

sorting()
{
  # removes the local executions
  grep -v "./" |
  column -c3 -s " " -t |
  sort -n |
  nl
}

fish_special_case()
{
  grep cmd "$HOME/.local/share/fish/fish_history" |
  cut -d: -f 2 | sed -e 's/^[ \t]*//' |
  awk "$awkscript" |
  sorting
  exit 0
}

main()
{
  $cmd |
  awk "$awkscript" |
  sorting
  exit 0
}

# shellcheck disable=SC2016
awkscript='
  {
    CMD[$1]++
    count++
  } END {
    for (a in CMD) {
      print CMD[a] " " CMD[a]/count*100 "% " a
    }
  }'

readonly callingshell=$(readlink /proc/$PPID/exe)

[[ "$callingshell" =~ .*zsh ]] && cmd="cut -d; -f 2 $HOME/.zsh_history"
[[ "$callingshell" =~ .*bash ]] && cmd="cat $HOME/.bash_history"
[[ "$callingshell" =~ .*fish ]] && fish_special_case

main
