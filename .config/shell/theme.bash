#!/usr/bin/env bash

# read-only globals
readonly __NOCOL="\\033[0m" # No color
readonly __BLACK="\\033[0;30m" # __Black
readonly __WHITE="\\033[1;37m" # White

# colored output
__colored()     { echo -e "$*$__NOCOL"; }
_grey()         { __colored "\\033[1;30m$*"; }
_light_grey()   { __colored "\\033[0;37m$*"; }
_red()          { __colored "\\033[0;31m$*"; }
_light_red()    { __colored "\\033[1;31m$*"; }
_green()        { __colored "\\033[0;32m$*"; }
_light_green()  { __colored "\\033[1;32m$*"; }
_orange()       { __colored "\\033[0;33m$*"; }
_yellow()       { __colored "\\033[1;33m$*"; }
_blue()         { __colored "\\033[0;34m$*"; }
_light_blue()   { __colored "\\033[1;34m$*"; }
_purple()       { __colored "\\033[0;35m$*"; }
_light_purple() { __colored "\\033[1;35m$*"; }
_cyan()         { __colored "\\033[0;36m$*"; }
_light_cyan()   { __colored "\\033[1;36m$*"; }


parse_git_branch() {
  git branch  --no-color 2> /dev/null |
  sed -e '/^[^*]/d' -e 's/* \(.*\)/\1 /'
}

git_branch()
{
  local branch
  branch="$(parse_git_branch)"
  if [[ $(git status --porcelain 2> /dev/null) ]]; then
    _red "$branch"
  else
    echo -n "$branch"
  fi
}

get_pwd()
{
  local cwd parent
  cwd="$(basename "$PWD")"
  parent="$(basename "$(dirname "$PWD")")"
  echo -n " $parent/$cwd "
}

user_symbol()
{
  local s
  s="${_USER_CHAR:-λ}"
  echo -n "$s"
}

insert_symbol()
{
  local s
  s="${_INSERT_CHAR:-›}"
  echo -n "$s "
}

PS1='$(user_symbol)$(get_pwd)$(git_branch)$(insert_symbol)'

