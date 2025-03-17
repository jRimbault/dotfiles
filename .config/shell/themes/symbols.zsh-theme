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

autoload -U colors && colors
setopt promptsubst

# User Indicator: Use `λ` by default, but switch to `user@host` in SSH sessions.
USER_PROMPT_SYMBOL="λ"

if [[ -n $SSH_CONNECTION ]]; then
  USER_PROMPT_SYMBOL="$USER@$HOST"
fi

# Symbols for Prompt
STATUS_SYMBOL="›" # Changes color based on last command status

# Ensure prompt colors are correctly escaped
_RESET="%{$reset_color%}"
_WHITE="%{$fg[white]%}"
_BOLD_WHITE="%{$fg_bold[white]%}"
_GREEN="%{$fg[green]%}"
_RED="%{$fg[red]%}"

# Shows a status indicator that turns red when the last command fails.
status_indicator() {
  if [[ $? -eq 0 ]]; then
    echo "$_GREEN$STATUS_SYMBOL$_RESET"
  else
    echo "$_RED$STATUS_SYMBOL$_RESET"
  fi
}

# Displays the current Git or Mercurial branch, with red color if the working directory is dirty.
vcs_info() {
  local branch status_color=""

  # Check for a Git branch first
  if branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null); then
    # Determine if there are uncommitted changes
    [[ -n $(git status --porcelain 2>/dev/null) ]] && status_color="$_RED" || status_color="$_WHITE"
    echo " $status_color$branch$_RESET"
  fi
}

# Displays a shortened path with a configurable number of segments,
# replacing $HOME with ~ when applicable.
shortened_path() {
  local max_segments="${1:-2}" max_segment_length="${2:-0}"
  local cwd_segments path_display segment trimmed_segment cwd_path

  # Get current directory and replace $HOME with ~ if applicable
  if [[ $PWD == $HOME* ]]; then
    cwd_path="~${PWD#$HOME}"
  else
    cwd_path="$PWD"
  fi

  # Split path into segments
  cwd_segments=("${(@s:/:)${(%)cwd_path}}")

  # Ensure valid segment counts
  (( max_segments < 1 )) && max_segments=1
  (( max_segment_length > 0 && max_segment_length < 4 )) && max_segment_length=4
  local half_length=$((max_segment_length / 2 - 1))

  # Process each path segment, applying shortening if needed
  for segment in "${cwd_segments[@]: -max_segments}"; do
    if (( max_segment_length > 0 && ${#segment} > max_segment_length )); then
      trimmed_segment="${segment:0:half_length}..${segment: -half_length}"
    else
      trimmed_segment="$segment"
    fi
    path_display+="${_BOLD_WHITE}$trimmed_segment$_RESET/"
  done

  # Remove trailing slash and return the final formatted path
  echo "${path_display%/}"
}

# Configure the primary prompt (left side).
PROMPT='${USER_PROMPT_SYMBOL} $(status_indicator) '
# Configure the secondary prompt (right side).
RPROMPT='$(shortened_path)$(vcs_info)'
