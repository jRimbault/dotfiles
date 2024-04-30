#!/usr/bin/env zsh

# History search
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search

[[ -n "$key[Up]"   ]] && bindkey -- "$key[Up]"   up-line-or-beginning-search
[[ -n "$key[Down]" ]] && bindkey -- "$key[Down]" down-line-or-beginning-search


# project navigation
_zsh_goto_project()
{
    goto_project
    zle reset-prompt
}
zle -N _zsh_goto_project
bindkey ^s _zsh_goto_project


# short git log
_zsh_git_log_short()
{
    git_log_pager_short
    zle reset-prompt
}
zle -N _zsh_git_log_short
bindkey ^k _zsh_git_log_short

# history fuzzy finder
_history_fuzzy_finder()
{
    history_fuzzy_finder
    zle reset-prompt
}
zle -N _history_fuzzy_finder
bindkey ^r _history_fuzzy_finder

_zsh_cli_fg() {
    fg
}
zle -N _zsh_cli_fg
bindkey ^z _zsh_cli_fg

