#!/usr/bin/env zsh

# Αα	Alpha
# Ββ	Beta
# Γγ	Gamma
# Δδ	Delta
# Εε	Epsilon
# Ζζ	Zeta
# Ηη	Eta
# Θθ	Theta
# Ιι	Iota
# Κκ	Kappa
# Λλ	Lambda
# Μμ	Mu
# Νν	Nu
# Ξξ	Xi
# Οο	Omicron
# Ππ	Pi
# Ρρ	Rho
# Σσς	Sigma
# Ττ	Tau
# Υυ	Upsilon
# Φφ	Phi
# Χχ	Chi
# Ψψ	Psi
# Ωω	Omega

_USER_CHAR="${_USER_CHAR:-λ}"
_INSERT_CHAR="${_INSERT_CHAR:-›}"

autoload -U colors && colors
setopt promptsubst

if [[ -n $SSH_CONNECTION ]]; then
  _USER_CHAR="$USER@$HOST"
fi

minimal_vcs() {
  local stat_color="%{${fg[white]}%}" # assume it is clean
  local branch_name

  branch_name="$(git rev-parse --abbrev-ref HEAD 2> /dev/null || hg branch 2> /dev/null)"
  if [[ -n "$branch_name" ]]; then
    if [[ -n "$(git status --porcelain 2> /dev/null)" ]]; then
      stat_color="%{${fg[red]}%}"
    fi
    print -r " $stat_color$branch_name%{$reset_color%}"
  fi
}

current_path() {
  local segments="${1:-2}"
  local seg_len="${2:-0}"

  local _w="%{$reset_color%}"
  local _g="%{${fg_bold[white]}%}"

  if [ "$segments" -le 0 ]; then
      segments=1
  fi
  if [ "$seg_len" -gt 0 ] && [ "$seg_len" -lt 4 ]; then
      seg_len=4
  fi
  local seg_hlen=$((seg_len / 2 - 1))

  local cwd="%${segments}~"
  cwd="${(%)cwd}"
  cwd=("${(@s:/:)cwd}")

  local pi=""
  for i in {1..${#cwd}}; do
    pi="$cwd[$i]"
    if [ "$seg_len" -gt 0 ] && [ "${#pi}" -gt "$seg_len" ]; then
      cwd[$i]="${pi:0:$seg_hlen}$_w..$_g${pi: -$seg_hlen}"
    fi
  done

  print -r "$_g${(j:/:)cwd//\//$_w/$_g}$_w"
}

status_prompt() {
  # ternary expression, check last command status
  print -r "%(?:%{${fg[green]}%}$1:%{${fg[red]}%}$1)$reset_color"
}

prompt() {
  print -r "$_USER_CHAR $(status_prompt "$_INSERT_CHAR") "
}

# single quotes to evaluate at runtime, not source time
PROMPT='$(prompt)'
RPROMPT='$(current_path)$(minimal_vcs)'
